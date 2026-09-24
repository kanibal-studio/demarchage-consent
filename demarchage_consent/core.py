"""Évaluation de la validité d'un consentement de démarchage téléphonique (France).

Transposition d'une garde appliquée en production dans un centre d'appels depuis
août 2026. Cadre légal : loi n° 2025-594 du 30 juin 2025 (art. 13, réécrivant
l'art. L. 223-1 du code de la consommation — opt-in obligatoire depuis le
11/08/2026) et son décret d'application n° 2026-662 du 23 juillet 2026 (JO du
25/07/2026), art. R. 223-1 : le consentement doit être libre, spécifique, éclairé,
univoque et révocable ; sa durée ne peut excéder **un an** à compter du recueil,
sans renouvellement tacite ; la preuve numérique datée est conservée **trois ans**
à compter du recueil.

Fonction PURE : aucune I/O, aucune donnée d'entreprise, stdlib uniquement.
Sémantique fail-closed héritée de la production :

- une date de recueil absente, illisible ou dans le futur ne vaut JAMAIS « valide » ;
- aucune valeur de repli n'est inventée pour une date de recueil ;
- aucune entrée, quelle qu'elle soit, ne fait lever d'exception : le verdict est
  toujours l'un des quatre états (seul un ``now`` explicite et illisible — erreur
  de l'appelant, pas une donnée — lève ``ValueError``) ;
- le format de date accepté est défini ici, pas par la version de Python : la même
  chaîne rend le même verdict de Python 3.9 à 3.14.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Final, Literal, Optional, Union

DECREE_MAX_AGE_DAYS: Final = 365
DECREE_PROOF_RETENTION_DAYS: Final = 3 * 365
DECREE_REFERENCE: Final = (
    "Décret n° 2026-662 du 23 juillet 2026 (JO du 25/07/2026, en vigueur le "
    "11/08/2026), art. R. 223-1"
)
LAW_REFERENCE: Final = (
    "Loi n° 2025-594 du 30 juin 2025, art. 13 — art. L. 223-1 du code de la "
    "consommation (consentement préalable obligatoire depuis le 11/08/2026)"
)

VALIDE: Final = "valide"
EXPIRE: Final = "expire"
REVOQUE: Final = "revoque"
PREUVE_MANQUANTE: Final = "preuve_manquante"

ConsentStatus = Literal["valide", "expire", "revoque", "preuve_manquante"]
STATUSES: Final[tuple[ConsentStatus, ...]] = (VALIDE, EXPIRE, REVOQUE, PREUVE_MANQUANTE)

DateInput = Union[str, datetime, date, None]

# Grammaire des dates acceptées (sous-ensemble ISO 8601 / RFC 3339, identique sur
# toutes les versions de Python) :
#   AAAA-MM-JJ[(T| )HH[:MM[:SS[.ffffff]]][Z|±HH[:MM[:SS]]|±HHMM]]
# La fraction de seconde admet 1 à 9 chiffres (tronqués à la microseconde), le
# séparateur décimal « , » est toléré, « Z »/« z » désigne l'UTC. Tout ce que
# ``datetime.isoformat()`` produit (hors décalage fractionnaire) est accepté.
_ISO_RE: Final = re.compile(
    r"""
    ^
    (?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})
    (?:
        [Tt ]
        (?P<hour>[0-9]{2})
        (?:
            :(?P<minute>[0-9]{2})
            (?:
                :(?P<second>[0-9]{2})
                (?:[.,](?P<fraction>[0-9]{1,9}))?
            )?
        )?
        (?P<tz>[Zz]|[+-][0-9]{2}(?::[0-9]{2}(?::[0-9]{2})?|[0-9]{2})?)?
    )?
    $
    """,
    re.VERBOSE | re.ASCII,
)


def _parse_iso(text: str) -> Optional[datetime]:
    """Parse la grammaire ci-dessus ; ``None`` pour tout ce qui en sort."""
    match = _ISO_RE.match(text.strip())
    if match is None:
        return None
    parts = match.groupdict()
    fraction = parts["fraction"]
    microsecond = int((fraction + "000000")[:6]) if fraction else 0
    tzinfo: Optional[timezone] = None
    tz = parts["tz"]
    if tz is not None:
        if tz in ("Z", "z"):
            tzinfo = timezone.utc
        else:
            digits = tz[1:].replace(":", "")
            hours = int(digits[:2])
            minutes = int(digits[2:4] or "0")
            seconds = int(digits[4:6] or "0")
            if hours > 23 or minutes > 59 or seconds > 59:
                return None
            offset = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            tzinfo = timezone(-offset if tz[0] == "-" else offset)
    try:
        return datetime(
            int(parts["year"]),
            int(parts["month"]),
            int(parts["day"]),
            int(parts["hour"] or "0"),
            int(parts["minute"] or "0"),
            int(parts["second"] or "0"),
            microsecond,
            tzinfo,
        )
    except (ValueError, OverflowError):
        return None


def _parse_utc(value: DateInput) -> Optional[datetime]:
    """Normalise une entrée en ``datetime`` UTC ; une date naïve est explicitement UTC.

    Accepte une chaîne (grammaire ci-dessus), un ``datetime`` ou une ``date``
    (minuit UTC). Toute autre valeur, absente, illisible ou non représentable en
    UTC rend ``None`` — le contrat fail-closed (pas de repli, pas d'exception).
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    elif isinstance(value, str):
        maybe = _parse_iso(value)
        if maybe is None:
            return None
        parsed = maybe
    else:
        return None
    try:
        if parsed.utcoffset() is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError, TypeError):
        return None


