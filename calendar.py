import sys
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLineEdit,
                               QHBoxLayout,QLabel,QPushButton)
from PySide6.QtGui import QGuiApplication
import datetime

class Calendar(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.titleLayout = QHBoxLayout()
        self.name_edit = QLineEdit(self,placeholderText="Name")
        self.time_label = QLabel(self)
        self.confirm_button = QPushButton("确认")
        self.confirm_button.connect()
        today = datetime.date.today()
        self.time_label.setText(f"-{today}-日报")
        self.titleLayout.addWidget(self.name_edit)
        self.titleLayout.addWidget(self.time_label)
        self.UILayout = QVBoxLayout()
        self.setLayout(self.UILayout)
        self.contentLayout = QVBoxLayout()       
        self.currentLineEdit = QLineEdit(self)
        self.contentLayout.addWidget(self.currentLineEdit)
        self.UILayout.addLayout(self.titleLayout)
        self.UILayout.addLayout(self.contentLayout)       
        self.currentLineEdit.returnPressed.connect(self.addNewLineEdit)
        
    def addNewLineEdit(self):
        newLineEdit = QLineEdit(self)
        self.contentLayout.addWidget(newLineEdit) 
        newLineEdit.returnPressed.connect(self.addNewLineEdit)
        newLineEdit.setFocus()
        self.currentLineEdit = newLineEdit

    def toclip(self,text):
        cb = QGuiApplication.clipboard()
        cb.setText(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Calendar()
    ex.show()
    sys.exit(app.exec())
