# aria/execution/routers/chess_router.py
#
# Router d'exécution du coach d'échecs (sprint 26, tronçon 02).
#
# Pipeline CHESS_ANALYSIS :
#   PGN collé → chess_coach.analysis.analyze (Stockfish)
#   → un diagramme PNG par position critique (≤ 3, flèche = meilleur coup)
#   → message enrichi des faits moteur (notation anglaise, sprint 27)
#   → LLMExecutionRouter en REASONING, SANS skip_intent : l'échange suit
#     le pipeline normal (intent + écriture épisodique), décision Q4.
#
# Contrat de retour : {"text": str, "images": [{"path", "caption"}, …]}.
#
# Règle d'architecture :
#   La seule écriture propre à ce router est la fiche de partie
#   (write_chess_game, tronçon 03), via memory/writer.py (règle 1).
#   L'échange lui-même est écrit par LLMExecutionRouter.
#   Les fiches de partie sont relues via le bridge (règle 2) pour le bloc
#   « Progression » (sprint 28, tronçon 03), écrit par le router sous le texte LLM.

import hashlib
import re
from pathlib import Path
from uuid import uuid4

import chess

from chess_coach.analysis import analyze, split_pgn
from chess_coach.explosive import _GAIN_MIN
from chess_coach.player_model import LABELS, MATE_LABELS, build_profile, opening_family
from chess_coach.render import render_position
from chess_coach.summary import summarize, summary_text
from config import config
from cognition.cognitive_context import CognitiveOperation
from execution.routers.execution_base import BaseRouter
from logger import get_logger
from memory.writer import write_chess_game

log = get_logger(__name__)

_COLOR_FR = {"white": "blancs", "black": "noirs"}

_SOURCE_FR = {
    "header": "pseudo dans l'en-tête",
    "message": "précisé dans le message",
    "default": "supposé par défaut",
}

_KIND_FR = {
    "a": "erreur de Nico",
    "b": "occasion manquée après erreur adverse",
    "c": "coup unique trouvé",
    "d": "occasion explosive",
    "e": "tournant (erreur adverse punie)",
}

# Critère d'avantage clair (chess_coach.analysis.clear_advantage) → libellé français.
_EVIDENCE_FR = {
    "material": "gain matériel", "crushing": "position écrasante", "mate": "attaque de mat",
    "development": "avance de développement", "activity": "avance d'activité",
}

_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

_OUTCOME_FR = {"win": "victoire", "loss": "défaite", "draw": "nulle", "unknown": "issue inconnue"}

# Lettre de pièce française devant une case (prise, désambiguïsation comprises) :
# « Dxe5+ », « Cbd7 », « Tae1 ». R (roi en français, tour en anglais) laissé tel quel.
_FR_PIECE_RE = re.compile(r"\b([CFTD])([a-h]?[1-8]?x?[a-h][1-8])\b")
_FR_TO_EN = {"C": "N", "F": "B", "T": "R", "D": "Q"}

# Nom français de la pièce offerte (libellé du bloc d'occasion explosive).
_PIECE_FR = {"N": "le cavalier", "B": "le fou", "R": "la tour", "Q": "la dame", "K": "le roi"}

_FORCING_FR = {"check": "échec", "capture": "prise", "threat": "menace"}

_PHASE_FR = {"opening": "ouverture", "middlegame": "milieu de partie", "endgame": "finale"}

_TAG_FR = {
    "capture": "prise", "check": "échec", "pawn": "coup de pion", "king": "coup de roi",
    "castle": "roque", "retreat": "recul", "hanging": "pièce en prise",
}

# Intent imposé aux échanges d'analyse de partie (bug 1, audit correctif 05) :
# le namer répondait « aucun » → échange non écrit en épisodique.
FORCED_INTENT_NAME = "jeux echecs"

# Clés de compteurs (qualité PlyAnalysis) → libellé français, dans l'ordre affiché.
# Raison affichée d'un badge débloqué (conditions : chess_coach.player_model).
_BADGE_REASON = {
    "Main propre": "aucune gaffe sur une partie d'au moins 40 demi-coups",
    "Justicier": "toutes les erreurs adverses punies (au moins 2)",
    "Coup de maître": "coup trouvé 400 Elo au-dessus du classement global",
    "Phénix": "nulle ou victoire après être tombé à 20 % de gain ou moins",
    "Bourreau": "3 victoires écrasantes de suite",
    "Série": "3 victoires de suite",
    "Répertoire": "5e partie dans la même famille d'ouverture",
}

_RESULT_FR = {1.0: "victoire", 0.5: "nulle", 0.0: "défaite"}

