from PySide6.QtWidgets import (QPushButton, QApplication,
                               QDialog, QVBoxLayout, QScrollArea, QWidget)
from input_dialog import InputDia
from auto_typer import send_command_to_hwnd, find_form_hwnd
from custom_widgets import show_error_toast


class GMList(QDialog):
    def __init__(self, list_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick GM")
        self.setMinimumWidth(300)
        self.setMaximumHeight(500)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        for k, v in list_dict.items():
            button = QPushButton(f"{k}")
            if k in ["重置宠物CD", "觉醒单个宠物", "Teleport"]:
                button.setObjectName("primaryButton")
                button.clicked.connect(lambda checked, t=v, title=k: self.show_input(t, title))
            else:
                button.clicked.connect(lambda checked, t=v: self.toclip(t))
                
            layout.addWidget(button)
            
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def toclip(self, text):
        hwnd = find_form_hwnd(self)
        success = send_command_to_hwnd(hwnd, text) if hwnd else False
        
        if not success:
            show_error_toast(self, text)

    def show_input(self, text, keys):
        inDia = InputDia(text, keys, self)
        if inDia.exec():
            inDia.show()

    def showEvent(self, event):
        super().showEvent(event)
        p = self.parentWidget()
        if p and p.window():
            self.move(p.window().geometry().center() - self.rect().center())

if __name__ == "__main__":
    app = QApplication()
    gm_list = GMList(item_dict={})
    gm_list.show()
    app.exec()
