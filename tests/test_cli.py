from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from evogen.cli import app


runner = CliRunner()


def test_demo_cli_runs_complete_cycle(tmp_path):
    workspace = tmp_path / "cli-demo"
    result = runner.invoke(
        app,
        ["demo", "--workspace", str(workspace), "--clean"],
    )

    assert result.exit_code == 0, result.output
    assert "Verdict: retain" in result.output
    assert (workspace / "report.md").exists()


def test_status_cli_reads_lineage(tmp_path):
    workspace = tmp_path / "cli-status"
    first = runner.invoke(app, ["demo", "--workspace", str(workspace), "--clean"])
    assert first.exit_code == 0, first.output
    status = runner.invoke(app, ["status", "--workspace", str(workspace)])
    assert status.exit_code == 0, status.output
    assert "gen-microworld-0001" in status.output
    assert "Lineage" in status.output


def test_normalize_kae_cli(tmp_path):
    source = Path(__file__).parent / "fixtures" / "kenshi_missing_close.raw.jsonl"
    destination = tmp_path / "normalized.jsonl"
    result = runner.invoke(
        app,
        [
            "normalize-kae",
            str(source),
            str(destination),
            "--generation",
            "kae-gen",
            "--scenario",
            "missing-close",
            "--strict",
        ],
    )
    assert result.exit_code == 0, result.output
    assert destination.exists()
    assert len(destination.read_text().splitlines()) == 11
