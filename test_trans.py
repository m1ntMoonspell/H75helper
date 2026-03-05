import sys
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

class TestDrop(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.resize(300, 300)
        
        l = QVBoxLayout(self)
        self.label = QLabel("Drop here")
        self.label.setStyleSheet("background-color: rgba(255, 0, 0, 100); font-size: 24px;")
        l.addWidget(self.label)
        
    def dragEnterEvent(self, e):
        e.accept()
        self.label.setText("Dragging!")
        
    def dropEvent(self, e):
        self.label.setText("Dropped!")

app = QApplication(sys.argv)
w = TestDrop()
w.show()
app.exec()
