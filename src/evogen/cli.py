from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from evogen import __version__
from evogen.adapters.conformance import (
    run_subject_conformance,
    subject_conformance_failure_report,
)
from evogen.adapters.subjects import (
    discover_subject_entry_points,
    read_subject_stage,
    read_subject_status,
    run_subject_cycle,
    run_subject_progress,
    run_subject_stage,
)
from evogen.core.enums import StageName
from evogen.core.models import CycleResult
from evogen.schema import export_schemas
from evogen.storage.ledger import Ledger

app = typer.Typer(
    name="evogen",
    help="Evidence-driven outer-loop capability engineering for autonomous agents.",
    no_args_is_help=True,
)
subject_app = typer.Typer(help="Inspect installed subject adapters.")
app.add_typer(subject_app, name="subject")
console = Console()


def _print_result(result: object, *, json_output: bool = False) -> None:
    if json_output:
        if hasattr(result, "model_dump_json"):
            console.print_json(result.model_dump_json())
        else:
            console.print_json(json.dumps(result))
        return
    if isinstance(result, CycleResult):
        console.print(f"Verdict: [bold]{result.decision.verdict.value}[/bold]")
        console.print(f"Result: {Path(result.workspace) / 'cycle-result.json'}")
    else:
        console.print(f"Completed stage: [bold]{type(result).__name__}[/bold]")


