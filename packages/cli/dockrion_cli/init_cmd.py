"""Init command - Create new Dockfile template."""

from pathlib import Path

import typer
from dockrion_schema import (
    AgentConfig,
    DockSpec,
    ExposeConfig,
    IOSchema,
    IOSubSchema,
    to_yaml_string,
)

from .utils import confirm_action, console, error, success, warning

app = typer.Typer()


def generate_dockfile_template(name: str) -> str:
    """Generate a Dockfile template using schema models.

    This ensures the template is always in sync with the schema definition
    and produces valid, validated output.

    Args:
        name: Agent name (lowercase with hyphens)

    Returns:
        YAML string representation of the Dockfile template
    """
    spec = DockSpec(
        version="1.0",
        agent=AgentConfig(
            name=name,
            description=f"dockrion agent: {name}",
            entrypoint="app.main:build_agent",
            framework="langgraph",
        ),
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
        expose=ExposeConfig(
            port=8080,
            host="0.0.0.0",
        ),
    )
    return to_yaml_string(spec)


@app.command(name="init")
def init(
    name: str = typer.Argument(..., help="Agent name (lowercase with hyphens)"),
    output: str = typer.Option("Dockfile.yaml", "--output", "-o", help="Output file path"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing file without asking"
    ),
):
    """
    Create a new Dockfile template.

    This generates a starter Dockfile with common configuration.
    You can then customize it for your specific agent.

    Examples:
        dockrion init my-agent
        dockrion init my-agent --output custom/Dockfile.yaml
        dockrion init my-agent --force
    """
    try:
        # Validate agent name
        if not name.replace("-", "").replace("_", "").isalnum():
            error("Agent name must contain only letters, numbers, hyphens, and underscores")
            raise typer.Exit(1)

        output_path = Path(output)

        # Check if file exists
        if output_path.exists() and not force:
            if not confirm_action(f"{output} already exists. Overwrite?", default=False):
                warning("Cancelled")
                raise typer.Exit(0)

        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate template using schema models
        content = generate_dockfile_template(name)

        # Write file
        output_path.write_text(content)

        success(f"Created {output}")

        # Show next steps
        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print("  1. Edit the Dockfile to customize your agent:")
        console.print("     [dim]• Set the correct entrypoint[/dim]")
        console.print("     [dim]• Define input/output schema[/dim]")
        console.print("  2. Implement your agent code")
        console.print("  3. Validate the Dockfile:")
        console.print(f"     [cyan]dockrion validate {output}[/cyan]")
        console.print("  4. Test your agent:")
        console.print(f"     [cyan]dockrion test {output} --payload '{{}}'[/cyan]")

    except typer.Exit:
        raise
    except Exception as e:
        error(f"Failed to create Dockfile: {str(e)}")
        raise typer.Exit(1)
