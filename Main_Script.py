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

INTRO_DISPLAY_MS = 2500
INTRO_FADE_MS = 1000


#Here we create the intro/title pop-up screen that shows at startup.
def _build_intro_pixmap():
    size = QtCore.QSize(760, 430)
    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtGui.QColor("#0b1522"))

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHints(
        QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform
    )

    background = QtGui.QPixmap(":/IMAGES/Satellite Network 1.jpg")
    if not background.isNull():
        scaled = background.scaled(
            size,
            QtCore.Qt.KeepAspectRatioByExpanding,
            QtCore.Qt.SmoothTransformation,
        )
        x = int((size.width() - scaled.width()) * 0.30)
        y = int((size.height() - scaled.height()) * 0.50)
        painter.drawPixmap(x, y, scaled)

    painter.fillRect(pixmap.rect(), QtGui.QColor(9, 20, 35, 165))

    icon = QtGui.QPixmap(":/ICONS/signal-satellite.png")
    if not icon.isNull():
        icon = icon.scaled(70, 70, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        painter.drawPixmap(int((size.width() - icon.width()) / 2), 86, icon)

    title_font = QtGui.QFont("Segoe UI", 34)
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.setPen(QtGui.QColor("#f8fbff"))
    painter.drawText(QtCore.QRect(0, 170, size.width(), 58), QtCore.Qt.AlignCenter, "ISatQuLLoS")

    subtitle_font = QtGui.QFont("Segoe UI", 12)
    subtitle_font.setWeight(QtGui.QFont.Medium)
    painter.setFont(subtitle_font)
    painter.setPen(QtGui.QColor("#d8e6f4"))
    painter.drawText(
        QtCore.QRect(0, 230, size.width(), 32),
        QtCore.Qt.AlignCenter,
        "Inter-Satellite Quantum Link Loss Simulations",
    )

    painter.setPen(QtGui.QColor("#9fb3c8"))
    painter.drawText(
        QtCore.QRect(0, 330, size.width(), 28),
        QtCore.Qt.AlignCenter,
        "Loading interface...",
    )
    painter.end()
    return pixmap


def _show_intro_splash(app):
    splash = QtWidgets.QSplashScreen(_build_intro_pixmap(), QtCore.Qt.WindowStaysOnTopHint)
    splash.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
    splash.setWindowOpacity(1.0)
    splash.show()
    app.processEvents()
    return splash


def _fade_intro_into_window(window, splash):
    window.setWindowOpacity(0.0)
    window.showMaximized()

    fade_out = QtCore.QPropertyAnimation(splash, b"windowOpacity", window)
    fade_out.setDuration(INTRO_FADE_MS)
    fade_out.setStartValue(1.0)
    fade_out.setEndValue(0.0)
    fade_out.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    fade_in = QtCore.QPropertyAnimation(window, b"windowOpacity", window)
    fade_in.setDuration(INTRO_FADE_MS)
    fade_in.setStartValue(0.0)
    fade_in.setEndValue(1.0)
    fade_in.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    intro_animation = QtCore.QParallelAnimationGroup(window)
    intro_animation.addAnimation(fade_out)
    intro_animation.addAnimation(fade_in)

    def finish_intro():
        splash.finish(window)
        splash.deleteLater()
        window._intro_splash = None
        window._intro_animation = None

    intro_animation.finished.connect(finish_intro)
    window._intro_splash = splash
    window._intro_animation = intro_animation
    QtCore.QTimer.singleShot(INTRO_DISPLAY_MS, intro_animation.start)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("Kevin Somenzi")
    app.setApplicationName("ISatQuLLoS")
    app.setStyle("Fusion")
    app.setFont(QtGui.QFont("Segoe UI", 9))

    splash = _show_intro_splash(app)
    logic = Logic()
    _fade_intro_into_window(logic, splash)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
