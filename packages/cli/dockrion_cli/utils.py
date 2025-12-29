"""Utility functions and helpers for CLI commands."""

import traceback
from typing import Any, Dict, List

from dockrion_common.errors import DockrionError, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Global console instance
console = Console()


def success(message: str):
    """Print a success message with green checkmark."""
    console.print(f"[bold green]✅ {message}[/bold green]")


def error(message: str):
    """Print an error message with red X."""
    console.print(f"[bold red]❌ {message}[/bold red]")


def warning(message: str):
    """Print a warning message with yellow icon."""
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


def info(message: str):
    """Print an info message with blue icon."""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


def print_validation_result(result: Dict[str, Any]):
    """
    Pretty print validation results with errors and warnings.

    Args:
        result: Validation result dict from validate_dockspec()
    """
    if not result["valid"]:
        # Show errors in a table
        if result["errors"]:
            error_table = Table(title="Validation Errors", show_header=False, border_style="red")
            error_table.add_column("Error", style="red")

            for err in result["errors"]:
                error_table.add_row(f"• {err}")

            console.print(error_table)

    # Show warnings if any
    if result["warnings"]:
        console.print()
        warning_table = Table(title="Warnings", show_header=False, border_style="yellow")
        warning_table.add_column("Warning", style="yellow")

        for warn in result["warnings"]:
            warning_table.add_row(f"• {warn}")

        console.print(warning_table)


def print_dict_as_json(data: Dict[str, Any], title: str = "Output"):
    """Print a dictionary as formatted JSON."""
    import json

    json_str = json.dumps(data, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title=title, border_style="green"))


def handle_error(e: Exception, verbose: bool = False):
    """
    Centralized error handling with helpful messages.

    Args:
        e: The exception to handle
        verbose: If True, show full stack trace
    """
    if isinstance(e, ValidationError):
        error(f"Validation Error: {str(e)}")
        console.print(
            "\n[dim]💡 Tip: Run 'dockrion validate' to see detailed validation errors[/dim]"
        )
    elif isinstance(e, DockrionError):
        error(f"dockrion Error: {str(e)}")
    elif isinstance(e, FileNotFoundError):
        error(f"File not found: {str(e)}")
        console.print("\n[dim]💡 Tip: Check that the file path is correct[/dim]")
    elif isinstance(e, KeyboardInterrupt):
        info("\nOperation cancelled by user")
    else:
        error(f"Unexpected error: {str(e)}")

    if verbose:
        console.print("\n[bold red]Stack Trace:[/bold red]")
        console.print(traceback.format_exc())


def print_agent_info(spec_data: Dict[str, Any]):
    """
    Print agent information from DockSpec in a formatted table.

    Args:
        spec_data: DockSpec model_dump() output
    """
    table = Table(title="Agent Information", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    agent = spec_data.get("agent", {})
    model = spec_data.get("model", {})
    expose = spec_data.get("expose", {})

    table.add_row("Name", agent.get("name", "N/A"))
    table.add_row("Framework", agent.get("framework", "N/A"))
    table.add_row("Entrypoint", agent.get("entrypoint", "N/A"))

    if model:
        table.add_row("Model Provider", model.get("provider", "N/A"))
        table.add_row("Model Name", model.get("name", "N/A"))

    if expose:
        port = expose.get("port", "N/A")
        host = expose.get("host", "N/A")
        table.add_row("Server Address", f"{host}:{port}")

    console.print(table)


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    from rich.prompt import Confirm

    return Confirm.ask(message, default=default)


def print_command_examples(command_name: str, examples: List[str]):
    """
    Print command usage examples.

    Args:
        command_name: Name of the command
        examples: List of example command strings
    """
    console.print("\n[bold]Examples:[/bold]")
    for example in examples:
        console.print(f"  [dim]$[/dim] [cyan]{example}[/cyan]")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
