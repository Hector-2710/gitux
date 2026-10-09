"""Tests for the ErrorLine widget (skeleton K2 / structure T3)."""

import pytest

from gitux.ui.widgets.error_line import ErrorLine


@pytest.mark.asyncio
async def test_error_line_hidden_by_default():
    app = _MinimalApp()
    async with app.run_test():
        line = app.query_one("#test-error-line", ErrorLine)
        assert line.display is False
        assert str(line.content) == ""


@pytest.mark.asyncio
async def test_error_line_shows_message_with_symbol():
    app = _MinimalApp()
    async with app.run_test():
        line = app.query_one("#test-error-line", ErrorLine)
        line.show("push rejected: remote moved forward \u2192 press p to pull")
        assert line.display is True
        assert "\u2717" in str(line.content)  # ⨯ symbol (surface V5)
        assert "press p to pull" in str(line.content)


@pytest.mark.asyncio
async def test_error_line_clear_hides_again():
    app = _MinimalApp()
    async with app.run_test():
        line = app.query_one("#test-error-line", ErrorLine)
        line.show("something broke \u2192 press ? for help")
        assert line.display is True
        line.clear()
        assert line.display is False
        assert str(line.content) == ""


from textual.app import App, ComposeResult  # noqa: E402


class _MinimalApp(App[None]):
    """Minimal host so the ErrorLine can mount in a real widget tree."""

    def compose(self) -> ComposeResult:
        yield ErrorLine(id="test-error-line")
