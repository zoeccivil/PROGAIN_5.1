"""
Centralized theme management for PROGRAIN 4.0/5.0

Provides:
- Multiple color schemes (light, dark, blue, green)
- Runtime theme switching
- Consistent styling across the application
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


# Current active theme
_current_theme = "light"


# Theme definitions
THEMES: Dict[str, str] = {}


# ============================================================================
# LIGHT THEME (Default - formalized version of existing theme)
# ============================================================================
THEMES["light"] = """
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

/* ========== TOOLBAR ========== */
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #E0E0E0;
    spacing: 8px;
    padding: 4px;
}

/* ========== SIDEBAR (Light theme specific) ========== */
#sidebar {
    background-color: #f0f3f8;
    color: #2b3f5c;
    border-right: 1px solid #d0d7e3;
}

#sidebarHeader {
    background-color: #f0f3f8;
    color: #2b3f5c;
    font-weight: bold;
}

#sidebarFooter {
    background-color: #f0f3f8;
    color: #2b3f5c;
}

#sidebar QLabel.sectionTitle {
    color: #7a8aa6;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Botones de navegación del sidebar (Dashboard, Transacciones, etc.) */
QPushButton#sidebarNavButton {
    background-color: transparent;
    color: #2b3f5c;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: left;
}

QPushButton#sidebarNavButton:hover {
    background-color: #e1e7f3;
}

QPushButton#sidebarNavButton:checked {
    background-color: #2563eb;
    color: white;
}

/* Botones de cuentas del sidebar */
QPushButton#sidebarAccountButton {
    background-color: transparent;
    color: #2b3f5c;
    border-radius: 6px;
    padding: 4px 8px;
    text-align: left;
}

QPushButton#sidebarAccountButton:hover {
    background-color: #e1e7f3;
}

QPushButton#sidebarAccountButton:checked {
    background-color: #2563eb;
    color: white;
}

/* Botones de acciones rápidas del sidebar */
QPushButton#sidebarQuickButton {
    background-color: transparent;
    color: #2b3f5c;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: left;
}

QPushButton#sidebarQuickButton:hover {
    background-color: #e1e7f3;
}
"""


# ============================================================================
# DARK THEME
# ============================================================================
THEMES["dark"] = """
/* ========== GLOBAL ========== */
QMainWindow {
    background-color: #1e1e1e;
}

QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    background-color: #1e1e1e;
    color: #e0e0e0;
}