# Marqueurs d'ABSENCE de révocation, tels que les exports CSV, les bases et
# pandas les écrivent. Comparés après ``strip().lower()``.
_NO_REVOCATION_TOKENS: Final = frozenset(
    {"", "false", "faux", "non", "no", "0", "n/a", "na", "none", "null", "nan", "nat", "-"}
)


def _revocation_signaled(value: object) -> bool:
    """Une révocation est-elle signalée, même sans date lisible ?

    Fail-closed : seules les absences explicites (``None``, ``False``, ``0``,
    ``NaN``/``NaT``, chaîne vide ou marqueur de :data:`_NO_REVOCATION_TOKENS`)
    valent « pas de révocation ». Toute autre valeur — ``True``, ``"oui"``, une
    date mal formée, un type inattendu — signale une révocation : une personne
    qui a dit non ne doit jamais redevenir appelable parce que la date de son
    refus est illisible.
    """
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _NO_REVOCATION_TOKENS
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not (value == 0 or value != value)  # 0 et NaN : absence
    if isinstance(value, (datetime, date)):
        # pandas.NaT est une sous-classe de datetime : absence, pas révocation.
        return _parse_utc(value) is not None or str(value) != "NaT"
    return True


def _ceiling(max_age_days: Optional[int]) -> int:
    """Plafond légal : resserrable par l'appelant, JAMAIS élargissable.

    ``None``, zéro, négatif ou illisible → plafond du décret ; toute valeur au-delà
    de 365 jours est ramenée à 365 : la loi borne la validité, pas la configuration.
    """
    if max_age_days is None or isinstance(max_age_days, bool):
        return DECREE_MAX_AGE_DAYS
    try:
        days = int(max_age_days)
    except (TypeError, ValueError, OverflowError):
        return DECREE_MAX_AGE_DAYS
    if days <= 0:
        return DECREE_MAX_AGE_DAYS
    return min(days, DECREE_MAX_AGE_DAYS)


def _resolve_now(now: DateInput) -> datetime:
    """``None`` → horloge courante UTC ; sinon la valeur DOIT être lisible.

    Un ``now`` explicite mais illisible est une erreur de programmation (replay,
    test), pas une donnée métier : la remplacer silencieusement par l'horloge
    réelle inventerait un repli et pourrait changer le verdict. On lève.
    """
    if now is None:
        return datetime.now(timezone.utc)
    current = _parse_utc(now)
    if current is None:
        raise ValueError(
            f"`now` illisible : {now!r} — attendu une date ISO 8601, un datetime, "
            "ou None pour l'horloge courante"
        )
    return current


def _shift(moment: datetime, days: int) -> Optional[datetime]:
    """``moment + days`` ; ``None`` si le résultat n'est pas représentable."""
    try:
        return moment + timedelta(days=days)
    except OverflowError:
        return None


