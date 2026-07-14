import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from ...resources import icon_path, set_app_user_model_id
from .fonts import UI_FAMILIES
from .main_window import MainWindow
from .style import STYLESHEET


def launch(output_dir: Path | None = None) -> int:
  """Create the QApplication, show the window, run the event loop."""
  # Detach the taskbar button from python.exe so it uses our icon.
  set_app_user_model_id()
  app = QApplication.instance() or QApplication(sys.argv)
  # Fusion renders our dark stylesheet identically on Win/macOS/Linux;
  # native styles partly ignore QSS (notably on tabs).
  app.setStyle("Fusion")
  # Names give QSettings (recent files) a stable location.
  app.setOrganizationName("Unsealed")
  app.setApplicationName("Unsealed Reader")
  app.setWindowIcon(QIcon(str(icon_path())))

  base_font = QFont()
  base_font.setFamilies(UI_FAMILIES)
  base_font.setPointSize(10)
  app.setFont(base_font)
  app.setStyleSheet(STYLESHEET)

  window = MainWindow(output_dir)
  window.show()
  return app.exec()
