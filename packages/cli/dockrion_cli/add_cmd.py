"""Add command - Add sections to existing Dockfile."""

from pathlib import Path
from typing import List, Optional, Union

import typer
import yaml

from .utils import confirm_action, console, error, success, warning

app = typer.Typer()

# Available streaming events presets
STREAMING_EVENTS_PRESETS = ["all", "chat", "debug", "minimal"]

# Available streaming backends
STREAMING_BACKENDS = ["memory", "redis"]


def load_dockfile(path: Path) -> dict:
    """Load and parse a Dockfile.

    Args:
        path: Path to Dockfile

    Returns:
        Parsed Dockfile as dict

    Raises:
        typer.Exit: If file doesn't exist or is invalid
    """
    if not path.exists():
        error(f"Dockfile not found: {path}")
        raise typer.Exit(1)

    try:
        content = path.read_text()
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            error(f"Invalid Dockfile format: {path}")
            raise typer.Exit(1)
        return data
    except yaml.YAMLError as e:
        error(f"YAML parsing error: {e}")
        raise typer.Exit(1)


def save_dockfile(path: Path, data: dict) -> None:
    """Save Dockfile data to file.

    Args:
        path: Path to Dockfile
        data: Dockfile data dict
    """
    # Use block style for better readability
    content = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    path.write_text(content)


@app.command(name="streaming")
def add_streaming(
    dockfile: str = typer.Argument("Dockfile.yaml", help="Path to Dockfile"),
    events: Optional[str] = typer.Option(
        None,
        "--events",
        "-E",
        help="Events preset (all, chat, debug, minimal) or comma-separated list",
    ),
    async_runs: bool = typer.Option(
        False,
        "--async-runs",
        "-A",
        help="Enable async /runs endpoint (Pattern B)",
    ),
    backend: str = typer.Option(
        "memory",
        "--backend",
        "-b",
        help="Event backend: memory (default) or redis",
    ),
    heartbeat: int = typer.Option(
        15,
        "--heartbeat",
        help="Heartbeat interval in seconds",
    ),
    max_duration: int = typer.Option(
        3600,
        "--max-duration",
        help="Maximum run duration in seconds",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing streaming configuration",
    ),
):
    """
    Add or update streaming configuration in a Dockfile.

    \b
    Examples:
        # Add basic streaming with chat preset
        dockrion add streaming --events chat

        # Enable async runs with debug events
        dockrion add streaming --events debug --async-runs

        # Custom event list
        dockrion add streaming --events "token,step,custom:fraud_check"

        # Production setup with Redis
        dockrion add streaming --events chat --async-runs --backend redis
    """
    path = Path(dockfile)
    data = load_dockfile(path)

    # Check if streaming config exists
    if "streaming" in data and not force:
        if not confirm_action("Streaming config already exists. Overwrite?", default=False):
            warning("Cancelled")
            raise typer.Exit(0)

    # Validate backend
    if backend not in STREAMING_BACKENDS:
        error(f"Invalid backend: '{backend}'. Valid options: {', '.join(STREAMING_BACKENDS)}")
        raise typer.Exit(1)

    # Parse events
    parsed_events: Optional[Union[str, List[str]]] = None
    if events:
        if events in STREAMING_EVENTS_PRESETS:
            parsed_events = events
        else:
            # Parse as comma-separated list
            events_list = [e.strip() for e in events.split(",") if e.strip()]
            if events_list:
                parsed_events = events_list

    # Build streaming config
    streaming_config: dict = {
        "async_runs": async_runs,
        "backend": backend,
    }

    if parsed_events:
        streaming_config["events"] = {
            "allowed": parsed_events,
            "heartbeat_interval": heartbeat,
            "max_run_duration": max_duration,
        }
    elif heartbeat != 15 or max_duration != 3600:
        streaming_config["events"] = {
            "heartbeat_interval": heartbeat,
            "max_run_duration": max_duration,
        }

    # Update Dockfile
    data["streaming"] = streaming_config
    save_dockfile(path, data)

    success(f"Added streaming configuration to {dockfile}")

    # Show summary
    console.print("\n[bold cyan]Streaming Configuration:[/bold cyan]")
    if parsed_events:
        if isinstance(parsed_events, str):
            console.print(f"  • Events preset: [green]{parsed_events}[/green]")
        else:
            console.print(f"  • Events filter: [green]{', '.join(parsed_events)}[/green]")
    else:
        console.print("  • Events: [green]all (default)[/green]")
    console.print(f"  • Async runs: [green]{'enabled' if async_runs else 'disabled'}[/green]")
    console.print(f"  • Backend: [green]{backend}[/green]")
    console.print(f"  • Heartbeat: [green]{heartbeat}s[/green]")
    console.print(f"  • Max duration: [green]{max_duration}s[/green]")


