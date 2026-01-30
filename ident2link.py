from PySide6.QtWidgets import (QLineEdit,QDialog,QPushButton,
                               QApplication,QVBoxLayout,
                               QHBoxLayout,QLabel)
from PySide6.QtGui import QGuiApplication 

class TransLink(QDialog):
    def __init__(self):
        super().__init__()
        self.edit = QLineEdit(placeholderText="Enter text here")
        self.button = QPushButton("To Link")
        self.button.clicked.connect(self.get_text)
        self.button.clicked.connect(self.edit.clear)
        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setWindowTitle("Identify 2 Link")
        hl = QHBoxLayout()
        self.status_label = QLabel("Status:")
        self.status = QLabel("Null")
        hl.addWidget(self.status_label)
        hl.addWidget(self.status)
        hl.addStretch()
        layout.addLayout(hl)

    def get_text(self):
        text = self.edit.text()
        try:
            link = f"https://unisdk.nie.netease.com/serverdump/h75/identify-detail?identify={text}&time=last_7_day"
        except ValueError:
            self.status.setText("<p style='color:red;'>Failed</p>")
        else:
            cb = QGuiApplication.clipboard()
            cb.setText(link)
            self.status.setText("<p style='color:green;'>Success</p>")

if __name__ == "__main__":
    app = QApplication()
    dia = TransLink()
    dia.show()
    app.exec()