"""Une révocation signalée mais illisible vaut révocation (fail-closed).

Avant 0.2.0, ``revoked_at=True``, ``"oui"`` ou une date mal formée étaient ignorés
et le verdict pouvait rester ``valide`` : une personne qui a dit non redevenait
appelable. Seules les absences explicites ne sont pas des révocations.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from demarchage_consent import REVOQUE, VALIDE, assess_consent, evaluate_consent
from demarchage_consent.core import _NO_REVOCATION_TOKENS

UTC = timezone.utc
NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)
COLLECTED = NOW - timedelta(days=30)  # preuve lisible et récente : sans révocation → valide


@pytest.mark.parametrize(
    "signal",
    [
        True,
        "true",
        "TRUE",
        "oui",
        "yes",
        "1",
        "revoque",
        "2026-13-45",
        "2026-09-10 ??",
        "garbage",
        1,
        2.5,
        float("inf"),
        ["2026-09-10"],
        b"2026-09-10",
        object(),
    ],
)
def test_revocation_illisible_vaut_revocation(signal: object) -> None:
    status = evaluate_consent(COLLECTED, now=NOW, revoked_at=signal)  # type: ignore[arg-type]
    assert status == REVOQUE
    assessment = assess_consent(COLLECTED, now=NOW, revoked_at=signal)  # type: ignore[arg-type]
    assert assessment.status == REVOQUE
    assert assessment.days_remaining is None


@pytest.mark.parametrize(
    "absence",
    [
        None,
        False,
        0,
        0.0,
        float("nan"),
        "",
        "   ",
        "false",
        "FALSE",
        "Faux",
        "non",
        "no",
        "0",
        "n/a",
        "N/A",
        "na",
        "None",
        "null",
        "NaN",
        "NaT",
        "-",
    ],
)
def test_absence_explicite_n_est_pas_une_revocation(absence: object) -> None:
    assert evaluate_consent(COLLECTED, now=NOW, revoked_at=absence) == VALIDE  # type: ignore[arg-type]


def test_revocation_illisible_garde_revoked_at_a_none() -> None:
    assessment = assess_consent(COLLECTED, now=NOW, revoked_at="oui")
    assert assessment.status == REVOQUE
    assert assessment.revoked_at is None
    assert assessment.to_dict()["revoked_at"] is None


def test_revocation_lisible_inchangee() -> None:
    assessment = assess_consent(COLLECTED, now=NOW, revoked_at=date(2026, 9, 10))
    assert assessment.status == REVOQUE
    assert assessment.revoked_at == datetime(2026, 9, 10, tzinfo=UTC)


@given(signal=st.text().filter(lambda text: text.strip().lower() not in _NO_REVOCATION_TOKENS))
def test_toute_chaine_non_neutre_revoque(signal: str) -> None:
    assert evaluate_consent(COLLECTED, now=NOW, revoked_at=signal) == REVOQUE
