"""Init command - Create new Dockfile template."""

from pathlib import Path
from typing import List, Optional, Union

import typer
from dockrion_schema import (
    AgentConfig,
    ApiKeysConfig,
    AuthConfig,
    DockSpec,
    ExposeConfig,
    IOSchema,
    IOSubSchema,
    Metadata,
    Observability,
    SecretDefinition,
    SecretsConfig,
    StreamingConfig,
    StreamingEventsConfig,
    to_yaml_string,
)

from .utils import confirm_action, console, error, success, warning

app = typer.Typer()

# Available auth modes
AUTH_MODES = ["none", "api_key", "jwt"]

# Available streaming modes (expose.streaming)
STREAMING_MODES = ["none", "sse", "websocket"]

# Available frameworks (must match SUPPORTED_FRAMEWORKS from dockrion_common)
FRAMEWORKS = ["langgraph", "langchain", "custom"]

# Available streaming events presets
STREAMING_EVENTS_PRESETS = ["all", "chat", "debug", "minimal"]

# Available streaming backends
STREAMING_BACKENDS = ["memory", "redis"]


def generate_dockfile_template(
    name: str,
    framework: str = "langgraph",
    handler_mode: bool = False,
    auth_mode: Optional[str] = None,
    streaming: str = "sse",
    include_secrets: bool = False,
    include_cors: bool = False,
    include_observability: bool = False,
    include_metadata: bool = False,
    secret_names: Optional[List[str]] = None,
    streaming_events: Optional[Union[str, List[str]]] = None,
    async_runs: bool = False,
    streaming_backend: str = "memory",
) -> str:
    """Generate a Dockfile template using schema models.

    This ensures the template is always in sync with the schema definition
    and produces valid, validated output.

    Args:
        name: Agent name (lowercase with hyphens)
        framework: Agent framework (langgraph, langchain, crewai, etc.)
        handler_mode: If True, use handler mode instead of entrypoint mode
        auth_mode: Authentication mode (none, api_key, jwt)
        streaming: Streaming mode (none, sse, websocket) for expose.streaming
        include_secrets: Whether to include secrets section
        include_cors: Whether to include CORS configuration
        include_observability: Whether to include observability section
        include_metadata: Whether to include metadata section
        secret_names: List of secret names to include
        streaming_events: Events preset or list ("chat", "debug", or ["token", "step"])
        async_runs: Whether to enable async /runs endpoint (Pattern B)
        streaming_backend: Backend type ("memory" or "redis")

    Returns:
        YAML string representation of the Dockfile template
    """
    # Build agent config based on mode
    if handler_mode:
        agent = AgentConfig(
            name=name,
            description=f"dockrion service: {name}",
            handler="app.service:handle_request",
            framework="custom",
        )
    else:
        agent = AgentConfig(
            name=name,
            description=f"dockrion agent: {name}",
            entrypoint="app.main:build_agent",
            framework=framework,
        )

    # Build expose config
    cors_config = None
    if include_cors:
        cors_config = {
            "origins": ["*"],
            "methods": ["GET", "POST", "OPTIONS"],
        }

    expose = ExposeConfig(
        rest=True,
        streaming=streaming,
        port=8080,
        host="0.0.0.0",
        cors=cors_config,
    )

    # Build auth config
    auth = None
    if auth_mode and auth_mode != "none":
        if auth_mode == "api_key":
            auth = AuthConfig(
                mode="api_key",
                api_keys=ApiKeysConfig(
                    env_var="MY_AGENT_KEY",
                    header="X-API-Key",
                ),
            )
        elif auth_mode == "jwt":
            auth = AuthConfig(
                mode="jwt",
            )

    # Build secrets config
    secrets = None
    if include_secrets or secret_names:
        required_secrets = []
        optional_secrets = []

        if secret_names:
            for secret_name in secret_names:
                required_secrets.append(
                    SecretDefinition(
                        name=secret_name.upper().replace("-", "_"),
                        description=f"Secret for {secret_name}",
                    )
                )
        else:
            # Default example secrets
            required_secrets = [
                SecretDefinition(
                    name="OPENAI_API_KEY",
                    description="OpenAI API key for LLM calls",
                ),
            ]
            optional_secrets = [
                SecretDefinition(
                    name="LANGFUSE_SECRET",
                    description="Langfuse telemetry secret",
                    default="",
                ),
            ]

        # Add auth secret if using api_key auth
        if auth_mode == "api_key":
            required_secrets.append(
                SecretDefinition(
                    name="MY_AGENT_KEY",
                    description="API key for agent authentication",
                )
            )

        secrets = SecretsConfig(
            required=required_secrets,
            optional=optional_secrets,
        )

    # Build observability config
    observability = None
    if include_observability:
        observability = Observability(
            tracing=True,
            log_level="info",
            metrics={"latency": True, "tokens": True, "cost": True},
        )

    # Build metadata config
    metadata = None
    if include_metadata:
        metadata = Metadata(
            maintainer="Your Name <your.email@example.com>",
            version="v0.1.0",
            tags=[name, framework],
        )

    # Build streaming config (Pattern A/B configuration)
    streaming_config = None
    if async_runs or streaming_events or streaming_backend != "memory":
        events_config = None
        if streaming_events:
            events_config = StreamingEventsConfig(
                allowed=streaming_events,
                heartbeat_interval=15,
                max_run_duration=3600,
            )
        streaming_config = StreamingConfig(
            async_runs=async_runs,
            backend=streaming_backend,
            events=events_config,
        )

    spec = DockSpec(
        version="1.0",
        agent=agent,
        io_schema=IOSchema(
            input=IOSubSchema(
                type="object",
                properties={"text": {"type": "string"}},
            ),
            output=IOSubSchema(
                type="object",
                properties={"result": {"type": "string"}},
            ),
        ),
        expose=expose,
        auth=auth,
        secrets=secrets,
        observability=observability,
        metadata=metadata,
        streaming=streaming_config,
    )
    return to_yaml_string(spec)


