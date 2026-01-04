from PySide6.QtWidgets import (QPushButton,QApplication,
                               QDialog,QVBoxLayout)
from PySide6.QtGui import QGuiApplication

class Popups(QDialog):
    def __init__(self,item_dict,parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索结果")
        layout = QVBoxLayout(self)
        for k,v in item_dict.items():
            button = QPushButton(f"{k} - {v}")
            text = f"#add_equip {v} 1 0 True"
            button.clicked.connect(lambda checked,
                                   t=text:self.toclip(t))
            button.clicked.connect(self.reject)
            layout.addWidget(button)
        self.setLayout(layout)

    def toclip(self,text):
        cb = QGuiApplication.clipboard()
        cb.setText(text)

if __name__ == "__main__":
    app = QApplication()
    popup = Popups(item_dict={})
    popup.show()
    app.exec()
