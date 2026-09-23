"""Ligne de commande : sortie, codes de retour, JSON."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from demarchage_consent import DECREE_REFERENCE, __version__
from demarchage_consent.cli import EXIT_NOT_VALID, EXIT_USAGE, EXIT_VALID, main

NOW = "2026-09-16T12:00:00Z"
ROOT = Path(__file__).resolve().parent.parent


def test_valide_code_0(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["2026-09-01T10:00:00Z", "--now", NOW]) == EXIT_VALID
    assert capsys.readouterr().out == "valide\n"


def test_expire_code_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["2024-03-01T10:00:00Z", "--now", NOW]) == EXIT_NOT_VALID
    assert capsys.readouterr().out == "expire\n"


def test_revoque_code_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["2026-09-01", "--now", NOW, "--revoked-at", "2026-09-10"]) == EXIT_NOT_VALID
    assert capsys.readouterr().out == "revoque\n"


def test_preuve_manquante_code_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["pas une date", "--now", NOW]) == EXIT_NOT_VALID
    assert capsys.readouterr().out == "preuve_manquante\n"
    assert main(["", "--now", NOW]) == EXIT_NOT_VALID


def test_plafond_resserre() -> None:
    assert main(["2026-08-01", "--now", NOW, "--max-age-days", "30"]) == EXIT_NOT_VALID
    assert main(["2026-08-01", "--now", NOW, "--max-age-days", "800"]) == EXIT_VALID


def test_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["2026-09-01T10:00:00Z", "--now", NOW, "--json"]) == EXIT_VALID
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "valide"
    assert payload["is_valid"] is True
    assert payload["expires_at"] == "2027-09-01T10:00:00+00:00"
    assert payload["days_remaining"] == 349
    assert payload["reference"] == DECREE_REFERENCE


def test_now_illisible_code_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["2026-09-01", "--now", "hier"]) == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "illisible" in captured.err


def test_plafond_non_entier_code_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["2026-09-01", "--max-age-days", "trente"])
    assert exc.value.code == EXIT_USAGE


def test_sans_argument_code_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == EXIT_USAGE


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_python_dash_m() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "demarchage_consent", "2026-09-01T10:00:00Z", "--now", NOW],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == EXIT_VALID, result.stderr
    assert result.stdout == "valide\n"

    result = subprocess.run(
        [sys.executable, "-m", "demarchage_consent", "2024-03-01", "--now", NOW, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == EXIT_NOT_VALID, result.stderr
    assert json.loads(result.stdout)["status"] == "expire"
