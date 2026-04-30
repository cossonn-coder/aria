# aria/cognition/context_builder.py
#
# Assemblage du contexte cognitif injecté dans le prompt LLM.
#
# Responsabilité unique : produire un bloc texte structuré à partir de
# trois sources mémoire (sémantique, intents actifs, épisodique),
# en respectant un budget tokens maximum.
#
# Cette fonction est STATELESS mais pas pure : elle appelle
# bridge.retrieve_semantic() qui effectue une requête ChromaDB.
# Mocker bridge dans les tests unitaires.
#
# Estimation tokens : math.ceil(len(text) / 4)
# Heuristique conservative (surestime légèrement) — aucune dépendance
# externe, coût CPU nul.

import math
from memory.mempalace_bridge import MempalaceBridge


def _estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def build_context_block(
    query: str,
    bridge: MempalaceBridge,
    active_intents: list,
    session_memories: dict,
    global_memories: dict | None = None,
    token_budget: int = 2000,
) -> str:
    """
    Assemble le bloc de contexte cognitif injectable dans un prompt LLM.

    Remplit le budget par priorité décroissante :
      1. Faits sémantiques stables (profil utilisateur)
      2. Intents actifs triés par salience décroissante
      3. Souvenirs épisodiques : session_memories en priorité (filtrés par
         intent_id), fallback sur global_memories si session sparse (< 3 hits)

    Args:
        query           : message utilisateur (requête vectorielle pour le sémantique)
        bridge          : MempalaceBridge injectable — appelle retrieve_semantic()
        active_intents  : liste d'Intent (depuis intent_engine.list_attention_active())
        session_memories: dict {"hits": [...]} filtré par intent_id — source primaire
        global_memories : dict {"hits": [...]} toutes rooms — fallback si session vide
        token_budget    : budget maximum en tokens estimés (défaut 2000)

    Returns:
        str — bloc texte multi-sections, prêt à injecter dans un prompt.
              Chaîne vide si toutes les sources sont vides.
    """
    remaining = token_budget
    sections = []

    # ── 1. Faits sémantiques stables (priorité max) ─────────────────────────
    semantic_hits = bridge.retrieve_semantic(query, n=5).get("hits", [])
    section = _build_semantic_section(semantic_hits, remaining)
    if section:
        sections.append(section)
        remaining -= _estimate_tokens(section)

    # ── 2. Intents actifs triés par salience décroissante ───────────────────
    sorted_intents = sorted(active_intents, key=lambda i: i.salience, reverse=True)
    section = _build_intents_section(sorted_intents, remaining)
    if section:
        sections.append(section)
        remaining -= _estimate_tokens(section)

    # ── 3. Souvenirs épisodiques — session prioritaire, global en fallback ──
    # session_memories contient les souvenirs filtrés par intent_id (pertinents).
    # Si la session est sparse (< 3 hits), on complète avec global_memories
    # en excluant les doublons pour ne pas répéter ce qu'on a déjà.
    session_hits = sorted(
        session_memories.get("hits", []),
        key=lambda h: h.get("distance", 1.0),
    )
    episodic_hits = session_hits
    if global_memories and len(session_hits) < 3:
        seen = {h.get("text", "") for h in session_hits}
        fallback = sorted(
            [h for h in global_memories.get("hits", []) if h.get("text", "") not in seen],
            key=lambda h: h.get("distance", 1.0),
        )
        episodic_hits = session_hits + fallback

    section = _build_episodic_section(episodic_hits, remaining)
    if section:
        sections.append(section)

    return "\n\n".join(sections)


def _build_semantic_section(hits: list, budget: int) -> str:
    if not hits:
        return ""
    header = "[Profil utilisateur stable]"
    lines = []
    used = _estimate_tokens(header + "\n")
    for hit in hits:
        text = hit.get("text", "").strip()
        if not text:
            continue
        line = f"- {text}"
        if used + _estimate_tokens(line + "\n") > budget:
            break
        lines.append(line)
        used += _estimate_tokens(line + "\n")
    if not lines:
        return ""
    return header + "\n" + "\n".join(lines)


def _build_intents_section(intents: list, budget: int) -> str:
    if not intents:
        return ""
    header = "[Projets actifs]"
    lines = []
    used = _estimate_tokens(header + "\n")
    for intent in intents:
        line = f"- {intent.name} (salience: {round(intent.salience, 2)})"
        if used + _estimate_tokens(line + "\n") > budget:
            break
        lines.append(line)
        used += _estimate_tokens(line + "\n")
    if not lines:
        return ""
    return header + "\n" + "\n".join(lines)


def _build_episodic_section(hits: list, budget: int) -> str:
    if not hits:
        return ""
    header = "[Souvenirs pertinents]"
    lines = []
    used = _estimate_tokens(header + "\n")
    for hit in hits:
        text = hit.get("text", "").strip()
        if not text:
            continue
        excerpt = text[:400]
        line = f"- {excerpt}"
        if used + _estimate_tokens(line + "\n") > budget:
            break
        lines.append(line)
        used += _estimate_tokens(line + "\n")
    if not lines:
        return ""
    return header + "\n" + "\n".join(lines)
