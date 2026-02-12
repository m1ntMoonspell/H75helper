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
        self.switch_label = QLabel("Switch:")
        self.switch = QLabel(" ")
        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.setWindowTitle("Identify 2 Link")
        hl = QHBoxLayout()
        h2 = QHBoxLayout()
        h3 = QHBoxLayout()
        h3.addWidget(self.switch_label)
        h3.addWidget(self.switch)
        h3.addStretch()
        self.app_button = QPushButton("Client")
        self.app_button.clicked.connect(self.client_switch)
        self.server_button = QPushButton("Server")
        self.server_button.clicked.connect(self.server_switch) 
        h2.addWidget(self.app_button)
        h2.addWidget(self.server_button)
        self.status_label = QLabel("Status:")
        self.status = QLabel("Null")
        hl.addWidget(self.status_label)
        hl.addWidget(self.status)
        hl.addStretch()
        layout.addLayout(h2)
        layout.addLayout(hl)
        layout.addLayout(h3)
        self.switchText = " "

    def get_text(self):
        text = self.edit.text()
        try:
            link = f"https://unisdk.nie.netease.com/{self.switchText}/h75/identify-detail?identify={text}&time=last_7_day"
        except ValueError:
            self.status.setText("<p style='color:red;'>Failed</p>")
        else:
            cb = QGuiApplication.clipboard()
            cb.setText(link)
            self.status.setText("<p style='color:green;'>Success</p>")

    def client_switch(self):
        self.switch.setText("<p style='color:green;'>Client</p>")
        self.switchText = "appdump"
    def server_switch(self):
        self.switch.setText("<p style='color:blue;'>Server</p>")
        self.switchText = "serverdump"


if __name__ == "__main__":
    app = QApplication()
    dia = TransLink()
    dia.show()
    app.exec()