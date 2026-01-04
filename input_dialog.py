from PySide6.QtWidgets import (QPushButton,QToolTip,
                               QDialog,QVBoxLayout,QLineEdit,)
from PySide6.QtGui import QGuiApplication

class InputDia(QDialog):
    def __init__(self,text,title,parent=None):
        super().__init__(parent)
        self.creat_subwidgets(text,title)
        self.setWindowTitle("Input Dia")

    def creat_subwidgets(self,text,title):
        self.edit = QLineEdit(self,placeholderText="Enter text here")
        self.button = QPushButton("Confirm")
        if title == "重置宠物CD" or title == "觉醒单个宠物":
            self.edit.setToolTip("  5 - 诺亚\n  6 - 爱丽丝\n  9 - 幻影\n11 - 游骑兵\n" \
            "13 - 冰龙\n15 - 竹宝\n18 - 八筒\n20 - 金鳞")
        self.button.clicked.connect(lambda checked,
                                    t=text:self.toclip(t,title=title))
        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)
        self.button.clicked.connect(self.reject)


    def toclip(self,text,title):
        cb = QGuiApplication.clipboard()
        if title == "重置宠物CD":
            cb.setText(f"{text}{self.edit.text()}")
        else:
            cb.setText(f"{text}({self.edit.text()})")