@app.command(name="auth")
def add_auth(
    dockfile: str = typer.Argument("Dockfile.yaml", help="Path to Dockfile"),
    mode: str = typer.Option(
        "api_key",
        "--mode",
        "-m",
        help="Auth mode: api_key or jwt",
    ),
    env_var: str = typer.Option(
        "API_KEY",
        "--env-var",
        help="Environment variable for API key (api_key mode)",
    ),
    header: str = typer.Option(
        "X-API-Key",
        "--header",
        help="HTTP header for API key (api_key mode)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing auth configuration",
    ),
):
    """
    Add or update auth configuration in a Dockfile.

    \b
    Examples:
        # Add API key auth
        dockrion add auth --mode api_key

        # Custom API key setup
        dockrion add auth --mode api_key --env-var MY_SECRET_KEY --header Authorization

        # JWT auth
        dockrion add auth --mode jwt
    """
    path = Path(dockfile)
    data = load_dockfile(path)

    # Check if auth config exists
    if "auth" in data and data["auth"] and not force:
        if not confirm_action("Auth config already exists. Overwrite?", default=False):
            warning("Cancelled")
            raise typer.Exit(0)

    # Validate mode
    if mode not in ["api_key", "jwt", "none"]:
        error(f"Invalid auth mode: '{mode}'. Valid options: api_key, jwt, none")
        raise typer.Exit(1)

    # Build auth config
    if mode == "none":
        data["auth"] = None
    elif mode == "api_key":
        data["auth"] = {
            "mode": "api_key",
            "api_keys": {
                "env_var": env_var,
                "header": header,
            },
        }
    elif mode == "jwt":
        data["auth"] = {
            "mode": "jwt",
            # User needs to fill in JWT settings
        }

    save_dockfile(path, data)
    success(f"Added auth configuration to {dockfile}")

    # Show summary
    console.print("\n[bold cyan]Auth Configuration:[/bold cyan]")
    console.print(f"  • Mode: [green]{mode}[/green]")
    if mode == "api_key":
        console.print(f"  • Env var: [green]{env_var}[/green]")
        console.print(f"  • Header: [green]{header}[/green]")
    elif mode == "jwt":
        console.print("  [dim]• Configure jwks_url, issuer, audience in the Dockfile[/dim]")


@app.command(name="secrets")
def add_secrets(
    dockfile: str = typer.Argument("Dockfile.yaml", help="Path to Dockfile"),
    names: str = typer.Argument(..., help="Comma-separated list of secret names"),
    optional: bool = typer.Option(
        False,
        "--optional",
        help="Mark secrets as optional instead of required",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing secrets configuration",
    ),
):
    """
    Add secrets to a Dockfile.

    \b
    Examples:
        # Add required secrets
        dockrion add secrets OPENAI_API_KEY,ANTHROPIC_KEY

        # Add optional secrets
        dockrion add secrets LANGFUSE_SECRET --optional
    """
    path = Path(dockfile)
    data = load_dockfile(path)

    # Parse secret names
    secret_names = [s.strip().upper().replace("-", "_") for s in names.split(",") if s.strip()]
    if not secret_names:
        error("No secret names provided")
        raise typer.Exit(1)

    # Check if secrets config exists and merge
    if "secrets" not in data or not data["secrets"]:
        data["secrets"] = {"required": [], "optional": []}
    elif not force:
        console.print("[dim]Merging with existing secrets configuration[/dim]")

    secrets = data["secrets"]
    if "required" not in secrets:
        secrets["required"] = []
    if "optional" not in secrets:
        secrets["optional"] = []

    # Add secrets
    target_list = "optional" if optional else "required"
    existing_names = {s.get("name", s) if isinstance(s, dict) else s for s in secrets[target_list]}

    added = []
    for name in secret_names:
        if name not in existing_names:
            secrets[target_list].append({
                "name": name,
                "description": f"Secret for {name.lower()}",
            })
            added.append(name)

    if not added:
        warning("All secrets already exist in configuration")
        raise typer.Exit(0)

    save_dockfile(path, data)
    success(f"Added {len(added)} secret(s) to {dockfile}")

    # Show summary
    console.print("\n[bold cyan]Added Secrets:[/bold cyan]")
    for name in added:
        console.print(f"  • {name} [green]({'optional' if optional else 'required'})[/green]")


# Main add command group
@app.callback()
def main():
    """
    Add or update sections in an existing Dockfile.

    \b
    Commands:
        streaming  - Add/update streaming configuration
        auth       - Add/update authentication
        secrets    - Add secrets definitions

    \b
    Examples:
        dockrion add streaming --events chat --async-runs
        dockrion add auth --mode api_key
        dockrion add secrets OPENAI_API_KEY,ANTHROPIC_KEY
    """
    pass
