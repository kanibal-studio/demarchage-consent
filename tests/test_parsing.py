"""Grammaire des dates : la même chaîne rend le même résultat de Python 3.9 à 3.14."""

from datetime import datetime, timedelta, timezone

import pytest

from demarchage_consent import PREUVE_MANQUANTE, assess_consent

NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
UTC = timezone.utc


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-09-01", datetime(2026, 9, 1, tzinfo=UTC)),
        ("2026-09-01T10", datetime(2026, 9, 1, 10, tzinfo=UTC)),
        ("2026-09-01T10:30", datetime(2026, 9, 1, 10, 30, tzinfo=UTC)),
        ("2026-09-01T10:30:15", datetime(2026, 9, 1, 10, 30, 15, tzinfo=UTC)),
        ("2026-09-01 10:30:15", datetime(2026, 9, 1, 10, 30, 15, tzinfo=UTC)),
        ("2026-09-01t10:30:15z", datetime(2026, 9, 1, 10, 30, 15, tzinfo=UTC)),
        ("2026-09-01T10:30:15Z", datetime(2026, 9, 1, 10, 30, 15, tzinfo=UTC)),
        ("2026-09-01T10:30:15.5Z", datetime(2026, 9, 1, 10, 30, 15, 500000, tzinfo=UTC)),
        ("2026-09-01T10:30:15.123Z", datetime(2026, 9, 1, 10, 30, 15, 123000, tzinfo=UTC)),
        # 9 chiffres (nanosecondes) tronqués à la microseconde ; virgule décimale tolérée.
        (
            "2026-09-01T10:30:15,123456789+02:00",
            datetime(2026, 9, 1, 8, 30, 15, 123456, tzinfo=UTC),
        ),
        ("2026-09-01T10:30:15+0200", datetime(2026, 9, 1, 8, 30, 15, tzinfo=UTC)),
        ("2026-09-01T10:30:15+02", datetime(2026, 9, 1, 8, 30, 15, tzinfo=UTC)),
        ("2026-09-01T10:30:15-05:30", datetime(2026, 9, 1, 16, 0, 15, tzinfo=UTC)),
        ("2026-09-01T10:30:15+00:00", datetime(2026, 9, 1, 10, 30, 15, tzinfo=UTC)),
        # Décalage avec secondes : ce que `datetime.isoformat()` produit pour un tel tzinfo.
        ("2026-09-01T10:30:15+02:00:30", datetime(2026, 9, 1, 8, 29, 45, tzinfo=UTC)),
        ("2026-09-01T23:59:59+23:59", datetime(2026, 9, 1, 0, 0, 59, tzinfo=UTC)),
        ("  2026-09-01T10:00:00Z\n", datetime(2026, 9, 1, 10, tzinfo=UTC)),
        ("2024-02-29", datetime(2024, 2, 29, tzinfo=UTC)),  # bissextile
        ("2026-09-01T00:00:00Z", datetime(2026, 9, 1, tzinfo=UTC)),
    ],
)
def test_formats_acceptes(text: str, expected: datetime) -> None:
    assert assess_consent(text, now=NOW).collected_at == expected


@pytest.mark.parametrize(
    "text",
    [
        "20260901",  # format ISO « basique » (accepté par fromisoformat ≥ 3.11 seulement)
        "2026-W36-1",  # date de semaine
        "2026-244",  # date ordinale
        "2026-9-1",  # mois/jour sans zéro
        "01/09/2026",  # format français
        "2026/09/01",
        "2026-09-01T10:00:00Z+02:00",  # deux fuseaux
        "2026-09-01Z",  # fuseau sans heure
        "2026-09-01T",  # séparateur sans heure
        "2026-09-01T10:00:00.1234567890Z",  # 10 chiffres de fraction
        "2026-09-01T10:00:00.Z",  # fraction vide
        "2026-09-01T10:00Z:00",
        "2026-09-01T10:00:00+2",  # décalage à un chiffre
        "2026-09-01T10:00:00+02:0",
        "2026-09-01T10:00:00+24:00",  # décalage hors plage
        "2026-09-01T10:00:00+02:60",
        "2026-09-01T10:00:00+02:00:60",
        "2026-09-01T10:00:00+020030",  # secondes de décalage sans deux-points
        "2026-09-01T10:00:00+02:00:30.5",  # décalage fractionnaire
        "2026-09-01T24:00:00",  # heure hors plage
        "2026-09-01T10:60:00",
        "2026-09-01T10:00:60",  # seconde intercalaire non représentable
        "2026-13-01",  # mois hors plage
        "2026-02-30",  # jour hors plage
        "2025-02-29",  # non bissextile
        "0000-01-01",  # année 0
        "٢٠٢٦-09-01",  # chiffres non ASCII
        "2026-09-01T10:00:00Z junk",
        "junk 2026-09-01",
        "2026-09-01T10:00:00Z\x00",
        "1756720800",  # timestamp Unix
        "Tue, 01 Sep 2026 10:00:00 GMT",  # RFC 2822
    ],
)
def test_formats_refuses_fail_closed(text: str) -> None:
    assessment = assess_consent(text, now=NOW)
    assert assessment.collected_at is None
    assert assessment.status == PREUVE_MANQUANTE


def test_le_fuseau_change_le_verdict_a_la_limite() -> None:
    limite = NOW - timedelta(days=365)  # 2025-09-16T12:00:00Z, encore valide
    assert assess_consent(limite.isoformat(), now=NOW).status == "valide"
    assert assess_consent("2025-09-16T13:00:00+01:00", now=NOW).status == "valide"
    assert assess_consent("2025-09-16T13:00:00+02:00", now=NOW).status == "expire"


def test_datetime_aware_normalise_en_utc() -> None:
    paris = timezone(timedelta(hours=2))
    assessment = assess_consent(datetime(2026, 9, 1, 14, 0, tzinfo=paris), now=NOW)
    assert assessment.collected_at == datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    assert assessment.collected_at is not None
    assert assessment.collected_at.tzinfo is UTC
