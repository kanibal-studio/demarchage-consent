"""Contrat de la garde d'âge — sémantique héritée du code de production."""

from datetime import date, datetime, timedelta, timezone

import pytest

from demarchage_consent import (
    DECREE_MAX_AGE_DAYS,
    DECREE_PROOF_RETENTION_DAYS,
    EXPIRE,
    PREUVE_MANQUANTE,
    REVOQUE,
    STATUSES,
    VALIDE,
    evaluate_consent,
)

NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)


def test_consentement_recent_valide() -> None:
    assert evaluate_consent("2026-09-01T10:00:00Z", now=NOW) == VALIDE


def test_limite_exacte_365_jours_valide() -> None:
    # Production : `<= timedelta(days=max)` — le jour anniversaire est encore valide.
    assert evaluate_consent(NOW - timedelta(days=365), now=NOW) == VALIDE


def test_une_microseconde_de_trop_expire() -> None:
    assert evaluate_consent(NOW - timedelta(days=365, microseconds=1), now=NOW) == EXPIRE


def test_un_jour_de_trop_expire() -> None:
    assert evaluate_consent(NOW - timedelta(days=366), now=NOW) == EXPIRE


def test_date_futur_preuve_manquante() -> None:
    # Une preuve postérieure à l'instant présent n'est pas une preuve recevable.
    assert evaluate_consent(NOW + timedelta(days=1), now=NOW) == PREUVE_MANQUANTE
    assert evaluate_consent(NOW + timedelta(microseconds=1), now=NOW) == PREUVE_MANQUANTE


def test_recueil_a_l_instant_meme_valide() -> None:
    assert evaluate_consent(NOW, now=NOW) == VALIDE


def test_date_absente_fail_closed() -> None:
    assert evaluate_consent(None, now=NOW) == PREUVE_MANQUANTE
    assert evaluate_consent("", now=NOW) == PREUVE_MANQUANTE
    assert evaluate_consent("   ", now=NOW) == PREUVE_MANQUANTE


def test_date_illisible_fail_closed_sans_repli() -> None:
    assert evaluate_consent("pas une date", now=NOW) == PREUVE_MANQUANTE
    assert evaluate_consent("17/45/2026", now=NOW) == PREUVE_MANQUANTE


@pytest.mark.parametrize(
    "value",
    [20260901, 1756720800, 1756720800.0, True, b"2026-09-01", object(), [], {}],
    ids=repr,
)
def test_types_inattendus_fail_closed(value: object) -> None:
    # Ni chaîne, ni datetime, ni date : aucune coercition, aucune exception.
    assert evaluate_consent(value, now=NOW) == PREUVE_MANQUANTE  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        "9999-12-31T23:59:59-23:59",  # conversion UTC hors plage (année 10000)
        "0001-01-01T00:00:00+23:59",  # conversion UTC hors plage (année 0)
        datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone(timedelta(hours=-23, minutes=-59))),
        datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=23, minutes=59))),
    ],
    ids=str,
)
def test_debordement_de_date_sans_exception(value: object) -> None:
    # Avant 0.2.0 ces entrées faisaient lever OverflowError, en violation du contrat.
    assert evaluate_consent(value, now=NOW) == PREUVE_MANQUANTE  # type: ignore[arg-type]


def test_extremes_representables() -> None:
    assert evaluate_consent(datetime.max, now=NOW) == PREUVE_MANQUANTE  # noqa: DTZ901 — futur
    assert evaluate_consent(datetime.min, now=NOW) == EXPIRE  # noqa: DTZ901
    assert evaluate_consent(datetime.min, now=datetime.min) == VALIDE  # noqa: DTZ901
    assert evaluate_consent(datetime.max, now=datetime.max) == VALIDE  # noqa: DTZ901


def test_revocation_prime_tout() -> None:
    assert (
        evaluate_consent("2026-09-01T00:00:00Z", now=NOW, revoked_at="2026-09-10T00:00:00Z")
        == REVOQUE
    )


def test_revocation_prime_expiration() -> None:
    assert (
        evaluate_consent(NOW - timedelta(days=900), now=NOW, revoked_at="2026-09-10T00:00:00Z")
        == REVOQUE
    )


def test_revocation_prime_preuve_manquante() -> None:
    # La personne a dit non : on ne rend pas « preuve_manquante », qui inviterait
    # à re-solliciter son consentement.
    assert evaluate_consent(None, now=NOW, revoked_at="2026-09-10T00:00:00Z") == REVOQUE
    assert evaluate_consent("n/a", now=NOW, revoked_at="2026-09-10T00:00:00Z") == REVOQUE
    assert (
        evaluate_consent(NOW + timedelta(days=3), now=NOW, revoked_at="2026-09-10T00:00:00Z")
        == REVOQUE
    )


def test_revocation_datee_du_futur_ou_anterieure_au_recueil_prime_quand_meme() -> None:
    # Côté sûr : une révocation datée, même incohérente, bloque l'appel.
    assert evaluate_consent(
        "2026-09-01T00:00:00Z", now=NOW, revoked_at=NOW + timedelta(days=1)
    ) == (REVOQUE)
    assert evaluate_consent("2026-09-01T00:00:00Z", now=NOW, revoked_at="2020-01-01") == REVOQUE


