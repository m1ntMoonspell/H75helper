from PySide6.QtWidgets import (QLineEdit, QDialog, QPushButton,
                               QApplication, QVBoxLayout,
                               QHBoxLayout, QLabel)
from PySide6.QtGui import QGuiApplication
from custom_widgets import ToggleSwitch 

class TransLink(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Enter text here...")
        self.button = QPushButton("To Link")
        self.button.setObjectName("primaryButton")
        self.button.clicked.connect(self.get_text)
        self.button.clicked.connect(self.edit.clear)
        
        self.switch_label = QLabel("Switch:")
        self.switch = QLabel("Not Selected")
        self.switch.setStyleSheet("color: #a0a0a0;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setWindowTitle("Identify 2 Link")
        
        hl = QHBoxLayout()
        h2 = QHBoxLayout()
        
        self.shift_label = QLabel("Client")
        self.shift_label.setStyleSheet("color: #57F287; font-weight: bold;")
        self.shift_toggle = ToggleSwitch()
        self.shift_toggle.stateChanged.connect(self.on_switch_toggled)
        
        h2.addWidget(self.shift_label)
        h2.addWidget(self.shift_toggle)
        h2.addStretch()
        
        self.status_label = QLabel("Status:")
        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #a0a0a0;")
        hl.addWidget(self.status_label)
        hl.addWidget(self.status)
        hl.addStretch()
        
        layout.addLayout(h2)
        layout.addLayout(hl)
        self.switchText = " "

    def get_text(self):
        text = self.edit.text()
        try:
            link = f"https://unisdk.nie.netease.com/{self.switchText}/h75/identify-detail?identify={text}"
        except ValueError:
            self.status.setText("Failed")
            self.status.setStyleSheet("color: #ED4245; font-weight: bold;")
        else:
            cb = QGuiApplication.clipboard()
            cb.setText(link)
            self.status.setText("Success")
            self.status.setStyleSheet("color: #57F287; font-weight: bold;")

    def on_switch_toggled(self, state):
        if not state:
            self.shift_label.setText("Client")
            self.shift_label.setStyleSheet("color: #57F287; font-weight: bold;")
            self.switchText = "appdump"
        else:
            self.shift_label.setText("Server")
            self.shift_label.setStyleSheet("color: #5865F2; font-weight: bold;")
            self.switchText = "serverdump"

    def showEvent(self, event):
        super().showEvent(event)
        p = self.parentWidget()
        if p and p.window():
            self.move(p.window().geometry().center() - self.rect().center())

if __name__ == "__main__":
    app = QApplication()
    dia = TransLink()
    dia.show()
    app.exec()