_QUALITY_FR = [
    ("best", "meilleurs"), ("correct", "corrects"), ("inaccuracy", "imprécisions"),
    ("mistake", "erreurs"), ("blunder", "gaffes"),
]


def _move_label(move_number: int, color: str, san: str) -> str:
    """« 17.Cg4+ » pour les blancs, « 17...Cg4+ » pour les noirs."""
    dots = "." if color == "white" else "..."
    return f"{move_number}{dots}{san}"


def _format_line(pv_san: list, move_number: int, color: str) -> str:
    """Ligne principale numérotée en notation anglaise (ex. « 17...Bd7 18.Nf3 Nc6 »)."""
    parts = []
    for i, san in enumerate(pv_san):
        if color == "white":
            parts.append(f"{move_number}.{san}")
            color = "black"
        else:
            parts.append(f"{move_number}...{san}" if i == 0 else san)
            color = "white"
            move_number += 1
    return " ".join(parts)


def _header_lines(headers: dict) -> list:
    """En-têtes utiles du PGN (valeurs « ? » ou absentes ignorées)."""
    def h(key):
        value = headers.get(key, "")
        return "" if value in ("", "?", "????.??.??") else value

    lines = []
    for color_key, label in (("White", "Blancs"), ("Black", "Noirs")):
        if h(color_key):
            elo = f" ({h(color_key + 'Elo')} Elo)" if h(color_key + "Elo") else ""
            lines.append(f"{label} : {h(color_key)}{elo}")
    if h("Date"):
        lines.append(f"Date : {h('Date')}")
    opening = " ".join(v for v in (h("ECO"), h("Opening")) if v)
    if opening:
        lines.append(f"Ouverture : {opening}")
    if h("Result"):
        lines.append(f"Résultat : {h('Result')}")
    return lines


def _anchor(summary: dict) -> str:
    """« Partie contre <adversaire> <date> <ouverture> » : identifiant lisible
    de la partie, pour qu'une question de suivi retrouve la bonne (Q11 b)."""
    parts = ["Partie contre", summary["opponent"] or "adversaire inconnu"]
    if summary["date"]:
        parts.append(summary["date"])
    if summary["opening"]:
        parts.append(summary["opening"].replace("-", " "))
    return " ".join(parts)