def test_revocation_illisible_ignoree() -> None:
    # Choix assumé et documenté : « n/a », « false »… ne sont pas des révocations.
    assert evaluate_consent("2026-09-01T00:00:00Z", now=NOW, revoked_at="n/a") == VALIDE
    assert evaluate_consent("2026-09-01T00:00:00Z", now=NOW, revoked_at="") == VALIDE


def test_plafond_resserrable() -> None:
    assert evaluate_consent("2026-08-01T00:00:00Z", now=NOW, max_age_days=30) == EXPIRE
    assert evaluate_consent("2026-09-01T00:00:00Z", now=NOW, max_age_days=30) == VALIDE


def test_plafond_jamais_elargissable() -> None:
    # 800 demandés → borné au plafond légal : 366 jours reste expiré.
    assert evaluate_consent(NOW - timedelta(days=366), now=NOW, max_age_days=800) == EXPIRE
    assert evaluate_consent(NOW - timedelta(days=364), now=NOW, max_age_days=800) == VALIDE


@pytest.mark.parametrize(
    "max_age_days",
    [0, -5, "abc", "", True, False, float("inf"), float("nan"), object()],
    ids=repr,
)
def test_plafond_invalide_retombe_sur_le_decret(max_age_days: object) -> None:
    assert (
        evaluate_consent(NOW - timedelta(days=200), now=NOW, max_age_days=max_age_days)  # type: ignore[arg-type]
        == VALIDE
    )
    assert (
        evaluate_consent(NOW - timedelta(days=366), now=NOW, max_age_days=max_age_days)  # type: ignore[arg-type]
        == EXPIRE
    )


def test_plafond_entier_sous_forme_de_chaine_ou_de_flottant() -> None:
    assert evaluate_consent(NOW - timedelta(days=40), now=NOW, max_age_days="30") == EXPIRE  # type: ignore[arg-type]
    assert evaluate_consent(NOW - timedelta(days=40), now=NOW, max_age_days=30.9) == EXPIRE  # type: ignore[arg-type]


def test_dates_naives_interpretees_utc() -> None:
    naive = datetime(2026, 9, 1, 12, 0, 0)  # noqa: DTZ001 — sans tzinfo, volontairement
    assert evaluate_consent(naive, now=NOW) == VALIDE
    assert evaluate_consent("2026-09-01T12:00:00", now=NOW) == VALIDE


def test_date_sans_heure_vaut_minuit_utc() -> None:
    assert evaluate_consent(date(2026, 9, 1), now=NOW) == VALIDE
    assert evaluate_consent(date(2026, 9, 16), now=NOW) == VALIDE  # minuit < 12:00
    assert evaluate_consent(date(2026, 9, 17), now=NOW) == PREUVE_MANQUANTE  # futur
    assert evaluate_consent("2025-09-16", now=NOW) == EXPIRE  # 365 jours et 12 h
    assert evaluate_consent("2025-09-16", now="2026-09-16") == VALIDE  # exactement 365 jours
    assert evaluate_consent("2025-09-15", now="2026-09-16") == EXPIRE


def test_date_avec_decalage_horaire() -> None:
    # 12:00 UTC = 14:00 UTC+2 : même instant, même verdict.
    assert evaluate_consent("2026-09-01T14:00:00+02:00", now=NOW) == VALIDE
    # Le décalage compte : 2025-09-16T12:00+02:00 = 10:00 UTC, soit 365 jours + 2 h.
    assert evaluate_consent("2025-09-16T12:00:00+02:00", now=NOW) == EXPIRE
    assert evaluate_consent("2025-09-16T12:00:00-02:00", now=NOW) == VALIDE


def test_now_sous_toutes_ses_formes() -> None:
    assert evaluate_consent("2026-09-01", now="2026-09-16T12:00:00Z") == VALIDE
    assert evaluate_consent("2026-09-01", now="2027-09-16") == EXPIRE
    assert evaluate_consent("2026-09-01", now=date(2027, 9, 1)) == VALIDE
    assert evaluate_consent("2026-09-01", now=date(2027, 9, 2)) == EXPIRE


def test_now_absent_prend_l_horloge_courante() -> None:
    assert evaluate_consent(datetime.now(timezone.utc) - timedelta(days=1)) == VALIDE
    assert evaluate_consent(datetime.now(timezone.utc) - timedelta(days=400)) == EXPIRE


@pytest.mark.parametrize("now", ["pas une date", "", 0, 1756720800, b"2026-09-01"], ids=repr)
def test_now_explicite_illisible_est_une_erreur(now: object) -> None:
    # Pas de repli silencieux sur l'horloge réelle : cela changerait le verdict d'un replay.
    with pytest.raises(ValueError, match="illisible"):
        evaluate_consent("2026-09-01", now=now)  # type: ignore[arg-type]


def test_constantes_du_decret() -> None:
    assert DECREE_MAX_AGE_DAYS == 365
    assert DECREE_PROOF_RETENTION_DAYS == 3 * 365
    assert STATUSES == (VALIDE, EXPIRE, REVOQUE, PREUVE_MANQUANTE)
    assert len(set(STATUSES)) == 4
