"""Init command - Create new Dockfile template."""
import typer
from pathlib import Path
from .utils import console, success, error, info, warning, confirm_action

app = typer.Typer()

DOCKFILE_TEMPLATE = '''version: "1.0"
agent:
  name: {name}
  description: "{description}"
  entrypoint: app.main:build_agent
  framework: langgraph
model:
  provider: openai
  name: gpt-4o-mini
  temperature: 0.7
  max_tokens: 1500
io_schema:
  input:
    type: object
    properties:
      text: {{ type: string }}
  output:
    type: object
    properties:
      result: {{ type: string }}
expose:
  port: 8080
  host: "0.0.0.0"
'''


@app.command(name="init")
def init(
    name: str = typer.Argument(
        ...,
        help="Agent name (lowercase with hyphens)"
    ),
    output: str = typer.Option(
        "Dockfile.yaml",
        "--output", "-o",
        help="Output file path"
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing file without asking"
    )
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
        if not name.replace('-', '').replace('_', '').isalnum():
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
        
        # Generate template
        content = DOCKFILE_TEMPLATE.format(
            name=name,
            description=f"dockrion agent: {name}"
        )
        
        # Write file
        output_path.write_text(content)
        
        success(f"Created {output}")
        
        # Show next steps
        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print("  1. Edit the Dockfile to customize your agent:")
        console.print(f"     [dim]• Set the correct entrypoint[/dim]")
        console.print(f"     [dim]• Configure the model settings[/dim]")
        console.print(f"     [dim]• Define input/output schema[/dim]")
        console.print(f"  2. Implement your agent code")
        console.print(f"  3. Validate the Dockfile:")
        console.print(f"     [cyan]dockrion validate {output}[/cyan]")
        console.print(f"  4. Test your agent:")
        console.print(f"     [cyan]dockrion test {output} --payload '{{}}'[/cyan]")
        
    except typer.Exit:
        raise
    except Exception as e:
        error(f"Failed to create Dockfile: {str(e)}")
        raise typer.Exit(1)

