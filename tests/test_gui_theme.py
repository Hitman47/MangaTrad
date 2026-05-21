from __future__ import annotations

from cbz_manga_translator.gui.theme import APP_STYLESHEET


def test_theme_defines_readable_tabs_and_scrollbars() -> None:
    assert "QTabWidget::pane" in APP_STYLESHEET
    assert "QTabBar::tab" in APP_STYLESHEET
    assert "QScrollBar:vertical" in APP_STYLESHEET
    assert "QLabel#fieldLabel" in APP_STYLESHEET
