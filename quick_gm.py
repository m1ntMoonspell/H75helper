from PySide6.QtWidgets import (QPushButton,QApplication,QToolTip,
                               QDialog,QVBoxLayout,QLineEdit,)
from PySide6.QtGui import QGuiApplication
from input_dialog import InputDia

class GMList(QDialog):
    def __init__(self,list_dict,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick GM")
        layout = QVBoxLayout(self)
        for k,v in list_dict.items():
            if k == "重置宠物CD" or k == "觉醒单个宠物" or k == "Teleport":
                button = QPushButton(f"{k}")
                button.clicked.connect(lambda checked,
                                       t=v,title=k:self.show_input(t,title))
            else:
                button = QPushButton(f"{k}")
                button.clicked.connect(lambda checked,
                                    t=v:self.toclip(t))
            layout.addWidget(button)
        self.setLayout(layout)

    def toclip(self,text):
        cb = QGuiApplication.clipboard()
        cb.setText(text)

    def show_input(self,text,keys):
        inDia = InputDia(text,keys)
        if inDia.exec():
            inDia.show()


if __name__ == "__main__":
    app = QApplication()
    list = GMList(item_dict={})
    list.show()
    app.exec()