import pytest
from textual.app import App

from gitux.ui.widgets.gitux_footer import GituxFooter


@pytest.mark.asyncio
async def test_footer_lists_l_log():
    app = App()
    async with app.run_test():
        footer = GituxFooter()
        await app.mount(footer)
        footer._refresh()
        plain = footer.content.plain

        assert "[R] Refresh" in plain
        assert "[L] Log" in plain
        assert "[S] Stage" in plain
        assert plain.index("[R] Refresh") < plain.index("[L] Log") < plain.index("[S] Stage")