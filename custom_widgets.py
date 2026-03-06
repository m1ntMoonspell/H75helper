from PySide6.QtWidgets import QCheckBox, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, Property, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._position = 0
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setDuration(200)
        self.stateChanged.connect(self.setup_animation)
        
    @Property(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(1)
            self.animation.start()
        else:
            self.animation.setEndValue(0)
            self.animation.start()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        p.setPen(Qt.NoPen)
        # Assuming unchecked = NA (Blue), checked = CN (Red)
        if self.isChecked():
            p.setBrush(QBrush(QColor("#ED4245"))) # Red for CN
        else:
            p.setBrush(QBrush(QColor("#5865F2"))) # Blue for NA
            
        p.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
        
        thumb_color = QColor("#ffffff")
        p.setBrush(QBrush(thumb_color))
        
        thumb_rect = QRect(
            2 + int(self._position * (self.width() - self.height())),
            2,
            self.height() - 4,
            self.height() - 4
        )
        p.drawEllipse(thumb_rect)
        p.end()

class InAppToast(QLabel):
    def __init__(self, text, parent=None, duration=2000):
        super().__init__(text, parent)
        self.duration = duration
        self.setStyleSheet("""
            QLabel {
                background-color: #57F287;
                color: #ffffff;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.adjustSize()
        self.hide()
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)
        
    def show_toast(self):
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 80
            self.move(x, y)
        self.show()
        self.raise_()
        
        # Disconnect old finished signals to prevent multiple hides
        try:
            self.anim.finished.disconnect()
        except RuntimeError:
            pass
            
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.hide_timer.start(self.duration)
        
    def fade_out(self):
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()


def show_error_toast(widget, command):
    """Shared fallback: copy command to clipboard and show a red error toast on the main window.
    
    Walks up the parent chain from `widget` to find either a QMainWindow or the
    top-level window, then attaches a red InAppToast to it so the toast survives
    dialog closures.
    
    Args:
        widget: The QWidget initiating the fallback (e.g. a QDialog).
        command: The command string to copy to the clipboard.
    """
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QMainWindow

    cb = QGuiApplication.clipboard()
    cb.setText(command)

    # Walk up to find the real persistent main window
    main_win = None
    walker = widget.parent() if widget else None
    while walker:
        if isinstance(walker, QMainWindow):
            main_win = walker
            break
        walker = walker.parent()

    # Fallback: use widget.window() if no QMainWindow found (e.g. standalone)
    if not main_win and widget:
        main_win = widget.window()

    if main_win:
        toast = InAppToast("未找到目标控制台，已复制到剪贴板！", main_win, 2500)
        toast.setStyleSheet("""
            QLabel {
                background-color: #ED4245;
                color: #ffffff;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        toast.show_toast()
        main_win._fallback_toast = toast
