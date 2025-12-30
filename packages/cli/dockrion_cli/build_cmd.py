"""Build command - Build Docker image for agent deployment."""

from pathlib import Path

import typer
from dockrion_common import MissingSecretError, get_env_summary, load_env_files, resolve_secrets
from dockrion_sdk import deploy, load_dockspec

from .utils import console, error, handle_error, info, success, warning

app = typer.Typer()


@app.command(name="build")
def build(
    path: str = typer.Argument("Dockfile.yaml", help="Path to Dockfile"),
    target: str = typer.Option("local", help="Deployment target (local for V1)"),
    tag: str = typer.Option(
        "dev",
        "--tag",
        help="Docker image tag (default: dev)",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Build Docker image without cache",
    ),
    env_file: str | None = typer.Option(
        None, "--env-file", "-e", help="Path to .env file for validating secrets"
    ),
    allow_missing_secrets: bool = typer.Option(
        False, "--allow-missing-secrets", help="Continue build even if required secrets are missing"
    ),
    dev: bool = typer.Option(
        False, "--dev", help="Development mode: use local PyPI server for Dockrion packages"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Build a Docker image for the agent.

    This command creates a production-ready Docker image that includes:
    - Your agent code
    - FastAPI runtime server
    - All dependencies
    - Health checks and metrics endpoints

    Environment variables are validated from:
    - .env file in project root
    - env.yaml / .dockrion-env.yaml in project root
    - Shell environment variables
    - Explicit --env-file if provided

    Use --allow-missing-secrets to build even if required secrets are not set
    (the secrets must be provided at container runtime).

    Use --dev for development builds that use local Dockrion packages via a
    local PyPI server (requires wheel files in dist/ directory).

    Examples:
        dockrion build
        dockrion build --dev                      # Development mode
        dockrion build custom/Dockfile.yaml
        dockrion build --env-file ./secrets/.env.local
        dockrion build --allow-missing-secrets
        dockrion build --verbose
    """
    try:
        # Validate file exists
        if not Path(path).exists():
            error(f"Dockfile not found: {path}")
            raise typer.Exit(1)

        # Load spec to show info (non-strict to get full info first)
        try:
            spec = load_dockspec(path, env_file=env_file, strict_secrets=False)
            agent_name = spec.agent.name
            expose_port = spec.expose.port if spec.expose else 8080

            # Show secrets validation status
            if spec.secrets:
                project_root = Path(path).resolve().parent
                loaded_env = load_env_files(project_root, env_file)
                resolved = resolve_secrets(spec.secrets, loaded_env)
                summary = get_env_summary(spec.secrets, resolved)

                if summary.get("has_secrets_config"):
                    req = summary["required"]
                    opt = summary["optional"]

                    if req["missing"] > 0:
                        missing_names = [
                            s.name
                            for s in spec.secrets.required
                            if s.name not in resolved or not resolved[s.name]
                        ]

                        if allow_missing_secrets:
                            warning(
                                f"Missing {req['missing']} required secrets: {', '.join(missing_names)}"
                            )
                            console.print(
                                "[dim]  ⚠️  These must be provided at container runtime (docker run -e ...)[/dim]"
                            )
                        else:
                            error(f"Missing required secrets: {', '.join(missing_names)}")
                            console.print(
                                "\n[dim]💡 Tip: Use --allow-missing-secrets to build anyway,[/dim]"
                            )
                            console.print(
                                "[dim]   then provide secrets at runtime with docker run -e VAR=value[/dim]"
                            )
                            raise typer.Exit(1)
                    elif verbose:
                        info(
                            f"Secrets: {req['set']}/{req['declared']} required ✓, {opt['set']}/{opt['declared']} optional"
                        )

        except MissingSecretError as e:
            if allow_missing_secrets:
                warning(f"Missing required secrets: {', '.join(e.missing)}")
                console.print("[dim]  ⚠️  These must be provided at container runtime[/dim]")
                # Re-load without strict validation
                spec = load_dockspec(path, env_file=env_file, strict_secrets=False)
                agent_name = spec.agent.name
                expose_port = spec.expose.port if spec.expose else 8080
            else:
                error(f"Missing required secrets: {', '.join(e.missing)}")
                console.print("\n[dim]💡 Tip: Use --allow-missing-secrets to build anyway[/dim]")
                raise typer.Exit(1)
        except Exception as e:
            error(f"Failed to load Dockfile: {str(e)}")
            raise typer.Exit(1)

        info(f"Building Docker image for agent: [bold]{agent_name}[/bold]")
        if env_file:
            info(f"Using env file: {env_file}")

        if verbose:
            console.print()
            info("This may take a few minutes...")

        # Build image
        if dev:
            info("Development mode: Using local PyPI server for Dockrion packages")

        with console.status("[bold green]Building Docker image..."):
            result = deploy(
                path,
                target=target,
                tag=tag,
                no_cache=no_cache,
                env_file=env_file,
                allow_missing_secrets=allow_missing_secrets,
                dev=dev,
            )

        # Show success
        console.print()
        success(f"Successfully built image: [bold cyan]{result['image']}[/bold cyan]")

        # Check if there are required secrets to show in the run command
        has_required_secrets = False
        secret_env_example = ""
        required_secrets = spec.secrets.required if spec.secrets else []
        if required_secrets:
            has_required_secrets = True
            # Get first required secret name for example
            first_secret = required_secrets[0].name
            secret_env_example = f"-e {first_secret}=<value> "
            if len(required_secrets) > 1:
                secret_env_example += "... "

        # Show next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Run locally:")
        if has_required_secrets:
            console.print(
                f"     [cyan]docker run -p {expose_port}:{expose_port} {secret_env_example}{result['image']}[/cyan]"
            )
            console.print(
                f"     [dim]Or use an env file:[/dim] [cyan]docker run -p {expose_port}:{expose_port} --env-file .env {result['image']}[/cyan]"
            )
            console.print()
            console.print("     [yellow]⚠️  Required secrets (must be provided at runtime):[/yellow]")
            for secret in required_secrets:
                desc = f" - {secret.description}" if secret.description else ""
                console.print(f"        [dim]• {secret.name}{desc}[/dim]")
        else:
            console.print(
                f"     [cyan]docker run -p {expose_port}:{expose_port} {result['image']}[/cyan]"
            )
        console.print()
        console.print("  2. Push to registry:")
        console.print(
            f"     [cyan]docker tag {result['image']} <registry>/{agent_name}:latest[/cyan]"
        )
        console.print(f"     [cyan]docker push <registry>/{agent_name}:latest[/cyan]")

    except typer.Exit:
        raise
    except KeyboardInterrupt:
        info("\nBuild cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, verbose)
        console.print("\n[dim]💡 Tip: Make sure Docker is running and accessible[/dim]")
        raise typer.Exit(1)
