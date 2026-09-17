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


@pytest.mark.asyncio
async def test_footer_sync_ok_renders_check():
    app = App()
    async with app.run_test():
        footer = GituxFooter()
        await app.mount(footer)
        footer.update_sync(ok=True)
        plain = footer.content.plain

        assert "\u2713" in plain  # ✓
        assert "\u2717" not in plain  # ✗


@pytest.mark.asyncio
async def test_footer_sync_fail_renders_cross():
    app = App()
    async with app.run_test():
        footer = GituxFooter()
        await app.mount(footer)
        footer.update_sync(ok=False)
        plain = footer.content.plain

        assert "\u2717" in plain  # ✗
        assert "\u2713" not in plain  # ✓


@pytest.mark.asyncio
async def test_footer_does_not_show_encoding():
    app = App()
    async with app.run_test():
        footer = GituxFooter()
        await app.mount(footer)
        footer.update_sync(ok=True)
        plain = footer.content.plain

        assert "UTF-8" not in plain
        assert "ISO-8859-1" not in plain
