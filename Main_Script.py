import os
import sys

# Keep Qt's Windows DPI handling predictable on high-resolution displays.
# These environment variables must be set before importing the rest of Qt.
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

from PyQt5 import QtWidgets, QtCore, QtGui

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts, True)

try:
    dpi_policy = QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(dpi_policy)
except AttributeError:
    pass

import ICONS_rc
from Logic import Logic


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("Kevin Somenzi")
    app.setApplicationName("ISatQuLLoS")
    app.setStyle("Fusion")
    app.setFont(QtGui.QFont("Segoe UI", 9))

    logic = Logic()
    logic.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
