from PySide6.QtWidgets import (QMainWindow,QApplication,QVBoxLayout,QWidget,Q)
from trace_helper_main_window import TraceDia
from gm_user_interface import Form

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(300,200)
        self.setWindowTitle("H75 Helper")
        self.creat_subwidgets()

    def creat_subwidgets(self):
        menuBar = self.menuBar()
        helpMenu = menuBar.addMenu("其他")
        luckyNode = helpMenu.addAction("How's the luck today")
        central = QWidget(self)
        self.setCentralWidget(central)

if __name__ == "__main__":
    app = QApplication()
    window = MyWindow()
    window.show()
    app.exec()