def _pieces_line(fen: str) -> str:
    """Pièces par camp tirées du FEN (ex. « pièces : blancs Kg1 Nf3, pions e4 ; noirs … ») :
    le LLM ne voit pas l'échiquier, cette liste l'empêche de placer une pièce inexistante."""
    board = chess.Board(fen)
    sides = []
    for color, label in ((chess.WHITE, "blancs"), (chess.BLACK, "noirs")):
        pieces = [
            f"{chess.piece_symbol(piece).upper()}{chess.square_name(sq)}"
            for piece in (chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
            for sq in board.pieces(piece, color)
        ]
        pawns = [chess.square_name(sq) for sq in board.pieces(chess.PAWN, color)]
        sides.append(f"{label} {' '.join(pieces)}, pions {' '.join(pawns) or 'aucun'}")
    return "  pièces : " + " ; ".join(sides)


def _material_line(fen: str, nico_color: str) -> str:
    """Bilan matériel du point de vue de Nico (valeurs 1/3/3/5/9)."""
    board = chess.Board(fen)
    nico = chess.WHITE if nico_color == "white" else chess.BLACK
    balance = sum(
        value * (len(board.pieces(piece, nico)) - len(board.pieces(piece, not nico)))
        for piece, value in _VALUES.items()
    )
    if balance == 0:
        return "matériel : égal"
    return f"matériel : Nico {'+' if balance > 0 else '−'}{abs(balance)}"


def _square_label(board: chess.Board, sq: int) -> str:
    """« Nf3 » pour une pièce, « pion e5 » pour un pion."""
    piece = board.piece_at(sq)
    if piece.piece_type == chess.PAWN:
        return f"pion {chess.square_name(sq)}"
    return f"{piece.symbol().upper()}{chess.square_name(sq)}"


def _attacked_line(fen: str) -> str:
    """Pièces attaquées par l'adversaire, par camp (hors roi ; pions seulement si non
    défendus), avec leurs attaquants : le LLM ne doit décrire aucune autre attaque."""
    board = chess.Board(fen)
    sides = []
    for color, label in ((chess.WHITE, "blancs"), (chess.BLACK, "noirs")):
        items = []
        for sq in chess.SquareSet(board.occupied_co[color]):
            if board.piece_type_at(sq) == chess.KING:
                continue
            attackers = board.attackers(not color, sq)
            if not attackers:
                continue
            defended = bool(board.attackers(color, sq))
            if board.piece_type_at(sq) == chess.PAWN and defended:
                continue
            by = ", ".join(_square_label(board, a) for a in attackers)
            items.append(f"{_square_label(board, sq)}{'' if defended else ' non défendu'} (par {by})")
        if items:
            sides.append(f"{label} " + ", ".join(items))
    return "attaquées : " + (" ; ".join(sides) or "aucune")


def _move_fact_items(fen: str, moves_san: list, move_number: int, color: str) -> list:
    """Ligne rejouée depuis `fen` : liste de (libellé du coup, faits observables) —
    prise, échec, mat, roque, promotion, et pièces adverses nouvellement attaquées
    par la pièce jouée (non défendues ou de valeur supérieure). Calcul unique partagé
    par la ligne « faits : » du message enrichi et la ligne « Variante : » des légendes."""
    board = chess.Board(fen)
    parts = []
    recapture_square = None
    for san in moves_san:
        move = board.parse_san(san)
        mover = board.turn
        castling = board.is_castling(move)
        facts = []
        if castling:
            facts.append("roque")
        elif board.is_capture(move):
            # Reprise : prise sur la case où l'adversaire vient de prendre.
            if move.to_square == recapture_square:
                facts.append("reprend")
            else:
                captured = move.to_square
                if board.is_en_passant(move):
                    captured += -8 if mover == chess.WHITE else 8
                facts.append(f"prend {_square_label(board, captured)}")
        recapture_square = move.to_square if board.is_capture(move) else None
        if move.promotion:
            facts.append(f"promotion en {chess.piece_symbol(move.promotion).upper()}")
        before = chess.SquareSet() if castling else board.attacks(move.from_square)
        # Le roi n'attaque utilement qu'une pièce non défendue (valeur 0 dans _VALUES).
        attacker_value = _VALUES[move.promotion or board.piece_type_at(move.from_square)] or 100
        board.push(move)
        if board.is_checkmate():
            facts.append("mat")
        elif board.is_check():
            facts.append("échec")
        if not castling and not board.is_checkmate():
            targets = [
                _square_label(board, sq)
                for sq in board.attacks(move.to_square) & board.occupied_co[not mover]
                if sq not in before and board.piece_type_at(sq) != chess.KING
                and (not board.attackers(not mover, sq)
                     or _VALUES[board.piece_type_at(sq)] > attacker_value)
            ]
            if targets:
                facts.append("attaque " + ", ".join(targets))
        parts.append((_move_label(move_number, color, san), facts))
        if color == "black":
            move_number += 1
        color = "black" if color == "white" else "white"
    return parts


def _move_facts(fen: str, moves_san: list, move_number: int, color: str) -> str:
    """Ligne « faits : » du message enrichi : chaque coup suivi de ses faits entre
    parenthèses. Le LLM s'appuie sur ces faits au lieu de les deviner."""
    return " ".join(
        f"{label} ({', '.join(facts)})" if facts else label
        for label, facts in _move_fact_items(fen, moves_san, move_number, color)
    )


def _variant_line(critical) -> str:
    """Ligne « Variante : » d'une légende, racontée par le code (tronçon 15) : coups
    séparés par « ; », chacun suivi de ses faits. Vide si la ligne n'a aucun coup."""
    p = critical.ply
    if critical.kind in ("c", "e"):
        moves = critical.line_san
    elif critical.kind == "d":
        moves = [critical.explosive.san] + critical.explosive.trap_line_san
    else:
        moves = p.pv_san
    if not moves:
        return ""
    items = _move_fact_items(p.fen_before, moves, p.move_number, p.color)
    return "Variante : " + " ; ".join(
        f"{label} {', '.join(facts)}" if facts else label for label, facts in items
    ) + "."


def _evaluation(win: float) -> str:
    """État de la position d'après le % de gain de Nico."""
    if win >= 60:
        return "avantage Nico"
    if win <= 40:
        return "avantage adverse"
    return "équilibre"


def _to_english(text: str) -> str:
    """Notation française résiduelle du LLM → anglaise (C→N, F→B, T→R, D→Q)."""
    return _FR_PIECE_RE.sub(lambda m: _FR_TO_EN[m.group(1)] + m.group(2), text)


def _level_line(summary: dict) -> str:
    """Données de niveau de la partie (précision Lichess, erreurs adverses punies, résultat)."""
    parts = []
    if summary["accuracy"] is not None:
        parts.append(f"précision Nico : {summary['accuracy']:.0f} %")
    parts.append(f"erreurs adverses punies : {summary['opponent_errors_punished']}"
                 f"/{summary['opponent_errors']}")
    parts.append(f"résultat : {summary['result'] or '?'} ({_OUTCOME_FR[summary['outcome']]})")
    return "Niveau (données) : " + " ; ".join(parts)


def _moves_line(summary: dict) -> str:
    """Ligne déterministe sous le texte LLM : précision, meilleur et pire coup (tronçon 08)."""
    parts = []
    if summary["accuracy"] is not None:
        parts.append(f"Précision {summary['accuracy']:.0f} %")
    if summary["best_move"]:
        parts.append(f"meilleur coup {summary['best_move']} "
                     f"(trouvé par {summary['best_move_p'] * 100:.0f} % des joueurs de ton niveau)")
    if summary["worst_move"]:
        parts.append(f"pire coup {summary['worst_move']} "
                     f"({summary['worst_win_before']:.0f} % → {summary['worst_win_after']:.0f} %)")
    return "🎯 " + " · ".join(parts) if parts else ""


def _signed(x: float) -> str:
    """ΔR arrondi signé, − typographique (comme _material_line)."""
    n = round(x)
    return f"+{n}" if n >= 0 else f"−{abs(n)}"


def _history_line(after) -> str:
    """Données d'historique pour la ligne « Niveau : » du LLM."""
    g = after.ratings["global"]
    return (f"Historique (données) : {after.n_games} parties saison 1, classement global "
            f"{round(g.value)} (niveau {g.level}), {_signed(after.last_game['global'].delta)} "
            "sur cette partie")


def _trial_text(trial) -> str:
    """Épreuve qui a le plus pesé : « 17.Qb3 trouvé (difficulté ≈1950) »."""
    if trial.label == "résultat":
        return f"{_RESULT_FR[trial.score]} contre {round(trial.difficulty)}"
    if trial.label == "coups 1-10":
        return f"coups 1-10 {'réussis' if trial.score else 'ratés'} (difficulté ≈{round(trial.difficulty)})"
    text = (f"{trial.label} {'trouvé' if trial.score else 'raté'} "
            f"(difficulté ≈{round(trial.difficulty, -1):.0f})")
    return f"{text}, {trial.mate}" if trial.mate else text


def _motif_fr(motif: str) -> str:
    """Libellé français d'un motif (« fork » → « fourchette ») pour le bloc enrichi."""
    if motif in MATE_LABELS:
        return MATE_LABELS[motif]
    label = LABELS["hanging" if motif == "hangingPiece" else motif]
    return label[0].lower() + label[1:]


def _rating_line(key: str, before, after) -> str:
    """« ⬆️ Punir les erreurs 1385 (+25) · niveau 13 atteint » (flèche si palier changé)."""
    rating, gd = after.ratings[key], after.last_game[key]
    line = f"{LABELS[key]} {round(rating.value)} ({_signed(gd.delta)})"
    old = before.ratings[key].level if before.ratings else rating.level
    if rating.level > old:
        return f"⬆️ {line} · niveau {rating.level} atteint"
    if rating.level < old:
        return f"⬇️ {line} · retour au niveau {rating.level}"
    return f"{line} · niveau {rating.level}" if key == "global" else line


def _progression_block(before, after, summary: dict) -> str:
    """Bloc « Progression » écrit par le router (exact par construction).
    Chaîne vide si la partie n'entre pas dans la saison (fiche ignorée)."""
    if after.n_games == before.n_games:
        return ""
    first = before.n_games == 0
    lines = ["🎮 Progression — saison 1 lancée" if first
             else f"🎮 Progression — saison 1, partie {after.n_games}"]
    lines.append(_rating_line("global", before, after))
    if not first:
        # Thèmes dont l'épreuve décisive est la même : une seule ligne, segments
        # joints par « · », texte de l'épreuve une fois (ordre de LABELS).
        merged = {}
        for key in LABELS:
            gd = after.last_game[key]
            if key == "global" or round(gd.delta) == 0:
                continue
            merged.setdefault(gd.top.label, (gd.top, []))[1].append(
                _rating_line(key, before, after))
        for trial, segments in merged.values():
            lines.append(f"{' · '.join(segments)} : {_trial_text(trial)}")
    for badge in after.badges:
        if badge in before.badges:
            continue
        if badge == "Tueur de géant":
            gap = summary["elo_opponent"] - summary["elo_nico"]
            reason = f"victoire contre un adversaire à {summary['elo_opponent']} (+{gap})"
        else:
            reason = _BADGE_REASON[badge]
        lines.append(f"🏆 Badge débloqué : {badge} — {reason}")
    if not first and summary["opening"]:
        family = opening_family(summary["opening"])
        stats = after.openings.get((family, summary["nico_color"]))
        if stats:
            lines.append(
                f"📖 {family} ({_COLOR_FR[summary['nico_color']]}) : "
                f"{stats.wins} V, {stats.draws} N, {stats.losses} D — {stats.win_rate * 100:.0f} %"
            )
    return "\n".join(lines)


def _reply_start(p) -> tuple:
    """(numéro, couleur) du premier coup adverse après le coup de Nico en p."""
    if p.color == "white":
        return p.move_number, "black"
    return p.move_number + 1, "white"


def _explosive_lines(p, e, nico_color: str) -> list:
    """Faits moteur du coup explosif d'une position de sorte d : l'idée, les réponses
    humaines probables (Maia, Elo adverse), l'espérance face à un humain, la variante
    si l'adversaire joue la réponse la plus probable."""
    lines = [f"  explosif {_move_label(p.move_number, p.color, e.san)}!?"]
    facts = []
    # Matériel : pièce offerte (posée en prise) prioritaire sur le sacrifice de ligne.
    if e.offered:
        facts.append(f"offre {_PIECE_FR.get(e.san[0], 'le pion')} ({e.offered})")
    elif max(e.sacrifice, e.accepted):
        facts.append(f"sacrifie {max(e.sacrifice, e.accepted)} pion(s) sur la ligne")
    if e.forcing:
        facts.append("forçant : " + "/".join(_FORCING_FR[f] for f in e.forcing))
    if facts:
        lines.append("  " + " ; ".join(facts))
    top = e.replies[0]
    lines.append(f"  réponse humaine la plus probable : {top['san']} ({top['p'] * 100:.0f} %)")
    lines.append(f"  espérance face à un humain : Nico {e.expected:.0f} % "
                 f"(meilleur coup : {e.best_expected:.0f} %)")
    # Admis par la seule règle sprint 28 (sacrifice / piège) : c'est un pari.
    if e.expected - e.best_expected < _GAIN_MIN:
        lines.append("  pari : face à un humain l'espérance n'est pas meilleure que le meilleur coup")
    number, color = _reply_start(p)
    # Admis sans avantage clair (sacrifice accepté avec échec) : pas de variante.
    if e.evidence is not None:
        lines.append(f"  variante : {_format_line(e.trap_line_san, number, color)} "
                     f"({_EVIDENCE_FR[e.evidence]})")
        after = chess.Board(p.fen_before)
        after.push_san(e.san)
        lines.append(f"  faits : {_move_facts(after.fen(), e.trap_line_san, number, color)}")
        lines.append(f"  fin de variante : {_material_line(e.trap_end_fen, nico_color)}, "
                     f"% de gain Nico {e.trap_end_win:.0f} %")
        lines.append(f"  fin de variante, {_attacked_line(e.trap_end_fen)}")
    for reply in e.replies:
        lines.append(f"  si {reply['san']} ({reply['p'] * 100:.0f} %) : "
                     f"{_format_line(reply['line_san'], number, color)}, {reply['win']:.0f} % pour Nico")
    return lines


def _caption(index: int, critical, plies: list) -> str:
    p = critical.ply
    if critical.kind == "e":
        prev = plies[p.ply - 1]
        return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
                f"tournant après {_move_label(prev.move_number, prev.color, prev.san)}?, "
                f"joué {_move_label(p.move_number, p.color, p.san)} "
                f"(meilleur {_move_label(p.move_number, p.color, p.best_san)})")
    if critical.kind == "c":
        return (f"Position {index} — coup {p.move_number} : "
                f"{_move_label(p.move_number, p.color, p.san)}, seul bon coup — bien joué")
    if critical.kind == "d":
        return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
                f"joué {_move_label(p.move_number, p.color, p.san)}, "
                f"explosif {_move_label(p.move_number, p.color, critical.explosive.san)}!? "
                f"(meilleur {_move_label(p.move_number, p.color, p.best_san)})")
    return (f"Position {index} — coup {p.move_number} ({_COLOR_FR[p.color]}) : "
            f"joué {_move_label(p.move_number, p.color, p.san)}, "
            f"meilleur {_move_label(p.move_number, p.color, p.best_san)}")


