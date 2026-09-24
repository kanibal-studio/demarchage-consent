"""Résultat structuré : expiration, jours restants, conservation de la preuve."""

import dataclasses
import json
from datetime import datetime, timedelta, timezone

import pytest

from demarchage_consent import (
    DECREE_PROOF_RETENTION_DAYS,
    DECREE_REFERENCE,
    EXPIRE,
    PREUVE_MANQUANTE,
    REVOQUE,
    VALIDE,
    ConsentAssessment,
    assess_consent,
    evaluate_consent,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)
COLLECTED = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)


def test_valide_expose_expiration_et_conservation() -> None:
    a = assess_consent("2026-09-01T10:00:00Z", now=NOW)
    assert a.status == VALIDE
    assert a.is_valid
    assert a.evaluated_at == NOW
    assert a.collected_at == COLLECTED
    assert a.revoked_at is None
    assert a.max_age_days == 365
    assert a.expires_at == COLLECTED + timedelta(days=365)
    assert a.proof_retention_until == COLLECTED + timedelta(days=DECREE_PROOF_RETENTION_DAYS)
    assert a.days_remaining == (a.expires_at - NOW).days == 349


def test_jours_restants_entiers() -> None:
    assert assess_consent(NOW - timedelta(days=365), now=NOW).days_remaining == 0
    assert assess_consent(NOW - timedelta(days=364, hours=12), now=NOW).days_remaining == 0
    assert assess_consent(NOW - timedelta(days=364), now=NOW).days_remaining == 1
    assert assess_consent(NOW, now=NOW).days_remaining == 365


def test_expire() -> None:
    a = assess_consent(NOW - timedelta(days=400), now=NOW)
    assert a.status == EXPIRE
    assert not a.is_valid
    assert a.expires_at == NOW - timedelta(days=35)
    assert a.days_remaining is None
    assert a.proof_retention_until == NOW - timedelta(days=400) + timedelta(days=1095)


def test_revoque() -> None:
    a = assess_consent("2026-09-01T10:00:00Z", now=NOW, revoked_at="2026-09-10")
    assert a.status == REVOQUE
    assert a.revoked_at == datetime(2026, 9, 10, tzinfo=UTC)
    assert a.collected_at == COLLECTED
    assert a.expires_at == COLLECTED + timedelta(days=365)
    assert a.days_remaining is None


def test_preuve_manquante() -> None:
    for value in (None, "", "n/a", NOW + timedelta(days=1)):
        a = assess_consent(value, now=NOW)
        assert a.status == PREUVE_MANQUANTE
        assert a.days_remaining is None
        assert a.proof_retention_until is None or value is not None


def test_preuve_manquante_pour_une_date_du_futur_garde_la_date_lue() -> None:
    # La date est lisible : on l'expose pour le diagnostic, mais elle ne vaut rien.
    a = assess_consent(NOW + timedelta(days=1), now=NOW)
    assert a.status == PREUVE_MANQUANTE
    assert a.collected_at == NOW + timedelta(days=1)


def test_plafond_resserre_applique_a_l_expiration() -> None:
    a = assess_consent("2026-09-01T10:00:00Z", now=NOW, max_age_days=30)
    assert a.max_age_days == 30
    assert a.expires_at == COLLECTED + timedelta(days=30)
    assert a.days_remaining == 14
    assert assess_consent("2026-09-01T10:00:00Z", now=NOW, max_age_days=800).max_age_days == 365


def test_expiration_non_representable_ne_casse_rien() -> None:
    a = assess_consent(datetime(9999, 12, 30, tzinfo=UTC), now=datetime(9999, 12, 31, tzinfo=UTC))
    assert a.status == VALIDE
    assert a.expires_at is None
    assert a.proof_retention_until is None
    assert a.days_remaining is None


def test_to_dict_serialisable_en_json() -> None:
    a = assess_consent("2026-09-01T10:00:00Z", now=NOW, revoked_at="2026-09-10T00:00:00Z")
    payload = json.loads(json.dumps(a.to_dict(), ensure_ascii=False))
    assert payload == {
        "status": "revoque",
        "is_valid": False,
        "evaluated_at": "2026-09-16T12:00:00+00:00",
        "collected_at": "2026-09-01T10:00:00+00:00",
        "revoked_at": "2026-09-10T00:00:00+00:00",
        "max_age_days": 365,
        "expires_at": "2027-09-01T10:00:00+00:00",
        "proof_retention_until": "2029-08-31T10:00:00+00:00",
        "days_remaining": None,
        "reference": DECREE_REFERENCE,
    }


def test_resultat_immuable() -> None:
    a = assess_consent("2026-09-01T10:00:00Z", now=NOW)
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.status = EXPIRE  # type: ignore[misc]
    assert isinstance(a, ConsentAssessment)


@pytest.mark.parametrize(
    ("collected", "revoked_at", "max_age_days"),
    [
        ("2026-09-01T10:00:00Z", None, None),
        (NOW - timedelta(days=400), None, None),
        ("2026-09-01T10:00:00Z", "2026-09-10", None),
        (None, None, None),
        ("2026-08-01T10:00:00Z", None, 30),
    ],
)
def test_evaluate_consent_est_le_raccourci_de_assess_consent(
    collected: "str | datetime | None", revoked_at: "str | None", max_age_days: "int | None"
) -> None:
    assert (
        evaluate_consent(collected, now=NOW, revoked_at=revoked_at, max_age_days=max_age_days)
        == assess_consent(
            collected, now=NOW, revoked_at=revoked_at, max_age_days=max_age_days
        ).status
    )
