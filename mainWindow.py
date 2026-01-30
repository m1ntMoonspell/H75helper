from PySide6.QtWidgets import (QMainWindow,QApplication,QVBoxLayout,QWidget,
                               QTabWidget,QMessageBox,QDialog,QLabel)
from trace_helper_main_window import TraceDia
from gm_user_interface import Form
from calendar import Calendar

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(350,200)
        self.setWindowTitle("H75 Helper")
        self.creat_subwidgets()

    def creat_subwidgets(self):
        menuBar = self.menuBar()
        helpMenu = menuBar.addMenu("其他")
        luckyNode = helpMenu.addAction("How's the luck today")
        abotNode = helpMenu.addAction("About")
        abotNode.triggered.connect(self.aboutclicked)
        tab = QTabWidget(parent=self)
        tab.addTab(self.embed_into_vlayout(Form(self)),"GM Helper")
        tab.addTab(self.embed_into_vlayout(TraceDia(self)),"Trace Helper")
        tab.addTab(self.embed_into_vlayout(Calendar(self)),"Calendar Helper")
        self.setCentralWidget(tab)

    def embed_into_vlayout(self,w,margin=5):
        result = QWidget()
        layout = QVBoxLayout(result)
        layout.addWidget(w)
        layout.setContentsMargins(margin,margin,margin,margin)
        return result
    
    def aboutclicked(self):
        popDia = QDialog(self)
        popDia.setWindowTitle("About")
        label = QLabel("All Rights Reserved" \
        "<a href='https://github.com/m1ntMoonspell?tab=repositories'>@m1nt</a>")
        label.setOpenExternalLinks(True)
        layout = QVBoxLayout()
        layout.addWidget(label)
        popDia.setLayout(layout)
        if popDia.exec():
            popDia.show()



if __name__ == "__main__":
    app = QApplication()
    window = MyWindow()
    window.show()
    app.exec()


