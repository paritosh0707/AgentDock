"""dockrion CLI - Main entry point."""
import typer
from . import validate_cmd, test_cmd, build_cmd, run_cmd, logs_cmd, init_cmd, info_cmd

app = typer.Typer(
    name="dockrion",
    help="dockrion CLI - Deploy and manage AI agents",
    no_args_is_help=True,
    add_completion=False
)

# Register all commands
app.command()(validate_cmd.validate)
app.command()(test_cmd.test)
app.command()(build_cmd.build)
app.command()(run_cmd.run)
app.command()(logs_cmd.logs)
app.command()(init_cmd.init)
app.command()(info_cmd.version)
app.command()(info_cmd.doctor)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
