#!/usr/bin/env python3
"""
AppForge - Agent Swap CLI
Phase 2: Hot-swappable Agent Framework

Swap any agent implementation with <10 lines of configuration change.

Usage:
    python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub
    python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub --dry-run
    python scripts/swap_agent.py --list
    python scripts/swap_agent.py --show frontend
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from rich.console import Console
from rich.table import Table

console = Console()


def load_config(config_path: Path) -> dict:
    """Load agents.yaml configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def save_config(config_path: Path, config: dict) -> None:
    """Save configuration back to YAML."""
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def list_agents(config_path: Path) -> None:
    """List all registered agents."""
    config = load_config(config_path)
    agents = config.get("agents", {})

    table = Table(title="Registered Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Module", style="yellow")
    table.add_column("Class", style="magenta")
    table.add_column("Enabled", style="blue")

    for agent_id, agent_data in agents.items():
        module = agent_data.get("module", f"agents.{agent_id}")
        class_name = agent_data.get(
            "class_name",
            "".join(word.capitalize() for word in agent_id.split("_")) + "Agent",
        )
        enabled = "Yes" if agent_data.get("enabled", True) else "No"

        table.add_row(
            agent_id,
            agent_data.get("name", agent_id),
            module,
            class_name,
            enabled,
        )

    console.print(table)


def show_agent(config_path: Path, agent_id: str) -> None:
    """Show details for a specific agent."""
    config = load_config(config_path)
    agents = config.get("agents", {})

    if agent_id not in agents:
        console.print(f"[red]Agent '{agent_id}' not found[/red]")
        console.print(f"Available agents: {', '.join(agents.keys())}")
        sys.exit(1)

    agent_data = agents[agent_id]

    console.print(f"\n[bold cyan]Agent: {agent_id}[/bold cyan]")
    console.print("-" * 40)

    for key, value in agent_data.items():
        if isinstance(value, dict):
            console.print(f"[green]{key}:[/green]")
            for k, v in value.items():
                console.print(f"  [yellow]{k}:[/yellow] {v}")
        else:
            console.print(f"[green]{key}:[/green] {value}")


def swap_agent(
    config_path: Path,
    agent_id: str,
    module: str,
    class_name: str,
    dry_run: bool = False,
) -> None:
    """Swap an agent's implementation."""
    config = load_config(config_path)
    agents = config.get("agents", {})

    if agent_id not in agents:
        console.print(f"[red]Agent '{agent_id}' not found[/red]")
        console.print(f"Available agents: {', '.join(agents.keys())}")
        sys.exit(1)

    old_module = agents[agent_id].get("module", f"agents.{agent_id}")
    old_class = agents[agent_id].get(
        "class_name",
        "".join(word.capitalize() for word in agent_id.split("_")) + "Agent",
    )

    console.print(f"\n[bold]Swapping agent: {agent_id}[/bold]")
    console.print("-" * 40)
    console.print(f"[yellow]Old:[/yellow] {old_module}.{old_class}")
    console.print(f"[green]New:[/green] {module}.{class_name}")

    if dry_run:
        console.print("\n[cyan]DRY RUN - No changes made[/cyan]")
        console.print("\nTo apply changes, run without --dry-run flag:")
        console.print(
            f"  python scripts/swap_agent.py --name {agent_id} "
            f"--module {module} --class {class_name}"
        )
        return

    # Apply changes
    agents[agent_id]["module"] = module
    agents[agent_id]["class_name"] = class_name

    save_config(config_path, config)

    console.print("\n[green]Agent swapped successfully![/green]")
    console.print("\nNote: If auto_reload is enabled, changes will take effect automatically.")
    console.print("Otherwise, restart the application to apply changes.")


def reset_agent(config_path: Path, agent_id: str) -> None:
    """Reset an agent to its default implementation."""
    config = load_config(config_path)
    agents = config.get("agents", {})

    if agent_id not in agents:
        console.print(f"[red]Agent '{agent_id}' not found[/red]")
        sys.exit(1)

    # Calculate default values
    default_module = f"agents.{agent_id}"
    default_class = "".join(word.capitalize() for word in agent_id.split("_")) + "Agent"

    # Remove overrides
    if "module" in agents[agent_id]:
        del agents[agent_id]["module"]
    if "class_name" in agents[agent_id]:
        del agents[agent_id]["class_name"]

    save_config(config_path, config)

    console.print(f"\n[green]Agent '{agent_id}' reset to defaults:[/green]")
    console.print(f"  Module: {default_module}")
    console.print(f"  Class: {default_class}")


def main():
    parser = argparse.ArgumentParser(
        description="Swap agent implementations in AppForge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all agents
  python scripts/swap_agent.py --list

  # Show agent details
  python scripts/swap_agent.py --show frontend

  # Swap agent (dry run)
  python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub --dry-run

  # Swap agent (apply)
  python scripts/swap_agent.py --name frontend --module agent_stubs --class FrontendStub

  # Reset agent to defaults
  python scripts/swap_agent.py --reset frontend
        """,
    )

    parser.add_argument(
        "--config",
        default="config/agents.yaml",
        help="Path to agents.yaml (default: config/agents.yaml)",
    )

    # Actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--list",
        action="store_true",
        help="List all registered agents",
    )
    action_group.add_argument(
        "--show",
        metavar="AGENT_ID",
        help="Show details for a specific agent",
    )
    action_group.add_argument(
        "--reset",
        metavar="AGENT_ID",
        help="Reset an agent to its default implementation",
    )

    # Swap options
    parser.add_argument(
        "--name",
        metavar="AGENT_ID",
        help="Agent ID to swap (e.g., 'frontend')",
    )
    parser.add_argument(
        "--module",
        help="New module path (e.g., 'agent_stubs')",
    )
    parser.add_argument(
        "--class",
        dest="class_name",
        help="New class name (e.g., 'FrontendStub')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without applying",
    )

    args = parser.parse_args()
    config_path = Path(args.config)

    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)

    # Handle actions
    if args.list:
        list_agents(config_path)
    elif args.show:
        show_agent(config_path, args.show)
    elif args.reset:
        reset_agent(config_path, args.reset)
    elif args.name and args.module and args.class_name:
        swap_agent(config_path, args.name, args.module, args.class_name, args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