@app.command()
def cycle(
    subject: str = typer.Option("microworld", "--subject"),
    workspace: Path = typer.Option(Path(".evogen-demo"), "--workspace", "-w"),
    clean: bool = typer.Option(False, "--clean"),
    until: str | None = typer.Option(None, "--until", help="Stop at a named stage."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run or resume the generic persisted evolution cycle."""
    if until is not None:
        try:
            StageName(until)
        except ValueError as exc:
            raise typer.BadParameter(f"Unknown stage {until!r}") from exc
    result = run_subject_progress(subject, workspace, clean=clean, until=until)
    _print_result(result, json_output=json_output)


@subject_app.command("list")
def subject_list_command(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List installed subject metadata without loading or composing plugins."""
    entries = discover_subject_entry_points()
    values = [
        {
            "name": entry.name,
            "value": str(getattr(entry, "value", "")),
            "distribution": str(
                getattr(getattr(entry, "dist", None), "name", "<unknown distribution>")
            ),
        }
        for entry in entries
    ]
    if json_output:
        console.print_json(json.dumps({"subjects": values}, sort_keys=True))
        return
    table = Table(title="Installed EvoGen subjects")
    table.add_column("Name")
    table.add_column("Distribution")
    table.add_column("Entry point")
    for value in values:
        table.add_row(value["name"], value["distribution"], value["value"])
    console.print(table)


@subject_app.command("doctor")
def subject_doctor_command(
    name: str = typer.Argument(..., help="Installed subject name."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run host conformance checks and subject diagnostics without a persisted cycle."""
    try:
        report = run_subject_conformance(name, workspace=workspace)
    except Exception as exc:
        report = subject_conformance_failure_report(name, exc)
    if json_output:
        console.print_json(report.model_dump_json())
    else:
        console.print(f"Status: {report.status}")
        for check in report.checks:
            code = str(check.evidence.get("code", check.boundary_id))
            console.print(
                f"{check.boundary_id}: {check.status} [{code}] - {check.message}",
                markup=False,
            )
        console.print(f"Diagnostics: {len(report.diagnostics.items)}")
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("stage")
def stage_command(
    name: str = typer.Argument(..., help="One of the nine ordered stage names."),
    subject: str = typer.Option("microworld", "--subject"),
    workspace: Path = typer.Option(Path(".evogen-demo"), "--workspace", "-w"),
    clean: bool = typer.Option(False, "--clean"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Invoke one persisted stage through the cycle dispatcher."""
    try:
        selected = StageName(name)
    except ValueError as exc:
        raise typer.BadParameter(f"Unknown stage {name!r}") from exc
    result = run_subject_stage(subject, workspace, selected, clean=clean)
    _print_result(result, json_output=json_output)


@app.command()
def demo(
    workspace: Path = typer.Option(
        Path(".evogen-demo"),
        "--workspace",
        "-w",
        help="Directory for trajectories, candidates, artifacts, and lineage.",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        help="Delete an existing demo workspace before running.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the complete CycleResult JSON instead of a table.",
    ),
) -> None:
    """Run the complete offline microworld evolution proof."""
    result = run_subject_cycle("microworld", workspace, clean=clean)
    if json_output:
        console.print_json(result.model_dump_json())
        return

    baseline = result.experiment.baseline_metrics
    candidate = result.experiment.candidate_metrics
    table = Table(title="EvoGen microworld cycle")
    table.add_column("Metric")
    table.add_column("Baseline", justify="right")
    table.add_column("Candidate", justify="right")
    table.add_row(
        "Revealing success",
        f"{baseline.revealing_success_rate:.0%}",
        f"{candidate.revealing_success_rate:.0%}",
    )
    table.add_row(
        "Variant success",
        f"{baseline.variant_success_rate:.0%}",
        f"{candidate.variant_success_rate:.0%}",
    )
    table.add_row(
        "Regression success",
        f"{baseline.regression_success_rate:.0%}",
        f"{candidate.regression_success_rate:.0%}",
    )
    table.add_row(
        "Long-horizon success",
        f"{baseline.long_horizon_success_rate:.0%}",
        f"{candidate.long_horizon_success_rate:.0%}",
    )
    table.add_row("Blocked runs", str(baseline.blocked_run_count), str(candidate.blocked_run_count))
    console.print(table)
    console.print(f"Issue: [bold]{result.issue.title}[/bold]")
    console.print(f"Candidate: [bold]{result.candidate.candidate_id}[/bold]")
    console.print(f"Verdict: [bold]{result.decision.verdict.value}[/bold]")
    if result.retained_generation is not None:
        console.print(
            f"Retained generation: [bold]{result.retained_generation.generation_id}[/bold]"
        )
    console.print(f"Report: {Path(result.workspace) / 'report.md'}")
    console.print(f"Result: {Path(result.workspace) / 'cycle-result.json'}")


@app.command()
def status(
    subject: str = typer.Option("microworld", "--subject"),
    workspace: Path = typer.Option(Path(".evogen-demo"), "--workspace", "-w"),
) -> None:
    """Show generations and retained lineage in an EvoGen workspace."""
    completed_stages, next_stage_value = read_subject_status(subject, workspace)
    ledger_path = workspace.resolve() / "evogen.sqlite3"
    if not ledger_path.exists():
        raise typer.BadParameter(f"No EvoGen ledger at {ledger_path}")
    ledger = Ledger(ledger_path, read_only=True)
    generations = ledger.list_generations()
    table = Table(title="EvoGen generations")
    table.add_column("Generation")
    table.add_column("Parent")
    table.add_column("Subject")
    table.add_column("Source")
    for generation in generations:
        table.add_row(
            generation.generation_id,
            generation.parent_generation_id or "—",
            generation.subject,
            generation.source_ref,
        )
    console.print(table)
    completed = [stage.value for stage in completed_stages]
    next_stage = next_stage_value.value if next_stage_value is not None else "complete"
    console.print(f"Stages completed: {', '.join(completed) or 'none'}")
    console.print(f"Next stage: {next_stage}")
    lineage = ledger.lineage_rows()
    if lineage:
        console.print("Lineage:")
        for row in lineage:
            console.print(
                f"  {row['parent_generation_id']} -> {row['child_generation_id']} "
                f"via {row['candidate_id']}"
            )


@app.command("show-result")
def show_result(
    subject: str = typer.Option("microworld", "--subject"),
    workspace: Path = typer.Option(Path(".evogen-demo"), "--workspace", "-w"),
) -> None:
    """Pretty-print the last stored cycle result."""
    result = read_subject_stage(subject, workspace, StageName.SELECT)
    if not isinstance(result, CycleResult):
        raise typer.BadParameter("Stored select output is not a CycleResult")
    console.print_json(result.model_dump_json())


@app.command("export-schemas")
def export_schema_command(
    directory: Path = typer.Option(Path("schemas"), "--directory", "-d"),
) -> None:
    """Export JSON Schemas for EvoGen's public artifact contracts."""
    paths = export_schemas(directory)
    console.print(f"Wrote {len(paths)} schema files to {directory}")


@app.command()
def version() -> None:
    console.print(__version__)


def main() -> None:
    app()
