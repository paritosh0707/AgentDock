"""Test command - Test agent locally without starting a server."""
import typer
import json
from pathlib import Path
from dockrion_sdk import invoke_local
from .utils import (
    console, success, error, info,
    handle_error, print_dict_as_json
)

app = typer.Typer()


@app.command(name="test")
def test(
    path: str = typer.Argument(
        "Dockfile.yaml",
        help="Path to Dockfile"
    ),
    payload: str = typer.Option(
        None,
        "--payload", "-p",
        help="JSON payload as string"
    ),
    payload_file: str = typer.Option(
        None,
        "--payload-file", "-f",
        help="Path to JSON file with payload"
    ),
    output_file: str = typer.Option(
        None,
        "--output", "-o",
        help="Save output to file"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed output"
    )
):
    """
    Test an agent locally without starting a server.
    
    This command loads your agent and invokes it with test input,
    allowing you to verify functionality before deployment.
    
    Examples:
        dockrion test --payload '{"text": "hello"}'
        dockrion test --payload-file input.json
        dockrion test -f input.json -o output.json
        dockrion test --verbose
    """
    try:
        # Validate Dockfile exists
        if not Path(path).exists():
            error(f"Dockfile not found: {path}")
            raise typer.Exit(1)
        
        # Load payload
        payload_data = None
        if payload_file:
            try:
                with open(payload_file, 'r') as f:
                    payload_data = json.load(f)
                if verbose:
                    info(f"Loaded payload from {payload_file}")
            except FileNotFoundError:
                error(f"Payload file not found: {payload_file}")
                raise typer.Exit(1)
            except json.JSONDecodeError as e:
                error(f"Invalid JSON in payload file: {str(e)}")
                raise typer.Exit(1)
        elif payload:
            try:
                payload_data = json.loads(payload)
                if verbose:
                    info("Parsed payload from command line")
            except json.JSONDecodeError as e:
                error(f"Invalid JSON payload: {str(e)}")
                console.print("\n[dim]💡 Tip: Ensure JSON is properly formatted with quotes[/dim]")
                raise typer.Exit(1)
        else:
            error("No payload provided")
            console.print("\n[dim]Provide input using either:[/dim]")
            console.print("  • [cyan]--payload '{\"key\": \"value\"}'[/cyan]")
            console.print("  • [cyan]--payload-file input.json[/cyan]")
            raise typer.Exit(1)
        
        # Show what we're doing
        if verbose:
            info(f"Testing agent from {path}")
            console.print("\n[bold]Input payload:[/bold]")
            print_dict_as_json(payload_data, "Input")
        
        # Invoke agent
        with console.status("[bold green]Invoking agent..."):
            result = invoke_local(path, payload_data)
        
        # Show success
        success("Agent invocation successful")
        
        # Print output
        console.print()
        print_dict_as_json(result, "Agent Output")
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                info(f"Output saved to {output_file}")
            except Exception as e:
                warning(f"Failed to save output: {str(e)}")
        
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        info("\nTest cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        handle_error(e, verbose)
        raise typer.Exit(1)

