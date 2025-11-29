"""Build command - Build Docker image for agent deployment."""
import typer
from pathlib import Path
from dockrion_sdk import deploy, load_dockspec
from .utils import console, success, error, info, warning, handle_error

app = typer.Typer()


@app.command(name="build")
def build(
    path: str = typer.Argument(
        "Dockfile.yaml",
        help="Path to Dockfile"
    ),
    target: str = typer.Option(
        "local",
        help="Deployment target (local for V1)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed output"
    )
):
    """
    Build a Docker image for the agent.
    
    This command creates a production-ready Docker image that includes:
    - Your agent code
    - FastAPI runtime server
    - All dependencies
    - Health checks and metrics endpoints
    
    Examples:
        dockrion build
        dockrion build custom/Dockfile.yaml
        dockrion build --verbose
    """
    try:
        # Validate file exists
        if not Path(path).exists():
            error(f"Dockfile not found: {path}")
            raise typer.Exit(1)
        
        # Load spec to show info
        try:
            spec = load_dockspec(path)
            agent_name = spec.agent.name
        except Exception as e:
            error(f"Failed to load Dockfile: {str(e)}")
            raise typer.Exit(1)
        
        info(f"Building Docker image for agent: [bold]{agent_name}[/bold]")
        
        if verbose:
            console.print()
            info("This may take a few minutes...")
        
        # Build image
        with console.status("[bold green]Building Docker image..."):
            result = deploy(path, target=target)
        
        # Show success
        console.print()
        success(f"Successfully built image: [bold cyan]{result['image']}[/bold cyan]")
        
        # Show next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Run locally:")
        console.print(f"     [cyan]docker run -p 8080:8080 {result['image']}[/cyan]")
        console.print(f"  2. Push to registry:")
        console.print(f"     [cyan]docker tag {result['image']} <registry>/{agent_name}:latest[/cyan]")
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

