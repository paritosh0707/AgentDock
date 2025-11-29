"""Validate command - Validate Dockfile configuration."""
import typer
from pathlib import Path
from dockrion_sdk import validate_dockspec, load_dockspec
from .utils import (
    console, success, error, warning, info,
    print_validation_result, handle_error, print_agent_info
)

app = typer.Typer()


@app.command(name="validate")
def validate(
    path: str = typer.Argument(
        "Dockfile.yaml",
        help="Path to Dockfile to validate"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed output including full spec"
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Only show errors, no warnings or info"
    )
):
    """
    Validate a Dockfile configuration.
    
    This command checks your Dockfile for:
    - Syntax errors (invalid YAML)
    - Schema validation (missing/invalid fields)
    - Format validation (entrypoint, names, ports)
    - Potential issues (warnings for best practices)
    
    Examples:
        dockrion validate
        dockrion validate custom/Dockfile.yaml
        dockrion validate --verbose
    """
    try:
        # Check if file exists
        file_path = Path(path)
        if not file_path.exists():
            error(f"File not found: {path}")
            if not quiet:
                console.print("\n[dim]💡 Tip: Create a new Dockfile with 'dockrion init <name>'[/dim]")
            raise typer.Exit(1)
        
        # Validate
        if not quiet:
            with console.status("[bold green]Validating Dockfile..."):
                result = validate_dockspec(path)
        else:
            result = validate_dockspec(path)
        
        # Handle result
        if result["valid"]:
            success(result["message"])
            
            # Show warnings if any
            if result["warnings"] and not quiet:
                console.print()
                warning(f"Found {len(result['warnings'])} warning(s):")
                for w in result["warnings"]:
                    console.print(f"  • {w}")
                console.print("\n[dim]💡 These are suggestions, not errors. Your Dockfile is still valid.[/dim]")
            
            # Show agent info in verbose mode
            if verbose and result["spec"]:
                console.print()
                spec_data = result["spec"].model_dump()
                print_agent_info(spec_data)
            
            return  # Success
        else:
            # Validation failed
            error("Validation failed")
            console.print()
            print_validation_result(result)
            
            if not quiet:
                console.print("\n[dim]💡 Tip: Check the documentation for Dockfile schema requirements[/dim]")
            raise typer.Exit(1)
            
    except typer.Exit:
        raise
    except Exception as e:
        handle_error(e, verbose)
        raise typer.Exit(1)
