"""CLI entry point using Typer."""

from typer import Typer, Option, echo, Exit

app = Typer(
    name="gitux",
    help="A beautiful, minimalist TUI for Git.",
    no_args_is_help=True,
)


@app.command()
def run(
    version: bool = Option(False, "--version", "-v", help="Show version and exit"),
):
    """Launch the GITUX TUI."""
    if version:
        from gitux import __version__

        echo(f"gitux {__version__}")
        raise Exit()

    from gitux.ui.app import GituxApp

    gitux_app = GituxApp()
    gitux_app.run()


def main() -> None:
    """Console script entry point."""
    app()


if __name__ == "__main__":
    main()