@app.command(name="init")
def init(
    name: str = typer.Argument(..., help="Agent name (lowercase with hyphens, e.g., my-agent)"),
    output: str = typer.Option("Dockfile.yaml", "--output", "-o", help="Output file path"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing file without asking"
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # AGENT TYPE - What kind of agent are you building?
    # ═══════════════════════════════════════════════════════════════════════════
    framework: str = typer.Option(
        "langgraph",
        "--framework",
        "-F",
        help="[AGENT TYPE] Framework: langgraph (default), langchain, or custom",
    ),
    handler: bool = typer.Option(
        False,
        "--handler",
        "-H",
        help="[AGENT TYPE] Use handler mode for simple functions (no .invoke() needed)",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SECURITY - How should the API be protected?
    # ═══════════════════════════════════════════════════════════════════════════
    auth: Optional[str] = typer.Option(
        None,
        "--auth",
        "-a",
        help="[SECURITY] Auth mode: none, api_key (recommended), or jwt (enterprise)",
    ),
    cors: bool = typer.Option(
        False,
        "--cors",
        help="[SECURITY] Enable CORS for browser access",
    ),
    secrets: bool = typer.Option(
        False,
        "--secrets",
        help="[SECURITY] Add secrets config (OPENAI_API_KEY, etc.)",
    ),
    secret_names: Optional[str] = typer.Option(
        None,
        "--secret-names",
        help="[SECURITY] Your secrets, comma-separated (e.g., OPENAI_API_KEY,ANTHROPIC_KEY)",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # API BEHAVIOR - How should the agent respond?
    # ═══════════════════════════════════════════════════════════════════════════
    streaming: str = typer.Option(
        "sse",
        "--streaming",
        "-s",
        help="[API] Streaming: sse (default, real-time), websocket, or none",
    ),
    streaming_events: Optional[str] = typer.Option(
        None,
        "--streaming-events",
        "-E",
        help="[API] Events config: preset (all, chat, debug, minimal) or comma-separated (token,step,custom:myevent)",
    ),
    async_runs: bool = typer.Option(
        False,
        "--async-runs",
        "-A",
        help="[API] Enable async /runs endpoint (Pattern B) for background execution",
    ),
    streaming_backend: str = typer.Option(
        "memory",
        "--streaming-backend",
        help="[API] Event backend: memory (default) or redis (production)",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # EXTRAS - Additional configuration sections
    # ═══════════════════════════════════════════════════════════════════════════
    observability: bool = typer.Option(
        False,
        "--observability",
        "--obs",
        help="[EXTRAS] Add logging, tracing, and metrics config",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="[EXTRAS] Add maintainer, version, and tags",
    ),
    # ═══════════════════════════════════════════════════════════════════════════
    # SHORTCUTS
    # ═══════════════════════════════════════════════════════════════════════════
    full: bool = typer.Option(
        False,
        "--full",
        help="[SHORTCUT] Include everything: auth, secrets, cors, observability, metadata",
    ),
):
    """
    Create a new Dockfile template for your agent.

    \b
    ╭─────────────────────────────────────────────────────────────────────────────╮
    │  🚀 QUICK START - Pick your pattern:                                        │
    ╰─────────────────────────────────────────────────────────────────────────────╯

    \b
      BASIC (development):
        dockrion init my-agent

    \b
      PRODUCTION (with auth & secrets):
        dockrion init my-agent --auth api_key --secrets

    \b
      FULL SETUP (everything enabled):
        dockrion init my-agent --full

    \b
      SIMPLE FUNCTION (no framework needed):
        dockrion init my-service --handler

    \b
    ╭─────────────────────────────────────────────────────────────────────────────╮
    │  📋 COMMON PATTERNS                                                         │
    ╰─────────────────────────────────────────────────────────────────────────────╯

    \b
      LangGraph Agent (default):
        dockrion init invoice-processor

    \b
      LangChain Agent:
        dockrion init chatbot --framework langchain

    \b
      REST API with auth:
        dockrion init my-api --auth api_key --cors

    \b
      Real-time streaming:
        dockrion init live-agent --streaming sse

    \b
      Enterprise setup (JWT + observability):
        dockrion init enterprise-bot --auth jwt --obs --metadata

    \b
    ╭─────────────────────────────────────────────────────────────────────────────╮
    │  💡 TIPS                                                                    │
    ╰─────────────────────────────────────────────────────────────────────────────╯

    \b
      • Use --full to start with all options, then remove what you don't need
      • Agent names must be lowercase with hyphens (my-agent, not MyAgent)
      • After init, edit the Dockfile to set your actual entrypoint path
    """
    try:
        # Validate agent name
        if not name.replace("-", "").replace("_", "").isalnum():
            error("Agent name must contain only letters, numbers, hyphens, and underscores")
            raise typer.Exit(1)

        # Validate framework
        if framework not in FRAMEWORKS:
            error(f"Invalid framework: '{framework}'. Valid options: {', '.join(FRAMEWORKS)}")
            raise typer.Exit(1)

        # Validate auth mode
        if auth and auth not in AUTH_MODES:
            error(f"Invalid auth mode: '{auth}'. Valid options: {', '.join(AUTH_MODES)}")
            raise typer.Exit(1)

        # Validate streaming mode
        if streaming not in STREAMING_MODES:
            error(
                f"Invalid streaming mode: '{streaming}'. Valid options: {', '.join(STREAMING_MODES)}"
            )
            raise typer.Exit(1)

        # Validate streaming backend
        if streaming_backend not in STREAMING_BACKENDS:
            error(
                f"Invalid streaming backend: '{streaming_backend}'. Valid options: {', '.join(STREAMING_BACKENDS)}"
            )
            raise typer.Exit(1)

        # Parse and validate streaming events
        parsed_streaming_events: Optional[Union[str, List[str]]] = None
        if streaming_events:
            # Check if it's a preset
            if streaming_events in STREAMING_EVENTS_PRESETS:
                parsed_streaming_events = streaming_events
            else:
                # Parse as comma-separated list
                events_list = [e.strip() for e in streaming_events.split(",") if e.strip()]
                if events_list:
                    parsed_streaming_events = events_list

        output_path = Path(output)

        # Check if file exists
        if output_path.exists() and not force:
            if not confirm_action(f"{output} already exists. Overwrite?", default=False):
                warning("Cancelled")
                raise typer.Exit(0)

        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle --full flag (enable all optional sections)
        if full:
            if not auth:
                auth = "api_key"
            secrets = True
            cors = True
            observability = True
            metadata = True
            # Enable async runs with full flag
            async_runs = True

        # Parse secret names if provided
        parsed_secret_names = None
        if secret_names:
            parsed_secret_names = [s.strip() for s in secret_names.split(",") if s.strip()]

        # Generate template using schema models
        content = generate_dockfile_template(
            name=name,
            framework=framework,
            handler_mode=handler,
            auth_mode=auth,
            streaming=streaming,
            include_secrets=secrets,
            include_cors=cors,
            include_observability=observability,
            include_metadata=metadata,
            secret_names=parsed_secret_names,
            streaming_events=parsed_streaming_events,
            async_runs=async_runs,
            streaming_backend=streaming_backend,
        )

        # Write file
        output_path.write_text(content)

        success(f"Created {output}")

        # Show configuration summary
        console.print("\n[bold cyan]Configuration:[/bold cyan]")
        console.print(f"  • Mode: [green]{'handler' if handler else 'entrypoint'}[/green]")
        console.print(f"  • Framework: [green]{framework if not handler else 'custom'}[/green]")
        console.print(f"  • Streaming: [green]{streaming}[/green]")
        if parsed_streaming_events:
            if isinstance(parsed_streaming_events, str):
                console.print(f"  • Events preset: [green]{parsed_streaming_events}[/green]")
            else:
                console.print(f"  • Events filter: [green]{', '.join(parsed_streaming_events)}[/green]")
        if async_runs:
            console.print("  • Async runs (/runs): [green]enabled[/green]")
        if streaming_backend != "memory":
            console.print(f"  • Backend: [green]{streaming_backend}[/green]")
        if auth:
            console.print(f"  • Auth: [green]{auth}[/green]")
        if secrets or parsed_secret_names:
            console.print("  • Secrets: [green]enabled[/green]")
        if cors:
            console.print("  • CORS: [green]enabled[/green]")
        if observability:
            console.print("  • Observability: [green]enabled[/green]")

        # Show next steps
        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        if handler:
            console.print("  1. Edit the Dockfile to customize your service:")
            console.print("     [dim]• Set the correct handler path[/dim]")
        else:
            console.print("  1. Edit the Dockfile to customize your agent:")
            console.print("     [dim]• Set the correct entrypoint[/dim]")
        console.print("     [dim]• Define input/output schema[/dim]")
        if auth == "api_key":
            console.print("     [dim]• Configure API key environment variable[/dim]")
        elif auth == "jwt":
            console.print("     [dim]• Configure JWT settings (jwks_url, issuer, audience)[/dim]")
        console.print("  2. Implement your agent code")
        console.print("  3. Validate the Dockfile:")
        console.print(f"     [cyan]dockrion validate {output}[/cyan]")
        console.print("  4. Test your agent:")
        console.print(f"     [cyan]dockrion test {output} --payload '{{}}'[/cyan]")

    except typer.Exit:
        raise
    except Exception as e:
        error(f"Failed to create Dockfile: {str(e)}")
        raise typer.Exit(1) from None
