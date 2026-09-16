"""demarchage-consent — validité du consentement au démarchage téléphonique (FR)."""
from .core import (
    DECREE_MAX_AGE_DAYS,
    DECREE_PROOF_RETENTION_DAYS,
    DECREE_REFERENCE,
    EXPIRE,
    PREUVE_MANQUANTE,
    REVOQUE,
    VALIDE,
    evaluate_consent,
)

__all__ = [
    "DECREE_MAX_AGE_DAYS",
    "DECREE_PROOF_RETENTION_DAYS",
    "DECREE_REFERENCE",
    "EXPIRE",
    "PREUVE_MANQUANTE",
    "REVOQUE",
    "VALIDE",
    "evaluate_consent",
]
__version__ = "0.1.0"
