"""CLI interface for AppForge."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from appforge.pipeline import Pipeline
from appforge.registry import StepRegistry, get_default_registry
from appforge.steps.mock import MockStep, EchoStep
from appforge.steps.llm import LLMStep

console = Console()


def setup_default_registry() -> StepRegistry:
    """Configure the default registry with standard steps."""
    registry = get_default_registry()

    # Register mock implementations
    registry.register("mock", MockStep)
    registry.register("echo", EchoStep)

    # Register LLM implementations
    registry.register("llm", LLMStep)
    registry.register("clarify", LLMStep)
    registry.register("design", LLMStep)
    registry.register("plan", LLMStep)

    # Register mock versions for testing
    registry.register("mock_clarify", MockStep)
    registry.register("mock_design", MockStep)
    registry.register("mock_plan", MockStep)

    return registry


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AppForge: Modular AI pipeline for software development."""
    setup_default_registry()


@main.command()
@click.argument("idea")
@click.option("--steps", "-s", default="clarify,design,plan", help="Comma-separated step names")
@click.option("--mock", is_flag=True, help="Use mock steps (no LLM calls)")
@click.option("--dry-run", is_flag=True, help="Validate pipeline without executing")
@click.option("--output-dir", "-o", default="./runs", help="Directory for run output")
@click.option("--model", "-m", default="gpt-4o-mini", help="LLM model to use")
@click.option("--provider", "-p", default="openai", help="LLM provider (openai/anthropic)")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config YAML")
def run(idea, steps, mock, dry_run, output_dir, model, provider, config):
    """Run the pipeline with a project idea.

    Example:
        appforge run "Build a todo app with user authentication"
        appforge run "Create an API for..." --mock --steps clarify,design
    """
    registry = get_default_registry()

    # Parse steps
    step_names = [s.strip() for s in steps.split(",")]

    # Load config if provided
    if config:
        registry.load_config(config)

    # If mock mode, swap to mock implementations
    if mock:
        for step_name in step_names:
            mock_name = f"mock_{step_name}"
            if mock_name in registry.list_registered():
                registry.set_active(step_name, mock_name)
            else:
                registry.set_active(step_name, "mock")

    # Configure step settings
    step_configs = {}
    for step_name in step_names:
        step_configs[step_name] = {
            "model": model,
            "provider": provider,
            "prompts_dir": "./prompts",
        }

    # Create and run pipeline
    pipeline = Pipeline(
        step_names=step_names,
        registry=registry,
        output_dir=output_dir,
        step_configs=step_configs,
    )

    console.print(Panel(f"[bold]Running pipeline:[/bold] {' → '.join(step_names)}"))
    console.print(f"[dim]Input:[/dim] {idea[:100]}{'...' if len(idea) > 100 else ''}")
    console.print()

    if dry_run:
        console.print("[yellow]DRY RUN MODE - no actual execution[/yellow]")
        console.print()

    with console.status("[bold green]Running pipeline..."):
        result = pipeline.run(idea, dry_run=dry_run)

    # Display results
    if result.status == "completed":
        console.print(Panel("[bold green]Pipeline completed successfully![/bold green]"))
    else:
        console.print(Panel(f"[bold red]Pipeline failed: {result.error}[/bold red]"))

    # Show step results
    for i, step_result in enumerate(result.results):
        step_name = step_result["step_name"]
        success = step_result["success"]
        status_icon = "✓" if success else "✗"
        status_color = "green" if success else "red"

        console.print(f"\n[{status_color}]{status_icon}[/{status_color}] [bold]{step_name}[/bold]")

        if step_result.get("output"):
            output = step_result["output"]
            if isinstance(output, str) and len(output) > 200:
                # For long outputs, show as markdown
                console.print(Markdown(output))
            else:
                console.print(f"  Output: {output}")

    console.print(f"\n[dim]Run saved to: {output_dir}/{result.run_id}.json[/dim]")


