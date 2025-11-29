"""Run command - Run agent server locally for development."""
import typer
import signal
from pathlib import Path
from dockrion_sdk import run_local, load_dockspec
from .utils import console, success, error, info, handle_error

app = typer.Typer()


@app.command(name="run")
def run(
    path: str = typer.Argument(
        "Dockfile.yaml",
        help="Path to Dockfile"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed output"
    )
):
    """
    Run agent server locally for development.
    
    This starts a FastAPI server that exposes your agent through HTTP endpoints:
    - POST /invoke - Invoke the agent
    - GET /health - Health check
    - GET /schema - Input/output schema
    - GET /metrics - Prometheus metrics
    
    Press Ctrl+C to stop the server.
    
    Examples:
        dockrion run
        dockrion run custom/Dockfile.yaml
        dockrion run --verbose
    """
    try:
        # Validate file exists
        if not Path(path).exists():
            error(f"Dockfile not found: {path}")
            raise typer.Exit(1)
        
        # Load spec to get server info
        try:
            spec = load_dockspec(path)
            port = spec.expose.port if spec.expose else 8080
            host = spec.expose.host if spec.expose else "0.0.0.0"
        except Exception as e:
            error(f"Failed to load Dockfile: {str(e)}")
            raise typer.Exit(1)
        
        info(f"Starting agent server from {path}...")
        console.print()
        
        # Start server
        proc = run_local(path)
        
        console.print()
        success(f"Server started at [bold]http://{host}:{port}[/bold]")
        
        # Show available endpoints
        console.print("\n[bold cyan]Available endpoints:[/bold cyan]")
        console.print(f"  • POST http://{host}:{port}/invoke - Invoke agent")
        console.print(f"  • GET  http://{host}:{port}/health - Health check")
        console.print(f"  • GET  http://{host}:{port}/schema - I/O schema")
        console.print(f"  • GET  http://{host}:{port}/metrics - Metrics")
        
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
            except:
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

