import pytest
from textual.app import App

from gitux.ui.widgets.gitux_footer import GituxFooter


@pytest.mark.asyncio
async def test_footer_shows_version_and_help():
    app = App()
    async with app.run_test():
        footer = GituxFooter()
        await app.mount(footer)
        footer._refresh()
        plain = footer.content.plain

        assert "GITUX v" in plain
        assert "[?] Help" in plain