@main.command()
@click.option("--output-dir", "-o", default="./runs", help="Directory with run files")
def list_runs(output_dir):
    """List previous pipeline runs."""
    runs_dir = Path(output_dir)
    if not runs_dir.exists():
        console.print("[yellow]No runs found.[/yellow]")
        return

    table = Table(title="Pipeline Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Steps", style="dim")

    for run_file in sorted(runs_dir.glob("*.json"), reverse=True):
        with open(run_file) as f:
            data = json.load(f)
        status_color = "green" if data["status"] == "completed" else "red"
        table.add_row(
            data["run_id"],
            f"[{status_color}]{data['status']}[/{status_color}]",
            ", ".join(data.get("steps_completed", [])),
        )

    console.print(table)


@main.command()
@click.argument("run_id")
@click.option("--output-dir", "-o", default="./runs", help="Directory with run files")
@click.option("--step", "-s", help="Show only this step's output")
def show(run_id, output_dir, step):
    """Show details of a previous run."""
    run_file = Path(output_dir) / f"{run_id}.json"
    if not run_file.exists():
        console.print(f"[red]Run not found: {run_id}[/red]")
        return

    with open(run_file) as f:
        data = json.load(f)

    console.print(Panel(f"[bold]Run: {run_id}[/bold]"))
    console.print(f"Status: {data['status']}")
    console.print(f"Started: {data['started_at']}")
    console.print(f"Completed: {data.get('completed_at', 'N/A')}")
    console.print(f"\n[bold]Initial Input:[/bold]\n{data.get('initial_input', 'N/A')}")

    for result in data.get("results", []):
        if step and result["step_name"] != step:
            continue

        console.print(f"\n[bold cyan]━━━ {result['step_name']} ━━━[/bold cyan]")
        if result.get("output"):
            output = result["output"]
            if isinstance(output, str):
                console.print(Markdown(output))
            else:
                console.print(json.dumps(output, indent=2))


@main.command()
def list_steps():
    """List available steps."""
    registry = get_default_registry()
    setup_default_registry()

    table = Table(title="Registered Steps")
    table.add_column("Name", style="cyan")
    table.add_column("Active Implementation", style="green")

    mappings = registry.list_active_mappings()
    for name in sorted(registry.list_registered()):
        active = mappings.get(name, name)
        table.add_row(name, active if active != name else "[dim]self[/dim]")

    console.print(table)


@main.command()
@click.argument("step_name")
@click.argument("implementation")
def swap(step_name, implementation):
    """Swap a step's implementation.

    Example:
        appforge swap clarify mock_clarify
    """
    registry = get_default_registry()
    setup_default_registry()

    try:
        registry.set_active(step_name, implementation)
        console.print(f"[green]✓[/green] Swapped '{step_name}' to use '{implementation}'")
    except KeyError as e:
        console.print(f"[red]Error:[/red] {e}")


@main.command()
@click.argument("idea")
@click.option("--step", "-s", default="clarify", help="Step to test")
@click.option("--mock", is_flag=True, help="Use mock step")
@click.option("--model", "-m", default="gpt-4o-mini", help="LLM model")
@click.option("--provider", "-p", default="openai", help="LLM provider")
def test_step(idea, step, mock, model, provider):
    """Test a single step in isolation.

    Example:
        appforge test-step "Build a todo app" --step clarify
        appforge test-step "Build a todo app" --step clarify --mock
    """
    registry = get_default_registry()
    setup_default_registry()

    if mock:
        impl = f"mock_{step}" if f"mock_{step}" in registry.list_registered() else "mock"
        registry.set_active(step, impl)

    config = {
        "model": model,
        "provider": provider,
        "prompts_dir": "./prompts",
    }

    step_instance = registry.create(step, config=config)

    console.print(Panel(f"[bold]Testing step: {step}[/bold]"))
    console.print(f"[dim]Implementation: {type(step_instance).__name__}[/dim]")
    console.print(f"[dim]Input: {idea[:100]}...[/dim]")
    console.print()

    with console.status(f"[bold green]Running {step}..."):
        result = step_instance.execute(idea, context={})

    if result.success:
        console.print("[green]✓ Step succeeded[/green]")
        if isinstance(result.output, str):
            console.print(Markdown(result.output))
        else:
            console.print(json.dumps(result.output, indent=2))
    else:
        console.print(f"[red]✗ Step failed: {result.error}[/red]")


if __name__ == "__main__":
    main()
