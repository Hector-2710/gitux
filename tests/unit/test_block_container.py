"""Tests for gitux.ui.widgets.block_container.BlockContainer (Fix 1)."""

import pytest
from textual.app import App

from gitux.ui.widgets.block_container import BlockContainer


def test_unmounted_block_is_inactive_by_default() -> None:
    block = BlockContainer(title="x")
    assert "block-inactive" in block.classes
    assert "block-active" not in block.classes


@pytest.mark.asyncio
async def test_mounted_block_is_inactive_by_default() -> None:
    app = App()
    block = BlockContainer(title="x")
    async with app.run_test():
        await app.mount(block)
        assert "block-inactive" in block.classes
        assert "block-active" not in block.classes


@pytest.mark.asyncio
async def test_empty_title_renders_subtitle_alone() -> None:
    app = App()
    block = BlockContainer(title="")
    async with app.run_test():
        await app.mount(block)
        block.set_header_subtitle("N items")
        assert block.query_one(".block-header").content == "N items"


@pytest.mark.asyncio
async def test_empty_title_no_subtitle_renders_empty() -> None:
    app = App()
    block = BlockContainer(title="")
    async with app.run_test():
        await app.mount(block)
        assert block.query_one(".block-header").content == ""


def test_empty_title_render_header_subtitle_alone() -> None:
    block = BlockContainer(title="")
    block._subtitle = "N items"
    assert block._render_header() == "N items"


def test_empty_title_render_header_empty() -> None:
    block = BlockContainer(title="")
    assert block._render_header() == ""
