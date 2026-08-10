from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from evogen import __version__
from evogen.demo.microworld.cycle import MicroworldEvolutionCycle
from evogen.integrations.kenshi.adapter import KenshiJsonlAdapter
from evogen.schema import export_schemas
from evogen.storage.ledger import Ledger

app = typer.Typer(
    name="evogen",
    help="Evidence-driven outer-loop capability engineering for autonomous agents.",
    no_args_is_help=True,
)
console = Console()


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
    result = MicroworldEvolutionCycle.prepare(workspace, clean=clean).run()
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
    workspace: Path = typer.Option(Path(".evogen-demo"), "--workspace", "-w"),
) -> None:
    """Show generations and retained lineage in an EvoGen workspace."""
    ledger_path = workspace.resolve() / "evogen.sqlite3"
    if not ledger_path.exists():
        raise typer.BadParameter(f"No EvoGen ledger at {ledger_path}")
    ledger = Ledger(ledger_path)
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
    workspace: Path = typer.Option(Path(".evogen-demo"), "--workspace", "-w"),
) -> None:
    """Pretty-print the last stored cycle result."""
    path = workspace.resolve() / "cycle-result.json"
    if not path.exists():
        raise typer.BadParameter(f"No result at {path}")
    console.print_json(json.dumps(json.loads(path.read_text(encoding="utf-8"))))


@app.command("normalize-kae")
def normalize_kae(
    source: Path = typer.Argument(..., exists=True, dir_okay=False),
    destination: Path = typer.Argument(..., dir_okay=False),
    generation_id: str = typer.Option(..., "--generation"),
    scenario_id: str = typer.Option(..., "--scenario"),
    run_id: str | None = typer.Option(None, "--run-id"),
    strict: bool = typer.Option(False, "--strict"),
) -> None:
    """Normalize a conservative KAE-like JSONL trace into EvoGen events."""
    events = KenshiJsonlAdapter().convert_to_file(
        source,
        destination,
        generation_id=generation_id,
        scenario_id=scenario_id,
        run_id=run_id,
        strict=strict,
    )
    console.print(f"Wrote {len(events)} normalized events to {destination}")


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
