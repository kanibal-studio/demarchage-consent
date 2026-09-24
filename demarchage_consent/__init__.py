"""demarchage-consent — validité du consentement au démarchage téléphonique (FR)."""

from .core import (
    DECREE_MAX_AGE_DAYS,
    DECREE_PROOF_RETENTION_DAYS,
    DECREE_REFERENCE,
    EXPIRE,
    LAW_REFERENCE,
    PREUVE_MANQUANTE,
    REVOQUE,
    STATUSES,
    VALIDE,
    ConsentAssessment,
    ConsentStatus,
    assess_consent,
    evaluate_consent,
)

__all__ = [
    "DECREE_MAX_AGE_DAYS",
    "DECREE_PROOF_RETENTION_DAYS",
    "DECREE_REFERENCE",
    "EXPIRE",
    "LAW_REFERENCE",
    "PREUVE_MANQUANTE",
    "REVOQUE",
    "STATUSES",
    "VALIDE",
    "ConsentAssessment",
    "ConsentStatus",
    "__version__",
    "assess_consent",
    "evaluate_consent",
]

# Source unique de vérité pour la version : pyproject.toml la lit (dynamic) et le
# workflow de release refuse un tag qui ne lui correspond pas.
__version__ = "0.2.0"
