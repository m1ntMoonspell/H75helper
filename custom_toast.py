from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, QPoint

class ToastNotification(QWidget):
    def __init__(self, title, message, click_callback=None):
        super().__init__(None) # Global floating window
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.click_callback = click_callback
        
        self.setFixedSize(320, 100)
        self.setStyleSheet("""
            ToastNotification {
                background-color: #2b2b36;
                border: 2px solid #5865F2;
                border-radius: 10px;
            }
            QLabel#title {
                color: #ffffff;
                font-weight: bold;
                font-size: 16px;
                background: transparent;
                border: none;
            }
            QLabel#message {
                color: #e0e0e0;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("title")
        self.message_label = QLabel(message)
        self.message_label.setObjectName("message")
        self.message_label.setWordWrap(True)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.message_label)
        layout.addStretch()
        
        # Calculate bottom right slide-up positions
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.end_pos = screen_geo.bottomRight() - QPoint(self.width(), self.height()) - QPoint(20, 20)
        self.start_pos = self.end_pos + QPoint(0, self.height() + 40)
        
        self.setGeometry(QRect(self.start_pos, self.size()))
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(600)
        self.animation.setStartValue(self.start_pos)
        self.animation.setEndValue(self.end_pos)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.hide_toast)
        
    def show_toast(self):
        self.show()
        self.animation.start()
        self.close_timer.start(10000) # Live for 10 seconds
        
    def hide_toast(self):
        self.animation.setStartValue(self.end_pos)
        self.animation.setEndValue(self.start_pos)
        self.animation.setDirection(QPropertyAnimation.Forward)
        self.animation.finished.connect(self.close)
        self.animation.start()
        
    def mousePressEvent(self, event):
        if self.click_callback:
            self.click_callback()
        self.hide_toast()
