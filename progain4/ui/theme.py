"""
Theme/Styling for PROGRAIN 4.0
Centralized styles with improved contrast and readability.
"""

# Modern theme with good contrast
PROGRAIN4_THEME = """
/* ========== GLOBAL ========== */
QMainWindow {
    background-color: #fafafa;
}

QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    background-color: #fafafa;
    color: #333333;
}

/* ========== DIALOGS ========== */
QDialog {
    background-color: #fafafa;
    color: #333333;
}

/* ========== GROUP BOXES ========== */
QGroupBox {
    font-weight: bold;
    color: #333333;
    border: 1px solid #cccccc;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: #1976D2;
    font-size: 11pt;
}

/* ========== LIST WIDGETS ========== */
QListWidget {
    background-color: #ffffff;
    border: none;
    outline: none;
    color: #333333;
}

QListWidget::item {
    padding: 12px;
    border-bottom: 1px solid #e0e0e0;
    color: #333333;
}

QListWidget::item:selected {
    background-color: #1976D2;
    color: #ffffff;
    font-weight: bold;
}

QListWidget::item:hover:!selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

/* ========== BUTTONS ========== */
QPushButton {
    background-color: #1976D2;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1565C0;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #BDBDBD;
    color: #757575;
}

/* ========== LABELS ========== */
QLabel {
    color: #333333;
}

/* ========== LINE EDITS ========== */
QLineEdit {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #333333;
}

QLineEdit:focus {
    border: 2px solid #1976D2;
}

QLineEdit:disabled {
    background-color: #F5F5F5;
    color: #999999;
}

/* ========== COMBO BOXES ========== */
QComboBox {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #333333;
}

QComboBox:hover {
    border: 1px solid #1976D2;
}

QComboBox:focus {
    border: 2px solid #1976D2;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    border: 1px solid #CCCCCC;
    background-color: #ffffff;
    color: #333333;
    selection-background-color: #1976D2;
    selection-color: #ffffff;
}

/* ========== TABLE WIDGETS ========== */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #F9F9F9;
    gridline-color: #E0E0E0;
    color: #333333;
    border: 1px solid #CCCCCC;
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QTableWidget::item:hover {
    background-color: #F5F5F5;
}

QHeaderView::section {
    background-color: #F5F5F5;
    color: #333333;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #1976D2;
    border-right: 1px solid #E0E0E0;
    font-weight: bold;
}

/* ========== SCROLL BARS ========== */
QScrollBar:vertical {
    border: none;
    background-color: #F5F5F5;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #BDBDBD;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9E9E9E;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #F5F5F5;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #BDBDBD;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #9E9E9E;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ========== SPLITTER ========== */
QSplitter::handle {
    background-color: #E0E0E0;
}

QSplitter::handle:hover {
    background-color: #BDBDBD;
}

/* ========== TAB WIDGET ========== */
QTabWidget::pane {
    border: 1px solid #CCCCCC;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #F5F5F5;
    color: #666666;
    padding: 8px 16px;
    border: 1px solid #CCCCCC;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1976D2;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #E3F2FD;
}

/* ========== MENU BAR ========== */
QMenuBar {
    background-color: #ffffff;
    color: #333333;
    border-bottom: 1px solid #E0E0E0;
}

QMenuBar::item {
    padding: 8px 12px;
    background-color: transparent;
}

QMenuBar::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QMenu {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #CCCCCC;
}

QMenu::item {
    padding: 8px 24px;
}

QMenu::item:selected {
    background-color: #1976D2;
    color: #ffffff;
}

/* ========== CHECKBOXES ========== */
QCheckBox {
    color: #333333;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #CCCCCC;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #1976D2;
    border-color: #1976D2;
}

QCheckBox::indicator:hover {
    border-color: #1976D2;
}

/* ========== RADIO BUTTONS ========== */
QRadioButton {
    color: #333333;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #CCCCCC;
    border-radius: 9px;
    background-color: #ffffff;
}

QRadioButton::indicator:checked {
    background-color: #1976D2;
    border-color: #1976D2;
}

QRadioButton::indicator:hover {
    border-color: #1976D2;
}

/* ========== DATE EDIT ========== */
QDateEdit {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #333333;
}

QDateEdit:focus {
    border: 2px solid #1976D2;
}

QDateEdit::drop-down {
    border: none;
    width: 20px;
}

/* ========== SPIN BOX ========== */
QSpinBox,
QDoubleSpinBox {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #333333;
}

QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 2px solid #1976D2;
}

/* ========== TEXT EDIT ========== */
QTextEdit,
QPlainTextEdit {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #333333;
}

QTextEdit:focus,
QPlainTextEdit:focus {
    border: 2px solid #1976D2;
}

/* ========== PROGRESS BAR ========== */
QProgressBar {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    background-color: #F5F5F5;
    text-align: center;
    color: #333333;
}

QProgressBar::chunk {
    background-color: #1976D2;
    border-radius: 3px;
}

/* ========== TOOL TIP ========== */
QToolTip {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #333333;
    padding: 4px;
    border-radius: 4px;
}
"""

def get_theme() -> str:
    """Get the complete PROGRAIN 4.0 theme stylesheet."""
    return PROGRAIN4_THEME