/* ========== DIALOGS ========== */
QDialog {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

/* ========== GROUP BOXES ========== */
QGroupBox {
    font-weight: bold;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: #2d2d2d;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: #64B5F6;
    font-size: 11pt;
}

/* ========== LIST WIDGETS ========== */
QListWidget {
    background-color: #2d2d2d;
    border: none;
    outline: none;
    color: #e0e0e0;
}

QListWidget::item {
    padding: 12px;
    border-bottom: 1px solid #404040;
    color: #e0e0e0;
}

QListWidget::item:selected {
    background-color: #1976D2;
    color: #ffffff;
    font-weight: bold;
}

QListWidget::item:hover:!selected {
    background-color: #383838;
    color: #64B5F6;
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
    background-color: #2196F3;
}

QPushButton:pressed {
    background-color: #1565C0;
}

QPushButton:disabled {
    background-color: #404040;
    color: #808080;
}

/* ========== LABELS ========== */
QLabel {
    color: #e0e0e0;
}

/* ========== LINE EDITS ========== */
QLineEdit {
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
    background-color: #2d2d2d;
    color: #e0e0e0;
}

QLineEdit:focus {
    border: 2px solid #1976D2;
}

QLineEdit:disabled {
    background-color: #252525;
    color: #808080;
}

/* ========== COMBO BOXES ========== */
QComboBox {
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
    background-color: #2d2d2d;
    color: #e0e0e0;
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
    border: 1px solid #404040;
    background-color: #2d2d2d;
    color: #e0e0e0;
    selection-background-color: #1976D2;
    selection-color: #ffffff;
}

/* ========== TABLE WIDGETS ========== */
QTableWidget {
    background-color: #2d2d2d;
    alternate-background-color: #252525;
    gridline-color: #404040;
    color: #e0e0e0;
    border: 1px solid #404040;
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:selected {
    background-color: #1976D2;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #383838;
}

QHeaderView::section {
    background-color: #252525;
    color: #e0e0e0;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #1976D2;
    border-right: 1px solid #404040;
    font-weight: bold;
}

/* ========== SCROLL BARS ========== */
QScrollBar:vertical {
    border: none;
    background-color: #252525;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #505050;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #606060;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #252525;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #505050;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #606060;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ========== SPLITTER ========== */
QSplitter::handle {
    background-color: #404040;
}

QSplitter::handle:hover {
    background-color: #505050;
}

/* ========== TAB WIDGET ========== */
QTabWidget::pane {
    border: 1px solid #404040;
    background-color: #2d2d2d;
}

QTabBar::tab {
    background-color: #252525;
    color: #808080;
    padding: 8px 16px;
    border: 1px solid #404040;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #2d2d2d;
    color: #64B5F6;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #383838;
}

/* ========== MENU BAR ========== */
QMenuBar {
    background-color: #252525;
    color: #e0e0e0;
    border-bottom: 1px solid #404040;
}

QMenuBar::item {
    padding: 8px 12px;
    background-color: transparent;
}

QMenuBar::item:selected {
    background-color: #383838;
    color: #64B5F6;
}

QMenu {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #404040;
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
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #404040;
    border-radius: 3px;
    background-color: #2d2d2d;
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
    color: #e0e0e0;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #404040;
    border-radius: 9px;
    background-color: #2d2d2d;
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
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
    background-color: #2d2d2d;
    color: #e0e0e0;
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
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
    background-color: #2d2d2d;
    color: #e0e0e0;
}

QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 2px solid #1976D2;
}

/* ========== TEXT EDIT ========== */
QTextEdit,
QPlainTextEdit {
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px;
    background-color: #2d2d2d;
    color: #e0e0e0;
}

QTextEdit:focus,
QPlainTextEdit:focus {
    border: 2px solid #1976D2;
}

/* ========== PROGRESS BAR ========== */
QProgressBar {
    border: 1px solid #404040;
    border-radius: 4px;
    background-color: #252525;
    text-align: center;
    color: #e0e0e0;
}

QProgressBar::chunk {
    background-color: #1976D2;
    border-radius: 3px;
}

/* ========== TOOL TIP ========== */
QToolTip {
    background-color: #383838;
    color: #e0e0e0;
    border: 1px solid #505050;
    padding: 4px;
    border-radius: 4px;
}

/* ========== TOOLBAR ========== */
QToolBar {
    background-color: #252525;
    border-bottom: 1px solid #404040;
    spacing: 8px;
    padding: 4px;
}

/* ========== SIDEBAR (Dark theme specific) ========== */
#sidebar {
    background-color: #0D47A1;
}

#sidebarHeader {
    background-color: #0a3c8a;
}

#sidebarFooter {
    background-color: #0a3c8a;
}
"""


# ============================================================================
# BLUE THEME (Blue accent variant)
# ============================================================================
THEMES["blue"] = """
/* ========== GLOBAL ========== */
QMainWindow {
    background-color: #e3f2fd;
}

QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    background-color: #e3f2fd;
    color: #01579b;
}

/* ========== DIALOGS ========== */
QDialog {
    background-color: #e3f2fd;
    color: #01579b;
}

/* ========== GROUP BOXES ========== */
QGroupBox {
    font-weight: bold;
    color: #01579b;
    border: 1px solid #90caf9;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: #0277bd;
    font-size: 11pt;
}

/* ========== LIST WIDGETS ========== */
QListWidget {
    background-color: #ffffff;
    border: none;
    outline: none;
    color: #01579b;
}

QListWidget::item {
    padding: 12px;
    border-bottom: 1px solid #bbdefb;
    color: #01579b;
}

QListWidget::item:selected {
    background-color: #0277bd;
    color: #ffffff;
    font-weight: bold;
}

QListWidget::item:hover:!selected {
    background-color: #bbdefb;
    color: #01579b;
}

/* ========== BUTTONS ========== */
QPushButton {
    background-color: #0277bd;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #01579b;
}

QPushButton:pressed {
    background-color: #003c6f;
}

QPushButton:disabled {
    background-color: #b0bec5;
    color: #607d8b;
}

/* Other elements inherit light theme with blue accents... */
QLineEdit {
    border: 1px solid #90caf9;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #01579b;
}

QLineEdit:focus {
    border: 2px solid #0277bd;
}

QComboBox {
    border: 1px solid #90caf9;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #01579b;
}

QComboBox:focus {
    border: 2px solid #0277bd;
}

QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f1f8fe;
    gridline-color: #bbdefb;
    color: #01579b;
    border: 1px solid #90caf9;
}

QTableWidget::item:selected {
    background-color: #bbdefb;
    color: #01579b;
}

QHeaderView::section {
    background-color: #e3f2fd;
    color: #01579b;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #0277bd;
    border-right: 1px solid #bbdefb;
    font-weight: bold;
}

QMenuBar {
    background-color: #ffffff;
    color: #01579b;
    border-bottom: 1px solid #90caf9;
}

