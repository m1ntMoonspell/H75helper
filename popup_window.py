from PySide6.QtWidgets import (QPushButton, QApplication,
                               QDialog, QVBoxLayout, QScrollArea, QWidget,
                               QHBoxLayout, QLineEdit)
from PySide6.QtCore import Qt

from auto_typer import send_command_to_hwnd, find_form_hwnd
from custom_widgets import show_error_toast


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
        
        for k, v in item_dict.items():
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            
            button = QPushButton(f"{k} - {v}")
            qty_edit = QLineEdit()
            qty_edit.setPlaceholderText("数量 (默认: 1)")
            qty_edit.setFixedWidth(80)
            
            button.clicked.connect(
                lambda checked, v_id=v, q=qty_edit:
                    self.toclip(f"#add_equip {v_id} {q.text().strip() or '1'} 0 True")
            )
            
            row_layout.addWidget(button, stretch=1)
            row_layout.addWidget(qty_edit, stretch=0)
            layout.addLayout(row_layout)
            
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def toclip(self, text):
        hwnd = find_form_hwnd(self)
        success = send_command_to_hwnd(hwnd, text) if hwnd else False
        
        if not success:
            show_error_toast(self, text)
                
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
