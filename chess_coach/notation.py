# aria/chess_coach/notation.py
#
# Traduction de la notation algébrique anglaise (SAN) vers la notation
# française : N→C (cavalier), B→F (fou), R→T (tour), Q→D (dame), K→R (roi).
# Les colonnes sont en minuscules, donc la substitution simultanée est sans
# collision ; « O-O » reste intact.

_SAN_TO_FR = str.maketrans({"N": "C", "B": "F", "R": "T", "Q": "D", "K": "R"})


def to_french(san: str) -> str:
    """Retourne le coup SAN en notation française (ex. « Nxe5 » → « Cxe5 »)."""
    return san.translate(_SAN_TO_FR)