# Début d'entrée « Position N — » en début de ligne (gras Markdown toléré) ;
# une ligne « Niveau : » clôt la dernière entrée.
_ENTRY_RE = re.compile(r"^\**Position (\d+)\**\s*[—–-]\**\s*", re.MULTILINE)
_LEVEL_RE = re.compile(r"^\**Niveau\b", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"[.!?…](?=\s|$)")

# Limite Telegram d'une légende de photo.
_CAPTION_MAX = 1024


def _fit_entry(entry: str, budget: int) -> str:
    """Entrée ≤ budget : coupée à la dernière phrase complète qui tient, puis « … »."""
    if len(entry) <= budget:
        return entry
    head = entry[:budget - 2]
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(head)]
    return (head[:ends[-1]] if ends else head).rstrip() + " …"


def _split_entries(text: str, images: list) -> tuple:
    """
    Déplace l'entrée « Position N » du LLM dans la légende de l'image N.

    Retourne (texte restant, images). Si une entrée 1…len(images) manque,
    texte et images sont rendus tels quels (pas de découpage partiel).
    """
    marks = list(_ENTRY_RE.finditer(text))
    found = {int(m.group(1)): m for m in marks}
    if not images or any(i not in found for i in range(1, len(images) + 1)):
        log.info("chess_caption_split FALLBACK images=%d entries=%s",
                 len(images), sorted(found))
        return text, images

    # Fin d'une entrée : début de l'entrée suivante, ligne « Niveau », ou fin du texte.
    bounds = [m.start() for m in marks] + [m.start() for m in _LEVEL_RE.finditer(text)]
    rest, cursor, captioned = [], 0, []
    for m in marks:
        n = int(m.group(1))
        if n > len(images):
            continue
        end = min([b for b in bounds if b > m.start()] + [len(text)])
        rest.append(text[cursor:m.start()])
        cursor = end
        entry = text[m.end():end].strip()
        factual = images[n - 1]["caption"]
        captioned.append((n, factual + "\n" + _fit_entry(entry, _CAPTION_MAX - len(factual) - 1)))
    rest.append(text[cursor:])

    new_images = [dict(img) for img in images]
    for n, caption in captioned:
        new_images[n - 1]["caption"] = caption
    remaining = re.sub(r"\n{3,}", "\n\n", "".join(rest)).strip()
    log.info("chess_caption_split OK images=%d", len(images))
    return remaining, new_images


