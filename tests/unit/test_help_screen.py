from gitux.ui.widgets.help_screen import HelpScreen


def test_help_promotes_l_and_two_panel_tab():
    text = HelpScreen._build_help_text().plain

    assert "Next section (Files/Diff)" in text

    log_line = next(line for line in text.splitlines() if "Commit log" in line)
    assert log_line.strip().startswith("l")

    coming_soon = text.index("Coming Soon")
    assert "Commit log" not in text[coming_soon:]