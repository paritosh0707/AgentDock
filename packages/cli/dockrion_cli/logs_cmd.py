"""Logs command - View agent logs."""

import typer
from dockrion_sdk import get_local_logs, stream_agent_logs

from .utils import console, handle_error, info

app = typer.Typer()


@app.command(name="logs")
def logs(
    agent: str = typer.Argument(..., help="Agent name"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output (real-time)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    View logs from a running agent.

    V1 Implementation: Reads logs from .dockrion_runtime/logs/ directory
    V1.1+: Will support remote log streaming from Controller

    Examples:
        dockrion logs invoice-copilot
        dockrion logs invoice-copilot --lines 50
        dockrion logs invoice-copilot --follow
    """
    try:
        if follow:
            info(f"Following logs for {agent} (Press Ctrl+C to stop)")
            console.print()
            for line in stream_agent_logs(agent, follow=True):
                console.print(line, end="")
        else:
            if verbose:
                info(f"Fetching last {lines} lines for {agent}")
                console.print()

            log_lines = get_local_logs(agent, lines=lines)

            for line in log_lines:
                console.print(line, end="")

    except KeyboardInterrupt:
        console.print()
        info("Stopped following logs")
    except Exception as e:
        handle_error(e, verbose)
        console.print("\n[dim]💡 Tip: Make sure the agent is running or has run previously[/dim]")
        raise typer.Exit(1)
