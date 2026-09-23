"""Ligne de commande : ``python -m demarchage_consent`` ou ``demarchage-consent``.

Code de sortie : 0 si le consentement est ``valide``, 1 pour tout autre état
(``expire``, ``revoque``, ``preuve_manquante``), 2 en cas d'erreur d'usage —
utilisable tel quel dans un script shell ou un pipeline de conformité.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Optional

from . import __version__
from .core import DECREE_MAX_AGE_DAYS, DECREE_REFERENCE, STATUSES, assess_consent

EXIT_VALID = 0
EXIT_NOT_VALID = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    """Construit l'analyseur d'arguments (exposé pour la documentation et les tests)."""
    parser = argparse.ArgumentParser(
        prog="demarchage-consent",
        description=(
            "Validité d'un consentement au démarchage téléphonique (France, "
            f"{DECREE_REFERENCE}). États possibles : {', '.join(STATUSES)}."
        ),
        epilog=(
            f"Code de sortie : {EXIT_VALID} si valide, {EXIT_NOT_VALID} sinon, "
            f"{EXIT_USAGE} en cas d'erreur d'usage. Les dates naïves sont lues en UTC."
        ),
    )
    parser.add_argument(
        "collected_at",
        help="date de recueil du consentement (ISO 8601, ex. 2026-03-01T10:00:00Z)",
    )
    parser.add_argument(
        "--revoked-at",
        metavar="DATE",
        help="date de révocation (ISO 8601) ; toute date lisible rend « revoque »",
    )
    parser.add_argument(
        "--now",
        metavar="DATE",
        help="instant de référence (ISO 8601) pour un replay ; défaut : horloge UTC courante",
    )
    parser.add_argument(
        "--max-age-days",
        metavar="N",
        type=int,
        help=f"plafond interne en jours, resserrable seulement (borné à {DECREE_MAX_AGE_DAYS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "sortie JSON détaillée (statut, expiration, jours restants, conservation de la preuve)"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} — {DECREE_REFERENCE}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Point d'entrée ; rend le code de sortie (voir le module)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        assessment = assess_consent(
            args.collected_at,
            now=args.now,
            revoked_at=args.revoked_at,
            max_age_days=args.max_age_days,
        )
    except ValueError as exc:  # --now explicite et illisible : erreur d'usage
        print(f"{parser.prog}: erreur : {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        print(json.dumps(assessment.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(assessment.status)
    return EXIT_VALID if assessment.is_valid else EXIT_NOT_VALID
