"""CLI entry point using Typer."""

from typer import Typer, Option, echo, Exit

app = Typer(
    name="gitz",
    help="A beautiful, minimalist TUI for Git.",
    no_args_is_help=True,
)


@app.command()
def run(
    version: bool = Option(False, "--version", "-v", help="Show version and exit"),
):
    """Launch the GITZ TUI."""
    if version:
        echo("gitz 0.1.0")
        raise Exit()

    from gitz.ui.app import GitzApp

    gitz_app = GitzApp()
    gitz_app.run()
