"""Évaluation de la validité d'un consentement de démarchage téléphonique (France).

Transposition fidèle d'une garde appliquée en production dans un centre d'appels
depuis août 2026. Décret n° 2026-662 du 23 juillet 2026 (JO du 25/07, en vigueur
le 11/08/2026), art. R. 223-1 : le consentement au démarchage téléphonique doit
être libre, spécifique, clair et révocable, valable un an au maximum à compter de
son recueil, avec preuve numérique datée conservée trois ans.

Fonction PURE : aucune I/O, aucune donnée d'entreprise, stdlib uniquement.
Sémantique fail-closed héritée de la production : une date de recueil absente ou
illisible ne vaut JAMAIS « valide », et aucune valeur de repli n'est inventée.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

DECREE_MAX_AGE_DAYS = 365
DECREE_PROOF_RETENTION_DAYS = 3 * 365
DECREE_REFERENCE = (
    "Décret n° 2026-662 du 23 juillet 2026 (JO du 25/07/2026, en vigueur le "
    "11/08/2026), art. R. 223-1"
)

VALIDE = "valide"
EXPIRE = "expire"
REVOQUE = "revoque"
PREUVE_MANQUANTE = "preuve_manquante"

DateInput = Union[str, datetime, None]


def _parse_utc(value: DateInput) -> Optional[datetime]:
    """Parse une date ISO 8601 vers l'UTC ; une date naïve est explicitement UTC.

    Toute valeur absente ou illisible rend ``None`` — le contrat fail-closed
    (pas de repli, pas d'exception : l'appelant reçoit PREUVE_MANQUANTE).
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ceiling(max_age_days: Optional[int]) -> int:
    """Plafond légal : resserrable par l'appelant, JAMAIS élargissable.

    ``None``, zéro ou négatif → plafond du décret ; toute valeur au-delà de
    365 jours est ramenée à 365 : la loi borne la validité, pas la configuration.
    """
    if max_age_days is None:
        return DECREE_MAX_AGE_DAYS
    try:
        days = int(max_age_days)
    except (TypeError, ValueError):
        return DECREE_MAX_AGE_DAYS
    if days <= 0:
        return DECREE_MAX_AGE_DAYS
    return min(days, DECREE_MAX_AGE_DAYS)


def evaluate_consent(
    collected_at: DateInput,
    *,
    now: DateInput = None,
    revoked_at: DateInput = None,
    max_age_days: Optional[int] = None,
) -> str:
    """Évalue la validité d'un consentement et rend l'un des quatre états.

    - ``valide`` : preuve datée lisible, non révoquée, âge ≤ plafond ;
    - ``expire`` : preuve datée lisible mais plus ancienne que le plafond ;
    - ``revoque`` : une révocation datée lisible existe (elle prime tout) ;
    - ``preuve_manquante`` : date absente/illisible — OU dans le futur, ce qui
      n'est pas une preuve recevable. Fail-closed, sans repli.

    Une date naïve est interprétée comme UTC. ``now`` sert aux tests et aux
    replays : par défaut l'heure courante UTC.
    """
    collected = _parse_utc(collected_at)
    if collected is None:
        return PREUVE_MANQUANTE
    current = _parse_utc(now)
    if current is None:
        current = datetime.now(timezone.utc)
    if collected > current:
        return PREUVE_MANQUANTE
    revoked = _parse_utc(revoked_at)
    if revoked is not None:
        return REVOQUE
    if current - collected > timedelta(days=_ceiling(max_age_days)):
        return EXPIRE
    return VALIDE
