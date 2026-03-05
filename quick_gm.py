from PySide6.QtWidgets import (QPushButton, QApplication, QToolTip,
                               QDialog, QVBoxLayout, QScrollArea, QWidget)
from PySide6.QtGui import QGuiApplication
from input_dialog import InputDia

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
        from auto_typer import send_command_to_hwnd
        from custom_widgets import InAppToast
        
        # Get the selected HWND from the parent Form's console dropdown
        p = self.parentWidget()
        hwnd = p.get_selected_hwnd() if p and hasattr(p, 'get_selected_hwnd') else 0
        success = send_command_to_hwnd(hwnd, text) if hwnd else False
        
        if not success:
            cb = QGuiApplication.clipboard()
            cb.setText(text)
            
            p = self.parentWidget()
            if p and p.window():
                win = p.window()
                toast = InAppToast("未找到目标控制台，已复制到剪贴板！", win, 2500)
                toast.setStyleSheet("""
                    QLabel {
                        background-color: #ED4245; 
                        color: #ffffff;
                        border-radius: 8px;
                        padding: 10px 20px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                toast.show_toast()
                win._fallback_toast = toast

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
