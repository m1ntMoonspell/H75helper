from PySide6.QtWidgets import (QPushButton, QApplication,
                               QDialog, QVBoxLayout, QScrollArea, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

class Popups(QDialog):
    def __init__(self, item_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("搜索结果")
        self.setMinimumWidth(300)
        self.setMaximumHeight(400)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        from PySide6.QtWidgets import QHBoxLayout, QLineEdit
        for k, v in item_dict.items():
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            
            # Button for the item
            button = QPushButton(f"{k} - {v}")
            # Quantity Input
            qty_edit = QLineEdit()
            qty_edit.setPlaceholderText("数量 (默认: 1)")
            qty_edit.setFixedWidth(80)
            
            # Use default 1 if empty
            button.clicked.connect(lambda checked, v_id=v, q=qty_edit: self.toclip(f"#add_equip {v_id} {q.text().strip() or '1'} 0 True"))
            
            row_layout.addWidget(button, stretch=1)
            row_layout.addWidget(qty_edit, stretch=0)
            layout.addLayout(row_layout)
            
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
                
        self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        p = self.parentWidget()
        if p and p.window():
            self.move(p.window().geometry().center() - self.rect().center())
if __name__ == "__main__":
    app = QApplication()
    popup = Popups(item_dict={})
    popup.show()
    app.exec()
