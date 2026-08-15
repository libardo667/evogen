from __future__ import annotations

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


def test_provisional_kae_normalizer_is_not_a_public_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    assert "normalize-kae" not in result.output
