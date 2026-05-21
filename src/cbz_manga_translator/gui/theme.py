from __future__ import annotations

APP_STYLESHEET = """
QWidget {
    font-size: 14px;
}
QMainWindow, QWidget {
    background-color: #202124;
    color: #f1f3f4;
}
QGroupBox {
    font-weight: 600;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    border: 1px solid #3c4043;
    border-radius: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QTabWidget::pane {
    border: 1px solid #3c4043;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    padding: 10px 16px;
    margin-right: 4px;
    border: 1px solid #3c4043;
    border-bottom: 0;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    background-color: #2a2b2e;
    color: #d8dee5;
}
QTabBar::tab:selected {
    background-color: #303134;
    color: #ffffff;
}
QTabBar::tab:hover {
    background-color: #383a3f;
}
QPushButton {
    padding: 8px 12px;
    min-height: 30px;
    border: 1px solid #5f6368;
    border-radius: 6px;
    background-color: #303134;
}
QPushButton:hover {
    background-color: #3c4043;
}
QPushButton:disabled {
    color: #858585;
    background-color: #252628;
    border-color: #3a3b3d;
}
QComboBox, QLineEdit, QDoubleSpinBox, QPlainTextEdit {
    border: 1px solid #5f6368;
    border-radius: 6px;
    background-color: #17181a;
    color: #f1f3f4;
    selection-background-color: #415a77;
}
QComboBox, QLineEdit, QDoubleSpinBox {
    padding: 6px 8px;
    min-height: 28px;
}
QTableWidget {
    gridline-color: rgba(128,128,128,0.25);
    alternate-background-color: #242528;
    background-color: #17181a;
    font-size: 14px;
}
QTableWidget::item {
    padding: 10px;
}
QTableWidget::item:selected {
    background-color: #334b63;
}
QHeaderView::section {
    padding: 9px;
    font-weight: 600;
    background-color: #303134;
    color: #f1f3f4;
    border: 0;
    border-right: 1px solid #44474a;
}
QPlainTextEdit {
    font-family: Consolas, 'Cascadia Mono', 'DejaVu Sans Mono', monospace;
    font-size: 14px;
    padding: 10px;
    line-height: 1.35em;
}
QScrollArea {
    border: 0;
    background: transparent;
}
QScrollBar:vertical {
    width: 14px;
    margin: 0;
    background: #202124;
}
QScrollBar::handle:vertical {
    min-height: 36px;
    border-radius: 7px;
    background: #5f6368;
}
QScrollBar::handle:vertical:hover {
    background: #7a7f85;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    height: 14px;
    margin: 0;
    background: #202124;
}
QScrollBar::handle:horizontal {
    min-width: 36px;
    border-radius: 7px;
    background: #5f6368;
}
QScrollBar::handle:horizontal:hover {
    background: #7a7f85;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QLabel#detailTitle {
    font-size: 18px;
    font-weight: 700;
}
QLabel#sectionTitle {
    font-size: 17px;
    font-weight: 700;
    padding-bottom: 4px;
}
QLabel#fieldLabel {
    font-size: 13px;
    font-weight: 700;
    color: #d8dee5;
    padding-top: 6px;
}
QLabel#summaryLabel {
    color: #c8d1da;
    padding: 4px 2px;
}
QLabel#statusPill {
    padding: 6px 10px;
    border-radius: 12px;
    background-color: #17324d;
    color: #d7ecff;
    font-weight: 700;
}
QLabel#warningPill {
    padding: 6px 10px;
    border-radius: 12px;
    background-color: #4a3415;
    color: #ffd89b;
    font-weight: 700;
}
QLabel#mutedText {
    color: #bdc1c6;
}
QSplitter::handle {
    background-color: #3c4043;
}
"""
