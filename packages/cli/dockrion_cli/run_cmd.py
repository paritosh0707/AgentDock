"""Run command - Run agent server locally for development."""

from pathlib import Path

import typer
from dockrion_common import MissingSecretError, get_env_summary
from dockrion_sdk import load_dockspec, run_local

from .utils import console, error, handle_error, info, success

app = typer.Typer()


@app.command(name="run")
def run(
    path: str = typer.Argument("Dockfile.yaml", help="Path to Dockfile"),
    host: str | None = typer.Option(
        None,
        "--host",
        help="Override bind host (default: value from Dockfile or 0.0.0.0)",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        help="Override bind port (default: value from Dockfile or 8080)",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable hot reload for development",
    ),
    env_file: str | None = typer.Option(
        None, "--env-file", "-e", help="Path to .env file (overrides auto-detected .env)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Run agent server locally for development.

    This starts a FastAPI server that exposes your agent through HTTP endpoints:
    - POST /invoke - Invoke the agent
    - GET /health - Health check
    - GET /schema - Input/output schema
    - GET /metrics - Prometheus metrics

    Environment variables are automatically loaded from:
    - .env file in project root
    - env.yaml / .dockrion-env.yaml in project root
    - Shell environment variables
    - Explicit --env-file if provided (highest priority)

    Press Ctrl+C to stop the server.

    Examples:
        dockrion run
        dockrion run custom/Dockfile.yaml
        dockrion run --env-file ./secrets/.env.local
        dockrion run --verbose
    """
    try:
        # Validate file exists
        if not Path(path).exists():
            error(f"Dockfile not found: {path}")
            raise typer.Exit(1)

        # Load spec to get server info (with env resolution)
        try:
            spec = load_dockspec(path, env_file=env_file)
            dockfile_port = spec.expose.port if spec.expose else 8080
            dockfile_host = spec.expose.host if spec.expose else "0.0.0.0"

            # Show secrets status if configured
            if spec.secrets and verbose:
                from dockrion_common import load_env_files, resolve_secrets

                project_root = Path(path).resolve().parent
                loaded_env = load_env_files(project_root, env_file)
                resolved = resolve_secrets(spec.secrets, loaded_env)
                summary = get_env_summary(spec.secrets, resolved)

                if summary.get("has_secrets_config"):
                    req = summary["required"]
                    opt = summary["optional"]
                    info(
                        f"Secrets: {req['set']}/{req['declared']} required, {opt['set']}/{opt['declared']} optional"
                    )

        except MissingSecretError as e:
            error(f"Missing required secrets: {', '.join(e.missing)}")
            console.print(
                "\n[dim]💡 Tip: Create a .env file or use --env-file to provide secrets[/dim]"
            )
            raise typer.Exit(1)
        except Exception as e:
            error(f"Failed to load Dockfile: {str(e)}")
            raise typer.Exit(1)

        info(f"Starting agent server from {path}...")
        if env_file:
            info(f"Using env file: {env_file}")
        console.print()

        # Start server (with env resolution)
        proc = run_local(path, host=host, port=port, reload=reload, env_file=env_file)

        effective_host = host or dockfile_host
        effective_port = port or dockfile_port

        console.print()
        success(f"Server started at [bold]http://{effective_host}:{effective_port}[/bold]")

        # Show available endpoints
        console.print("\n[bold cyan]Available endpoints:[/bold cyan]")
        console.print(f"  • POST http://{effective_host}:{effective_port}/invoke - Invoke agent")
        console.print(f"  • GET  http://{effective_host}:{effective_port}/health - Health check")
        console.print(f"  • GET  http://{effective_host}:{effective_port}/schema - I/O schema")
        console.print(f"  • GET  http://{effective_host}:{effective_port}/metrics - Metrics")
        console.print(f"  • GET  http://{effective_host}:{effective_port}/docs - Swagger UI")

        console.print("\n[bold yellow]Press Ctrl+C to stop the server[/bold yellow]")

        # Wait for Ctrl+C
        try:
            proc.wait()
        except KeyboardInterrupt:
            console.print()
            info("Shutting down server...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
            console.print()
            success("Server stopped")

    except typer.Exit:
        raise
    except KeyboardInterrupt:
        raise typer.Exit(0)
    except Exception as e:
        handle_error(e, verbose)
        raise typer.Exit(1)
