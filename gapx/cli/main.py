"""GAPx command line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..config.loader import load_config, load_manifest
from ..runner import Runner

app = typer.Typer(help="GA-based Integrated Gap-Filling & Pruning Framework")
console = Console()


def _print_config_summary(run_path: Path) -> None:
    bundle = load_config(run_path)
    table = Table(title=f"GAPx Run: {bundle.run.name}")
    table.add_column("Section")
    table.add_column("Details")
    table.add_row("Seed", str(bundle.run.seed))
    table.add_row("Output Dir", str(bundle.run.output_dir))
    table.add_row("Tasks", str(len(bundle.tasks.tasks) if bundle.tasks else 0))
    table.add_row("GA Generations", str(bundle.ga.generations if bundle.ga else "?"))
    table.add_row("Population", str(bundle.ga.population if bundle.ga else "?"))
    console.print(table)


@app.command()
def validate(
    run: Path = typer.Option(..., exists=True, dir_okay=False, help="Root run configuration"),
) -> None:
    """Validate a configuration bundle and print a summary."""

    bundle = load_config(run)
    console.print(f"[green]Configuration '{bundle.run.name}' validated successfully.[/green]")
    _print_config_summary(run)


@app.command()
def run(
    run: Path = typer.Option(..., exists=True, dir_okay=False, help="Root run configuration"),
    resume: bool = typer.Option(False, help="Resume from previous manifest"),
) -> None:
    """Execute the GA workflow using the provided configuration."""

    bundle = load_config(run)
    runner = Runner(bundle)
    result = runner.run(resume=resume)
    manifest_path = result.manifest_path or Path(bundle.run.output_dir) / "manifest.json"
    console.print(f"[green]Run completed. Manifest saved to {manifest_path}[/green]")


@app.command()
def report(
    run: Path = typer.Option(..., exists=True, help="Manifest or run directory"),
    format: Optional[str] = typer.Option("html", help="Output format (html/json)"),
) -> None:
    """Generate a placeholder report from an existing manifest."""

    manifest_path = run
    if run.is_dir():
        manifest_path = run / "manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter("Manifest not found")

    if manifest_path.suffix == ".json":
        bundle = load_manifest(manifest_path)
    else:
        bundle = load_config(manifest_path)
    console.print(
        f"[yellow]Report generation stub for run '{bundle.run.name}' in format {format}[/yellow]"
    )


if __name__ == "__main__":  # pragma: no cover
    app()

