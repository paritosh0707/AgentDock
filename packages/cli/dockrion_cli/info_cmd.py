"""Info commands - Version and doctor diagnostics."""
import typer
import sys
import subprocess
from pathlib import Path
from rich.table import Table
from .utils import console, success, warning, error, info

app = typer.Typer()


@app.command(name="version")
def version():
    """
    Show dockrion version information.
    
    Displays versions of:
    - CLI package
    - SDK package
    - Python runtime
    
    Examples:
        dockrion version
    """
    try:
        import dockrion_sdk
        cli_version = "0.1.0"
        sdk_version = dockrion_sdk.__version__
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        table = Table(title="dockrion Version Information", show_header=True, header_style="bold cyan")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        
        table.add_row("CLI", cli_version)
        table.add_row("SDK", sdk_version)
        table.add_row("Python", python_version)
        
        console.print(table)
        
    except Exception as e:
        error(f"Failed to get version info: {str(e)}")
        raise typer.Exit(1)


@app.command(name="doctor")
def doctor():
    """
    Diagnose common issues with your dockrion setup.
    
    Checks for:
    - Docker installation
    - Python version
    - Dockfile presence
    - Package installations
    
    Examples:
        dockrion doctor
    """
    console.print("[bold cyan]🔍 Running diagnostics...[/bold cyan]\n")
    
    issues = []
    checks_passed = 0
    total_checks = 0
    
    # Check Python version
    total_checks += 1
    if sys.version_info >= (3, 12):
        success(f"Python {sys.version.split()[0]}")
        checks_passed += 1
    else:
        warning(f"Python {sys.version.split()[0]} (3.12+ recommended)")
        issues.append("Upgrade to Python 3.12 or higher")
    
    # Check Docker
    total_checks += 1
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            docker_version = result.stdout.strip()
            success(f"Docker installed: {docker_version}")
            checks_passed += 1
        else:
            warning("Docker found but not responding correctly")
            issues.append("Check Docker installation")
    except FileNotFoundError:
        warning("Docker not found")
        issues.append("Install Docker: https://docs.docker.com/get-docker/")
    except subprocess.TimeoutExpired:
        warning("Docker command timed out")
        issues.append("Check if Docker daemon is running")
    except Exception as e:
        warning(f"Docker check failed: {str(e)}")
        issues.append("Verify Docker installation")
    
    # Check for Dockfile
    total_checks += 1
    dockfile_path = Path("Dockfile.yaml")
    if dockfile_path.exists():
        success("Found Dockfile.yaml in current directory")
        checks_passed += 1
        
        # Try to validate it
        try:
            from dockrion_sdk import validate_dockspec
            result = validate_dockspec(str(dockfile_path))
            if result["valid"]:
                success("Dockfile is valid")
            else:
                warning(f"Dockfile has validation errors ({len(result['errors'])} errors)")
                issues.append("Run 'dockrion validate' to see details")
        except Exception:
            pass
    else:
        info("No Dockfile.yaml in current directory")
        console.print("  [dim]Create one with: dockrion init <name>[/dim]")
    
    # Check SDK installation
    total_checks += 1
    try:
        import dockrion_sdk
        import dockrion_schema
        import dockrion_common
        import dockrion_adapters
        success("All dockrion packages installed")
        checks_passed += 1
    except ImportError as e:
        warning(f"Missing package: {str(e)}")
        issues.append("Install missing packages with: pip install dockrion-sdk")
    
    # Summary
    console.print()
    console.print("[bold]Summary:[/bold]")
    if checks_passed == total_checks:
        success(f"All checks passed! ({checks_passed}/{total_checks})")
        console.print("\n[bold green]✨ Your setup looks good![/bold green]")
    else:
        info(f"Passed {checks_passed}/{total_checks} checks")
        
        if issues:
            console.print("\n[bold yellow]📋 Action items:[/bold yellow]")
            for idx, issue in enumerate(issues, 1):
                console.print(f"  {idx}. {issue}")
    
    console.print()