@dataclass(frozen=True)
class ConsentAssessment:
    """Résultat structuré de :func:`assess_consent` (toutes les dates en UTC).

    - ``status`` : l'un des quatre états (voir :data:`STATUSES`) ;
    - ``evaluated_at`` : l'instant de référence (``now``) ;
    - ``collected_at`` / ``revoked_at`` : les dates telles que lues, ``None`` si
      absentes ou illisibles (une révocation illisible rend quand même
      ``revoque`` avec ``revoked_at=None``) ;
    - ``max_age_days`` : le plafond effectivement appliqué (≤ 365) ;
    - ``expires_at`` : dernier instant de validité (recueil + plafond), ``None``
      sans date de recueil lisible ;
    - ``proof_retention_until`` : fin de l'obligation de conservation de la preuve
      (recueil + trois ans), ``None`` sans date de recueil lisible ;
    - ``days_remaining`` : jours entiers restants avant expiration, uniquement
      quand le consentement est ``valide`` (sinon ``None``).
    """

    status: ConsentStatus
    evaluated_at: datetime
    collected_at: Optional[datetime]
    revoked_at: Optional[datetime]
    max_age_days: int
    expires_at: Optional[datetime]
    proof_retention_until: Optional[datetime]
    days_remaining: Optional[int]

    @property
    def is_valid(self) -> bool:
        """``True`` uniquement pour l'état ``valide``."""
        return self.status == VALIDE

    def to_dict(self) -> dict[str, object]:
        """Représentation sérialisable (dates en ISO 8601 UTC), ex. pour du JSON."""

        def iso(moment: Optional[datetime]) -> Optional[str]:
            return None if moment is None else moment.isoformat()

        return {
            "status": self.status,
            "is_valid": self.is_valid,
            "evaluated_at": iso(self.evaluated_at),
            "collected_at": iso(self.collected_at),
            "revoked_at": iso(self.revoked_at),
            "max_age_days": self.max_age_days,
            "expires_at": iso(self.expires_at),
            "proof_retention_until": iso(self.proof_retention_until),
            "days_remaining": self.days_remaining,
            "reference": DECREE_REFERENCE,
        }


def assess_consent(
    collected_at: DateInput,
    *,
    now: DateInput = None,
    revoked_at: DateInput = None,
    max_age_days: Optional[int] = None,
) -> ConsentAssessment:
    """Évalue un consentement et rend un :class:`ConsentAssessment` complet.

    Ordre de décision (le premier critère vérifié l'emporte) :

    1. ``revoque`` : une révocation est signalée — datée lisible, ou présente
       mais illisible (``True``, ``"oui"``, date mal formée…) ; seules les
       absences explicites (``None``, ``False``, ``0``, ``""``, ``"false"``,
       ``"non"``, ``"n/a"``, ``NaN``/``NaT``…) n'en sont pas. Elle prime tout, y
       compris une preuve de recueil absente : la personne a dit non, on ne
       re-sollicite pas son consentement ;
    2. ``preuve_manquante`` : date de recueil absente, illisible ou postérieure à
       ``now`` (une preuve datée du futur n'est pas recevable) — fail-closed ;
    3. ``expire`` : la preuve est plus ancienne que le plafond ;
    4. ``valide`` : sinon (le jour anniversaire du plafond est encore valide).

    Une date naïve est interprétée comme UTC. ``now`` sert aux tests et aux
    replays : ``None`` (défaut) prend l'horloge courante UTC ; une valeur
    explicite illisible lève ``ValueError``.
    """
    current = _resolve_now(now)
    ceiling = _ceiling(max_age_days)
    collected = _parse_utc(collected_at)
    revoked = _parse_utc(revoked_at)

    expires_at = None if collected is None else _shift(collected, ceiling)
    retention = None if collected is None else _shift(collected, DECREE_PROOF_RETENTION_DAYS)

    status: ConsentStatus
    if revoked is not None or _revocation_signaled(revoked_at):
        status = REVOQUE
    elif collected is None or collected > current:
        status = PREUVE_MANQUANTE
    elif current - collected > timedelta(days=ceiling):
        status = EXPIRE
    else:
        status = VALIDE

    days_remaining = None
    if status == VALIDE and expires_at is not None:
        days_remaining = (expires_at - current).days

    return ConsentAssessment(
        status=status,
        evaluated_at=current,
        collected_at=collected,
        revoked_at=revoked,
        max_age_days=ceiling,
        expires_at=expires_at,
        proof_retention_until=retention,
        days_remaining=days_remaining,
    )


def evaluate_consent(
    collected_at: DateInput,
    *,
    now: DateInput = None,
    revoked_at: DateInput = None,
    max_age_days: Optional[int] = None,
) -> ConsentStatus:
    """Évalue la validité d'un consentement et rend l'un des quatre états.

    - ``valide`` : preuve datée lisible, non révoquée, âge ≤ plafond ;
    - ``expire`` : preuve datée lisible mais plus ancienne que le plafond ;
    - ``revoque`` : une révocation est signalée, lisible ou non (elle prime
      tout ; seules les absences explicites n'en sont pas, voir
      :func:`assess_consent`) ;
    - ``preuve_manquante`` : date absente, illisible ou dans le futur — ce n'est
      pas une preuve recevable. Fail-closed, sans repli.

    Raccourci de :func:`assess_consent` (même logique, même ordre de décision) ;
    voir celle-ci pour les dates d'expiration et de conservation de la preuve.
    """
    return assess_consent(
        collected_at, now=now, revoked_at=revoked_at, max_age_days=max_age_days
    ).status
