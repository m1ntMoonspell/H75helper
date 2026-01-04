from mainWindow import MyWindow
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication()
    window = MyWindow()
    window.show()
    app.exec()
