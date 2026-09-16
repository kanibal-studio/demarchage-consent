"""Contrat de la garde d'âge — sémantique héritée du code de production."""
from datetime import datetime, timedelta, timezone

from demarchage_consent.core import (
    DECREE_MAX_AGE_DAYS,
    EXPIRE,
    PREUVE_MANQUANTE,
    REVOQUE,
    VALIDE,
    evaluate_consent,
)

NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)


def test_consentement_recent_valide():
    assert evaluate_consent("2026-09-01T10:00:00Z", now=NOW) == VALIDE


def test_limite_exacte_365_jours_valide():
    # Production : `<= timedelta(days=max)` — le jour anniversaire est encore valide.
    assert evaluate_consent(NOW - timedelta(days=365), now=NOW) == VALIDE


def test_un_jour_de_trop_expire():
    assert evaluate_consent(NOW - timedelta(days=366), now=NOW) == EXPIRE


def test_date_futur_preuve_manquante():
    # Une preuve postérieure à l'instant présent n'est pas une preuve recevable.
    assert evaluate_consent(NOW + timedelta(days=1), now=NOW) == PREUVE_MANQUANTE


def test_date_absente_fail_closed():
    assert evaluate_consent(None, now=NOW) == PREUVE_MANQUANTE
    assert evaluate_consent("", now=NOW) == PREUVE_MANQUANTE


def test_date_illisible_fail_closed_sans_repli():
    assert evaluate_consent("pas une date", now=NOW) == PREUVE_MANQUANTE
    assert evaluate_consent("17/45/2026", now=NOW) == PREUVE_MANQUANTE


def test_revocation_prime_tout():
    assert (
        evaluate_consent(
            "2026-09-01T00:00:00Z", now=NOW, revoked_at="2026-09-10T00:00:00Z"
        )
        == REVOQUE
    )


def test_revocation_illisible_ignoree():
    assert (
        evaluate_consent("2026-09-01T00:00:00Z", now=NOW, revoked_at="n/a")
        == VALIDE
    )


def test_plafond_resserrable():
    assert evaluate_consent("2026-08-01T00:00:00Z", now=NOW, max_age_days=30) == EXPIRE


def test_plafond_jamais_elargissable():
    # 800 demandés → borné au plafond légal : 366 jours reste expiré.
    assert evaluate_consent(NOW - timedelta(days=366), now=NOW, max_age_days=800) == EXPIRE
    assert evaluate_consent(NOW - timedelta(days=364), now=NOW, max_age_days=800) == VALIDE


def test_plafond_invalide_retombe_sur_le_decret():
    assert evaluate_consent(NOW - timedelta(days=200), now=NOW, max_age_days=0) == VALIDE
    assert evaluate_consent(NOW - timedelta(days=200), now=NOW, max_age_days=-5) == VALIDE


def test_dates_natives_interpretees_utc():
    naive = datetime(2026, 9, 1, 12, 0, 0)  # sans tzinfo
    assert evaluate_consent(naive, now=NOW) == VALIDE


def test_date_avec_decalage_horaire():
    # 12:00 UTC = 14:00 UTC+2 : même instant, même verdict.
    assert evaluate_consent("2026-09-01T14:00:00+02:00", now=NOW) == VALIDE


def test_constantee_plafond_decret():
    assert DECREE_MAX_AGE_DAYS == 365