class ChessExecutionRouter(BaseRouter):
    """
    Effecteur « coach d'échecs » du pipeline d'exécution.

    Args:
        llm_execution_router : LLMExecutionRouter — production de l'explication
        mempalace_bridge     : MempalaceBridge — relecture des fiches (bloc Progression)
    """

    def __init__(self, llm_execution_router, mempalace_bridge):
        self.llm_execution_router = llm_execution_router
        self.mempalace_bridge = mempalace_bridge

    def execute(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})

        # Plusieurs parties (sprint 42) : toutes analysées, réponse groupée.
        games = split_pgn(message)
        if len(games) > 1:
            return self._execute_many(games, metadata)

        analysis = analyze(message, message, config.stockfish_path, config.maia_models_dir)
        if analysis is None:
            log.warning("chess_router PGN unreadable")
            return self.llm_execution_router.execute({
                "op_type" : CognitiveOperation.REASONING.value,
                "content" : f"[PGN illisible : dis-le à Nico en une phrase.]\n\n{message}",
                "metadata": metadata,
            })
        return self._execute_game(analysis, message, metadata)

    def _execute_many(self, games: list[str], metadata: dict) -> dict:
        """Une analyse complète par partie, puis fusion en une seule réponse.

        Images concaténées (légende préfixée « Partie k — »), puis un bloc de
        texte par partie sous son titre ; une partie illisible tient une ligne.
        """
        texts, images, ok = [], [], 0
        for k, game in enumerate(games, 1):
            analysis = analyze(game, game, config.stockfish_path, config.maia_models_dir)
            if analysis is None:
                log.warning("chess_router PGN unreadable game=%d", k)
                texts.append(f"Partie {k} — PGN illisible")
                continue
            result = self._execute_game(analysis, game, metadata)
            ok += 1
            h = analysis.headers
            title = f"Partie {k} — {h.get('White', '?')} – {h.get('Black', '?')} ({h.get('Result', '*')})"
            texts.append(f"{title}\n{result['text']}")
            images += [{**img, "caption": f"Partie {k} — {img['caption']}"} for img in result["images"]]
        log.info("chess_router multi games=%d ok=%d", len(games), ok)
        return {"text": "\n\n".join(texts), "images": images}

    def _execute_game(self, analysis, message: str, metadata: dict) -> dict:
        """Pipeline d'une partie analysée : diagrammes, fiche, progression, LLM."""
        # ── Diagrammes : un PNG par position critique ────────────────────────
        out_dir = Path(config.image_output_dir) / "chess"
        out_dir.mkdir(parents=True, exist_ok=True)
        images = []
        for i, critical in enumerate(analysis.critical, 1):
            out_path = out_dir / f"{uuid4().hex[:8]}_{i}.png"
            # Sorte d : 2e flèche (orange) pour le coup explosif.
            alt_uci = critical.explosive.uci if critical.kind == "d" else None
            render_position(critical.ply.fen_before, analysis.nico_color,
                            critical.ply.best_uci, str(out_path), alt_uci=alt_uci)
            # La variante est écrite sous la ligne factuelle dès la création de la
            # légende : elle survit au repli chess_caption_split FALLBACK.
            caption = _caption(i, critical, analysis.plies)
            variant = _variant_line(critical)
            if variant:
                caption += "\n" + variant
            images.append({"path": str(out_path), "caption": caption})

        # ── Fiche de partie (non bloquante) ──────────────────────────────────
        # Hash des coups seuls (pas des en-têtes) : le même PGN recopié sans
        # en-têtes reste la même partie → même doc_id → la fiche est remplacée.
        game_hash = hashlib.sha256(
            "".join(p.uci for p in analysis.plies).encode()
        ).hexdigest()[:16]
        summary = summarize(analysis)
        try:
            write_chess_game(summary_text(analysis, summary), game_hash, extra=summary)
            log.info("chess_game_write OK hash=%s plies=%d", game_hash, len(analysis.plies))
        except Exception:
            log.exception("chess_game_write ERROR hash=%s", game_hash)

        # ── Progression (non bloquante) : profil avant / après cette partie ──
        # Recalculé depuis les fiches (la courante est en base depuis l'écriture).
        block, history = "", None
        try:
            games = self.mempalace_bridge.load_chess_games()
            before = build_profile([g for g in games if g["id"] != f"chess_game_{game_hash}"])
            after = build_profile(games)
            block = _progression_block(before, after, summary)
            if block:
                history = _history_line(after)
                log.info("chess_progression OK games=%d global=%d",
                         after.n_games, round(after.ratings["global"].value))
        except Exception:
            log.exception("chess_progression ERROR")

        enriched = self._build_enriched(analysis, message, _anchor(summary), summary, history)
        result = self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # Pas de skip_intent (Q4) : la partie doit aller en mémoire épisodique,
            # sous un intent imposé (le namer répondait « aucun », audit 05).
            # skip_history (tronçon 15) : les analyses passées en historique servaient
            # de moule au LLM ; l'échange reste écrit pour les questions de suivi.
            "metadata": {**metadata, "forced_intent_name": FORCED_INTENT_NAME,
                         "skip_history": True},
        })

        log.info("chess_router OK critical=%d images=%d", len(analysis.critical), len(images))
        # Chaque entrée « Position N » part en légende de son diagramme (tronçon 05).
        text, images = _split_entries(_to_english(result["text"]), images)
        moves_line = _moves_line(summary)
        if moves_line:
            text += "\n\n" + moves_line
        if block:
            text += "\n\n" + block
        return {"text": text, "images": images}

    def _build_enriched(self, analysis, message: str, anchor: str, summary: dict,
                        history: str | None = None) -> str:
        """Ancre de la partie, puis faits moteur en français, puis message original."""
        color = analysis.nico_color
        opening = summary["opening"]
        nico_plies = [p for p in analysis.plies if p.color == color]
        counts = ", ".join(
            f"{label} {sum(1 for p in nico_plies if p.quality == key)}" for key, label in _QUALITY_FR
        )

        lines = [anchor, f"[Analyse Stockfish de la partie — Nico joue les {_COLOR_FR[color]} "
                 f"({_SOURCE_FR[analysis.color_source]}) :"]
        lines += _header_lines(analysis.headers)
        lines.append(f"Compteurs Nico : {counts}")
        lines.append(_level_line(summary))
        if history:
            lines.append(history)
        for i, critical in enumerate(analysis.critical, 1):
            p = critical.ply
            tags = ", ".join(_TAG_FR.get(t, t) for t in p.tags) or "aucune"
            lines += [
                f"Position {i} ({_KIND_FR[critical.kind]}) — coup {p.move_number} :",
                f"  joué {_move_label(p.move_number, p.color, p.san)}, perte {p.loss:.0f} pts "
                f"de % de gain ({p.win_before:.0f} % → {p.win_after:.0f} %)",
                f"  meilleur {_move_label(p.move_number, p.color, p.best_san)}, "
                f"ligne : {_format_line(p.pv_san, p.move_number, p.color)}",
                f"  faits : {_move_facts(p.fen_before, p.pv_san, p.move_number, p.color)}",
                f"  étiquettes : {tags}, phase : {_PHASE_FR[p.phase]}",
                _pieces_line(p.fen_before),
                f"  {_material_line(p.fen_before, color)}",
                f"  {_attacked_line(p.fen_before)}",
                f"  évaluation : {_evaluation(p.win_before)} ({p.win_before:.0f} %)",
            ]
            if p.motifs:
                lines.append(f"  motifs : {', '.join(_motif_fr(m) for m in p.motifs)}")
            if critical.kind == "e":
                prev = analysis.plies[p.ply - 1]
                lines.append(f"  erreur adverse {_move_label(prev.move_number, prev.color, prev.san)} : "
                             f"perte {prev.loss:.0f} pts "
                             f"(meilleur {_move_label(prev.move_number, prev.color, prev.best_san)})")
            if critical.kind in ("c", "e"):
                lines.append(f"  variante : {_format_line(critical.line_san, p.move_number, p.color)} "
                             f"({_EVIDENCE_FR[critical.evidence]})")
                lines.append(f"  faits : {_move_facts(p.fen_before, critical.line_san, p.move_number, p.color)}")
            if critical.kind == "d":
                lines += _explosive_lines(p, critical.explosive, color)
        block = "\n".join(lines) + "]"

        elo = analysis.headers.get("WhiteElo" if color == "white" else "BlackElo", "")
        player = f"joueur d'environ {elo} Elo" if elo and elo != "?" else "joueur amateur"
        n = len(analysis.critical)
        consigne = (
            f"[Consigne : réponse COURTE à Nico, {player}. Format imposé : 1re ligne "
            f"exacte « {anchor} » ; puis une entrée pour chacune des {n} positions, de "
            f"Position 1 à Position {n}, aucune omise (Nico voit les diagrammes du même "
            "numéro), 1 à 3 phrases et 400 caractères : l'idée générale de la position "
            "seulement (plan, pièce faible, roi exposé…) d'après la ligne « évaluation », les "
            "motifs et le but du meilleur coup (d'après ses faits) ; n'énumère pas les coups "
            "de la variante : elle est affichée sous le diagramme ; au plus un chiffre "
            "réduit à « 50 % → 37 % », ou aucun ; chaque entrée commence en début de ligne par "
            "« Position N — » et ne recopie pas la ligne « coup … joué … meilleur … » "
            "(elle est déjà sous le diagramme) ; puis une ligne « Niveau : » de 2 phrases (mal joué, "
            "passif, solide ou brillant), justifiée par la ligne « Niveau (données) » et, si "
            "présente, par la ligne « Historique (données) ». Rien "
            "d'autre : pas de section « ce qui se passe » ni « pourquoi ». Utilise "
            "uniquement les coups et lignes fournis ci-dessus ; n'invente aucun coup "
            "ni évaluation, ni emplacement de pièce : fie-toi à la liste des pièces. "
            "Ne décris aucune attaque, défense, menace ou colonne absente des lignes "
            "matériel / attaquées / faits. Ne recopie ni ne paraphrase « matériel égal » "
            "ou « aucune attaquée ». Notation anglaise : N, B, R, Q, K.]"
        )
        parts = [block, consigne]
        if opening:
            parts.append(
                f"[Consigne : ouverture jouée : {opening.replace('-', ' ')}. Quand c'est "
                "pertinent, relie la position aux idées classiques de cette ouverture en une "
                "demi-phrase. Un gambit d'ouverture choisi par Nico est un choix assumé, "
                "pas une faute à corriger.]"
            )
        if any(c.kind == "e" for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque tournant, nomme l'erreur adverse et montre la "
                "variante qui la punit (coups fournis).]"
            )
        if any(c.kind == "d" for c in analysis.critical):
            parts.append(
                "[Consigne : pour chaque occasion explosive : l'idée en une phrase ; la "
                "variante si l'adversaire joue la réponse humaine la plus probable (coups fournis, rien "
                "au-delà) et l'avantage atteint (critère fourni), expliqué par les pièces "
                "protégées / vulnérables de la fin de variante ; quelles réponses humaines "
                "probables perdent et ce qu'elles coûtent à l'adversaire, d'après les lignes "
                "« si … ». Ne donne ni le coût, ni quand le tenter, et ne le présente jamais "
                "comme le meilleur coup. Si la ligne « pari » est présente, une demi-phrase "
                "la présente comme une idée risquée. Cette entrée peut dépasser 3 phrases.]"
            )
        if analysis.color_source == "default":
            parts.append(
                "[Consigne : signale que tu as supposé que Nico joue les blancs faute "
                "de pseudo, et qu'il peut préciser « je joue les noirs ».]"
            )
        return "\n".join(parts) + f"\n\n{message}"