QMenuBar::item:selected {
    background-color: #bbdefb;
    color: #01579b;
}

QMenu {
    background-color: #ffffff;
    color: #01579b;
    border: 1px solid #90caf9;
}

QMenu::item:selected {
    background-color: #0277bd;
    color: #ffffff;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #90caf9;
    spacing: 8px;
    padding: 4px;
}

#sidebar {
    background-color: #0277bd;
}

#sidebarHeader {
    background-color: #01579b;
}

#sidebarFooter {
    background-color: #01579b;
}
"""


# ============================================================================
# GREEN THEME (Green/eco accent variant)
# ============================================================================
THEMES["green"] = """
/* ========== GLOBAL ========== */
QMainWindow {
    background-color: #f1f8e9;
}

QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
    background-color: #f1f8e9;
    color: #1b5e20;
}

/* ========== DIALOGS ========== */
QDialog {
    background-color: #f1f8e9;
    color: #1b5e20;
}

/* ========== GROUP BOXES ========== */
QGroupBox {
    font-weight: bold;
    color: #1b5e20;
    border: 1px solid #aed581;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: #388e3c;
    font-size: 11pt;
}

/* ========== LIST WIDGETS ========== */
QListWidget {
    background-color: #ffffff;
    border: none;
    outline: none;
    color: #1b5e20;
}

QListWidget::item {
    padding: 12px;
    border-bottom: 1px solid #c5e1a5;
    color: #1b5e20;
}

QListWidget::item:selected {
    background-color: #388e3c;
    color: #ffffff;
    font-weight: bold;
}

QListWidget::item:hover:!selected {
    background-color: #c5e1a5;
    color: #1b5e20;
}

/* ========== BUTTONS ========== */
QPushButton {
    background-color: #388e3c;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2e7d32;
}

QPushButton:pressed {
    background-color: #1b5e20;
}

QPushButton:disabled {
    background-color: #b0bec5;
    color: #607d8b;
}

QLineEdit {
    border: 1px solid #aed581;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #1b5e20;
}

QLineEdit:focus {
    border: 2px solid #388e3c;
}

QComboBox {
    border: 1px solid #aed581;
    border-radius: 4px;
    padding: 6px;
    background-color: #ffffff;
    color: #1b5e20;
}

QComboBox:focus {
    border: 2px solid #388e3c;
}

QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f9fdf7;
    gridline-color: #c5e1a5;
    color: #1b5e20;
    border: 1px solid #aed581;
}

QTableWidget::item:selected {
    background-color: #c5e1a5;
    color: #1b5e20;
}

QHeaderView::section {
    background-color: #f1f8e9;
    color: #1b5e20;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #388e3c;
    border-right: 1px solid #c5e1a5;
    font-weight: bold;
}

QMenuBar {
    background-color: #ffffff;
    color: #1b5e20;
    border-bottom: 1px solid #aed581;
}

QMenuBar::item:selected {
    background-color: #c5e1a5;
    color: #1b5e20;
}

QMenu {
    background-color: #ffffff;
    color: #1b5e20;
    border: 1px solid #aed581;
}

QMenu::item:selected {
    background-color: #388e3c;
    color: #ffffff;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #aed581;
    spacing: 8px;
    padding: 4px;
}

#sidebar {
    background-color: #388e3c;
}

#sidebarHeader {
    background-color: #2e7d32;
}

#sidebarFooter {
    background-color: #2e7d32;
}
"""


# ============================================================================
# Theme Management Functions
# ============================================================================

def get_available_themes() -> List[str]:
    """
    Get list of available theme names.
    
    Returns:
        List of theme names (e.g., ["light", "dark", "blue", "green"])
    """
    return list(THEMES.keys())


def get_current_theme() -> str:
    """
    Get the name of the currently active theme.
    
    Returns:
        Current theme name
    """
    return _current_theme


def apply_theme(app, theme_name: str) -> None:
    """
    Apply a theme to the application.
    
    Args:
        app: QApplication instance
        theme_name: Name of the theme to apply (e.g., "light", "dark", "blue", "green")
    
    Raises:
        ValueError: If theme_name is not valid
    """
    global _current_theme
    
    if theme_name not in THEMES:
        available = ", ".join(get_available_themes())
        raise ValueError(
            f"Invalid theme '{theme_name}'. Available themes: {available}"
        )
    
    logger.info(f"Applying theme: {theme_name}")
    
    # Apply stylesheet
    stylesheet = THEMES[theme_name]
    app.setStyleSheet(stylesheet)
    
    # Update current theme
    _current_theme = theme_name
    
    logger.info(f"Theme '{theme_name}' applied successfully")