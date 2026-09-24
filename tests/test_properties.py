"""Propriétés vérifiées par génération aléatoire (Hypothesis).

Ces tests encadrent le contrat fail-closed au-delà des exemples : aucune entrée ne
fait lever d'exception, la chaîne ISO et l'objet datetime rendent le même verdict,
et la règle d'âge est exacte à la microseconde près.
"""

import json
from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from demarchage_consent import (
    DECREE_MAX_AGE_DAYS,
    EXPIRE,
    PREUVE_MANQUANTE,
    REVOQUE,
    STATUSES,
    VALIDE,
    assess_consent,
    evaluate_consent,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)

# Instants UTC assez loin des bornes pour que « ± quelques siècles » reste représentable.
SAFE_INSTANTS = st.datetimes(
    min_value=datetime(1900, 1, 1),  # noqa: DTZ001 — Hypothesis exige des bornes naïves
    max_value=datetime(9000, 1, 1),  # noqa: DTZ001
    timezones=st.just(UTC),
)
OFFSETS = st.timedeltas(
    min_value=timedelta(hours=-23, minutes=-59), max_value=timedelta(hours=23, minutes=59)
).map(lambda delta: timezone(delta - timedelta(microseconds=delta.microseconds)))
WITHIN_CEILING = st.timedeltas(
    min_value=timedelta(0), max_value=timedelta(days=DECREE_MAX_AGE_DAYS)
)
BEYOND_CEILING = st.timedeltas(
    min_value=timedelta(days=DECREE_MAX_AGE_DAYS, microseconds=1), max_value=timedelta(days=36500)
)
ANYTHING = st.one_of(
    st.none(),
    st.text(),
    st.binary(),
    st.integers(),
    st.floats(),
    st.booleans(),
    st.dates(),
    st.datetimes(),
    st.datetimes(timezones=OFFSETS),
    st.lists(st.text(), max_size=2),
)


@settings(max_examples=400)
@given(collected=ANYTHING, revoked=ANYTHING, max_age=st.one_of(st.none(), st.integers(), ANYTHING))
def test_jamais_d_exception_quelle_que_soit_l_entree(
    collected: object, revoked: object, max_age: object
) -> None:
    status = evaluate_consent(collected, now=NOW, revoked_at=revoked, max_age_days=max_age)  # type: ignore[arg-type]
    assert status in STATUSES
    payload = assess_consent(collected, now=NOW, revoked_at=revoked, max_age_days=max_age)  # type: ignore[arg-type]
    assert payload.status == status
    json.dumps(payload.to_dict())  # toujours sérialisable


@given(now=ANYTHING)
def test_now_illisible_leve_valueerror_sinon_verdict(now: object) -> None:
    try:
        status = evaluate_consent("2026-09-01", now=now)  # type: ignore[arg-type]
    except ValueError:
        assert now is not None
    else:
        assert status in STATUSES


@given(now=SAFE_INSTANTS, age=WITHIN_CEILING)
def test_age_dans_le_plafond_est_valide(now: datetime, age: timedelta) -> None:
    assert evaluate_consent(now - age, now=now) == VALIDE


@given(now=SAFE_INSTANTS, age=BEYOND_CEILING)
def test_age_au_dela_du_plafond_est_expire(now: datetime, age: timedelta) -> None:
    assert evaluate_consent(now - age, now=now) == EXPIRE


@given(now=SAFE_INSTANTS, avance=st.timedeltas(min_value=timedelta(microseconds=1)))
def test_preuve_du_futur_jamais_valide(now: datetime, avance: timedelta) -> None:
    try:
        collected = now + avance
    except OverflowError:
        return
    assert evaluate_consent(collected, now=now) == PREUVE_MANQUANTE


@given(collected=ANYTHING, revoked=SAFE_INSTANTS, now=SAFE_INSTANTS)
def test_revocation_lisible_prime_toujours(
    collected: object, revoked: datetime, now: datetime
) -> None:
    assert evaluate_consent(collected, now=now, revoked_at=revoked) == REVOQUE  # type: ignore[arg-type]
    assert evaluate_consent(collected, now=now, revoked_at=revoked.isoformat()) == REVOQUE  # type: ignore[arg-type]


@given(collected=SAFE_INSTANTS, now=SAFE_INSTANTS, offset=OFFSETS)
def test_chaine_iso_et_objet_datetime_rendent_le_meme_verdict(
    collected: datetime, now: datetime, offset: timezone
) -> None:
    local = collected.astimezone(offset)
    reference = assess_consent(collected, now=now)
    for variant in (local, local.isoformat(), collected.isoformat(), collected.isoformat(sep=" ")):
        assessment = assess_consent(variant, now=now)
        assert assessment.status == reference.status
        assert assessment.collected_at == collected


@given(collected=SAFE_INSTANTS, now=SAFE_INSTANTS)
def test_z_et_offset_nul_sont_equivalents(collected: datetime, now: datetime) -> None:
    iso = collected.isoformat()
    assert iso.endswith("+00:00")
    zulu = iso[: -len("+00:00")] + "Z"
    assert assess_consent(zulu, now=now) == assess_consent(iso, now=now)


@given(days=st.integers())
def test_plafond_effectif_toujours_entre_1_et_365(days: int) -> None:
    effective = assess_consent(NOW, now=NOW, max_age_days=days).max_age_days
    assert 1 <= effective <= DECREE_MAX_AGE_DAYS
    assert effective == (min(days, DECREE_MAX_AGE_DAYS) if days > 0 else DECREE_MAX_AGE_DAYS)


@given(now=SAFE_INSTANTS, age=WITHIN_CEILING, plafond=st.integers(min_value=1, max_value=365))
def test_plafond_resserre_exact(now: datetime, age: timedelta, plafond: int) -> None:
    assessment = assess_consent(now - age, now=now, max_age_days=plafond)
    expected = VALIDE if age <= timedelta(days=plafond) else EXPIRE
    assert assessment.status == expected
    assert assessment.expires_at == now - age + timedelta(days=plafond)
    if expected == VALIDE:
        assert assessment.days_remaining is not None
        assert 0 <= assessment.days_remaining <= plafond
    else:
        assert assessment.days_remaining is None
