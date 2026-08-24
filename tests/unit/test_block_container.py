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
