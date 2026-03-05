from PySide6.QtWidgets import (QLineEdit, QDialog, QPushButton,
                               QApplication, QVBoxLayout,
                               QHBoxLayout, QLabel)
from PySide6.QtGui import QGuiApplication 

class SliceDia(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Enter text here...")
        self.button = QPushButton("Slice!")
        self.button.setObjectName("primaryButton")
        self.button.clicked.connect(self.get_text)
        self.button.clicked.connect(self.edit.clear)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setWindowTitle("Link Slicer")
        
        hl = QHBoxLayout()
        self.status_label = QLabel("Status:")
        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #a0a0a0;")
        hl.addWidget(self.status_label)
        hl.addWidget(self.status)
        hl.addStretch()
        layout.addLayout(hl)

    def get_text(self):
        text = self.edit.text()
        try:
            str1, number, title, link = text.split(" ")
        except ValueError:
            self.status.setText("Failed")
            self.status.setStyleSheet("color: #ED4245; font-weight: bold;")
        else:
            cb = QGuiApplication.clipboard()
            cb.setText(link)
            self.status.setText("Success")
            self.status.setStyleSheet("color: #57F287; font-weight: bold;")

    def showEvent(self, event):
        super().showEvent(event)
        p = self.parentWidget()
        if p and p.window():
            self.move(p.window().geometry().center() - self.rect().center())

if __name__ == "__main__":
    app = QApplication()
    dia = SliceDia()
    dia.show()
    app.exec()