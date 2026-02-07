import sys

from normcore import AdmissibilityEvaluator
from normcore.cli import main as cli_main
from normcore.evaluator import AdmissibilityEvaluator as NamespacedEvaluator


def test_normcore_namespace_exports_evaluator():
    assert NamespacedEvaluator is AdmissibilityEvaluator


def test_normcore_cli_help_runs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["normcore"])
    assert cli_main() == 0
    output = capsys.readouterr().out
    assert "NormCore CLI" in output


def test_normcore_cli_version_runs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["normcore", "--version"])
    assert cli_main() == 0
    output = capsys.readouterr().out.strip()
    assert output


def test_normcore_cli_evaluate_runs(capsys):
    assert cli_main(["evaluate", "--text", "The deployment is blocked."]) == 0
    output = capsys.readouterr().out
    assert '"status"' in output
