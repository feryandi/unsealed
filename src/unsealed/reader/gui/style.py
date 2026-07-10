"""Central theme for the reader GUI.

Dark, IDE-flavoured (VSCode/Chrome lineage) with a wax-amber accent that
sets it apart from the usual editor blue. All design tokens live here so
the look can be tuned in one place. Pair it with the Fusion style for
consistent rendering across Windows, macOS, and Linux.
"""

from .fonts import MONO_STACK, UI_STACK

# -- design tokens ------------------------------------------------
BG = "#15171C"  # window / editor surface
TAB_STRIP = "#101216"  # strip behind the tabs
TAB_INACTIVE = "#1B1E24"
TAB_HOVER = "#22262E"
BORDER = "#2C313A"
TEXT = "#E6E8EC"
MUTED = "#868D99"
FAINT = "#6B7280"
ACCENT = "#E0A94F"  # wax-amber
ACCENT_HOVER = "#EDB964"
ACCENT_PRESS = "#C9963F"

STYLESHEET = f"""
QMainWindow, QWidget#welcomeTab, QWidget#contentTab {{
  background-color: {BG};
}}
QWidget {{
  color: {TEXT};
  font-family: {UI_STACK};
  font-size: 13px;
}}

/* Tab strip -------------------------------------------------- */
QTabWidget::pane {{ border: none; background: {BG}; }}
QTabBar {{ background: {TAB_STRIP}; qproperty-drawBase: 0; }}
QTabBar::tab {{
  background: {TAB_INACTIVE};
  color: {MUTED};
  min-width: 150px;
  padding: 9px 10px 9px 14px;
  border: none;
  border-right: 1px solid {TAB_STRIP};
  border-top: 2px solid transparent;
}}
QTabBar::tab:hover {{ background: {TAB_HOVER}; color: {TEXT}; }}
QTabBar::tab:selected {{
  background: {BG};
  color: {TEXT};
  border-top: 2px solid {ACCENT};
}}

/* Per-tab close (x) and inline add (+) buttons --------------- */
QToolButton#tabCloseButton {{
  color: {MUTED};
  background: transparent;
  border: none;
  border-radius: 3px;
  font-size: 15px;
}}
QToolButton#tabCloseButton:hover {{ color: {TEXT}; background: {TAB_HOVER}; }}
QToolButton#addTabButton {{
  color: {MUTED};
  background: transparent;
  border: none;
  border-radius: 4px;
  font-size: 18px;
}}
QToolButton#addTabButton:hover {{ color: {TEXT}; background: {TAB_HOVER}; }}

/* Welcome screen --------------------------------------------- */
QWidget#welcomeColumn {{
  border: 1px dashed transparent;
  border-radius: 10px;
}}
QWidget#welcomeColumn[dragActive="true"] {{
  border: 1px dashed {ACCENT};
}}
QLabel#subtitle {{ color: {MUTED}; font-size: 14px; }}
QPushButton#openButton {{
  background: {ACCENT};
  color: {BG};
  font-weight: bold;
  border: none;
  border-radius: 6px;
  padding: 11px 22px;
}}
QPushButton#openButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#openButton:pressed {{ background: {ACCENT_PRESS}; }}
QLabel#dropHint {{ color: {FAINT}; font-size: 12px; }}

/* Recent list panel ------------------------------------------ */
QFrame#recentBox {{
  background: {TAB_INACTIVE};
  border: 1px solid {BORDER};
  border-radius: 8px;
}}
QLabel#recentEyebrow {{ color: {MUTED}; }}
QLabel#recentEmpty {{ color: {FAINT}; font-size: 13px; }}
QFrame#recentRow {{ background: transparent; border-radius: 6px; }}
QFrame#recentRow:hover {{ background: {TAB_HOVER}; }}
QLabel#recentName {{ color: {TEXT}; font-size: 13px; }}
QLabel#recentPath {{ color: {FAINT}; font-size: 11px; font-family: {MONO_STACK}; }}

/* Content placeholder ---------------------------------------- */
QLabel#contentPlaceholder {{ color: {MUTED}; font-size: 13px; }}
QLabel#errorHeading {{ color: {ACCENT}; font-size: 14px; font-weight: bold; }}

/* Asset tree ------------------------------------------------- */
QTreeView#assetTree {{
  background: {BG};
  border: none;
  outline: none;
  font-family: {MONO_STACK};
  font-size: 12px;
}}
QTreeView#assetTree::item {{ padding: 3px 2px; }}
QTreeView#assetTree::item:selected {{ background: {TAB_HOVER}; color: {TEXT}; }}
QHeaderView::section {{
  background: {TAB_STRIP};
  color: {MUTED};
  border: none;
  border-right: 1px solid {BORDER};
  padding: 5px 8px;
}}
QPlainTextEdit#errorTrace {{
  background: {TAB_STRIP};
  border: none;
  color: {TEXT};
  font-family: {MONO_STACK};
  font-size: 12px;
  padding: 6px;
}}

/* Properties view -------------------------------------------- */
QWidget#propertiesView {{ background: {BG}; }}
QLabel#propTitle {{ color: {TEXT}; font-size: 16px; font-weight: bold; }}
QLabel#propSection {{ color: {ACCENT}; font-size: 11px; font-weight: bold; }}
QLabel#propKey {{ color: {MUTED}; font-size: 13px; }}
QLabel#propValue {{ color: {TEXT}; font-size: 13px; font-family: {MONO_STACK}; }}

/* Map view --------------------------------------------------- */
QWidget#mapView {{ background: {BG}; }}
QListWidget#mapNav {{
  background: {TAB_STRIP};
  border: none;
  border-right: 1px solid {BORDER};
  outline: none;
  padding-top: 8px;
}}
QListWidget#mapNav::item {{ color: {MUTED}; padding: 9px 16px; }}
QListWidget#mapNav::item:hover {{ color: {TEXT}; }}
QListWidget#mapNav::item:selected {{
  background: {BG};
  color: {TEXT};
  border-left: 2px solid {ACCENT};
}}
QTableView#mapTable {{
  background: {BG};
  border: none;
  outline: none;
  font-family: {MONO_STACK};
  font-size: 12px;
}}
QTableView#mapTable::item {{ padding: 3px 6px; }}
QTableView#mapTable::item:selected {{ background: {TAB_HOVER}; color: {TEXT}; }}
QLabel#mapDetailName {{
  color: {TEXT};
  font-size: 13px;
  font-weight: bold;
  font-family: {MONO_STACK};
}}
QPushButton#mapOpenButton {{
  color: {TEXT};
  background: {TAB_INACTIVE};
  border: 1px solid {BORDER};
  border-radius: 5px;
  padding: 6px 14px;
}}
QPushButton#mapOpenButton:hover {{ border-color: {ACCENT}; }}
QPushButton#mapOpenButton:disabled {{ color: {FAINT}; border-color: {TAB_INACTIVE}; }}

/* Image preview view ----------------------------------------- */
QWidget#imageView {{ background: {BG}; }}
QWidget#imageCanvas {{ background: {TAB_STRIP}; }}
QScrollArea#imageProps {{
  background: {BG};
  border: none;
  border-left: 1px solid {BORDER};
}}

/* EDT decrypt-and-convert view ------------------------------- */
QWidget#edtView {{ background: {BG}; }}
QLabel#edtBanner {{
  background: {TAB_STRIP};
  color: {ACCENT};
  border-bottom: 1px solid {BORDER};
  padding: 6px 12px;
  font-size: 12px;
}}
QPlainTextEdit#edtText {{
  background: {BG};
  border: none;
  color: {TEXT};
  font-family: {MONO_STACK};
  font-size: 12px;
  padding: 6px 10px;
}}

/* Schema table view (.dat / .scr / .tsv) --------------------- */
QWidget#tableView {{ background: {BG}; }}
QWidget#tableBar {{
  background: {TAB_STRIP};
  border-bottom: 1px solid {BORDER};
}}
QLabel#tableBarLabel {{ color: {MUTED}; font-size: 12px; }}
QLabel#tableInfo {{ color: {MUTED}; font-size: 12px; font-family: {MONO_STACK}; }}
QCheckBox#tableShowAll {{ color: {MUTED}; font-size: 12px; }}
QComboBox#schemaCombo {{
  background: {TAB_INACTIVE};
  color: {TEXT};
  border: 1px solid {BORDER};
  border-radius: 5px;
  padding: 4px 8px;
}}
QComboBox#schemaCombo:focus {{ border-color: {ACCENT}; }}
QComboBox#schemaCombo QAbstractItemView {{
  background: {TAB_INACTIVE};
  color: {TEXT};
  selection-background-color: {TAB_HOVER};
  border: 1px solid {BORDER};
}}
QTableView#dataTable {{
  background: {BG};
  alternate-background-color: {TAB_INACTIVE};
  border: none;
  outline: none;
  gridline-color: {BORDER};
  font-family: {MONO_STACK};
  font-size: 12px;
}}
QTableView#dataTable::item {{ padding: 2px 6px; }}
QTableView#dataTable::item:selected {{ background: {TAB_HOVER}; color: {TEXT}; }}

/* MEN / SPR tree views --------------------------------------- */
QWidget#menView, QWidget#sprView {{ background: {BG}; }}

/* SPAK / MDT archive browser --------------------------------- */
QWidget#spakView {{ background: {BG}; }}
QLabel#spakLoadingTitle {{ color: {TEXT}; font-size: 16px; font-weight: bold; }}
QLabel#spakStatus {{ color: {MUTED}; font-size: 12px; }}
QLabel#spakCount {{ color: {MUTED}; font-size: 12px; }}
QLineEdit#spakSearch {{
  background: {TAB_INACTIVE};
  color: {TEXT};
  border: 1px solid {BORDER};
  border-radius: 5px;
  padding: 5px 8px;
  max-width: 280px;
}}
QLineEdit#spakSearch:focus {{ border-color: {ACCENT}; }}
QTableView#spakTable {{
  background: {BG};
  border: none;
  outline: none;
  font-family: {MONO_STACK};
  font-size: 12px;
}}
QTableView#spakTable::item {{ padding: 4px 6px; }}
QTableView#spakTable::item:selected {{ background: {TAB_HOVER}; color: {TEXT}; }}
QLabel#keyHeading {{ color: {ACCENT}; font-size: 16px; font-weight: bold; }}
QLabel#keyBody {{ color: {TEXT}; font-size: 13px; }}
QLabel#keyGuide {{ color: {MUTED}; font-size: 12px; }}
QLabel#keyStatus {{ color: {ACCENT}; font-size: 12px; }}
"""
