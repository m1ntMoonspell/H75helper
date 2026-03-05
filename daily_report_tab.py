import sys
from PySide6.QtWidgets import (QApplication, QVBoxLayout, QLineEdit, QHBoxLayout, 
                               QLabel, QWidget, QScrollArea, QPushButton, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent
import datetime
from PySide6.QtCore import QTimer
from custom_widgets import ToggleSwitch, InAppToast
from settings import load_config, save_config

class TrackingLineEdit(QLineEdit):
    backspacePressedWhenEmpty = Signal()
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Backspace and self.text() == "":
            self.backspacePressedWhenEmpty.emit()
        super().keyPressEvent(event)


class CalendarRow(QWidget):
    def __init__(self, is_night_shift=False, parent=None):
        super().__init__(parent)
        self.is_night = is_night_shift
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_edit = TrackingLineEdit()
        self.main_edit.setPlaceholderText("在此处输入内容，回车键添加下一行，空行退格可删除该行...")
        self.layout.addWidget(self.main_edit, stretch=1)
        
        if not self.is_night:
            # Morning Shift: Time and Priority
            self.time_combo = QComboBox()
            self.time_combo.addItems([f"{i}h" for i in range(1, 9)])
            
            self.priority_combo = QComboBox()
            self.priority_combo.addItems(["低优先级", "中优先级", "高优先级"])
            
            self.layout.addWidget(self.time_combo)
            self.layout.addWidget(self.priority_combo)
        else:
            # Night Shift: Completion input
            self.complete_input = QLineEdit()
            self.complete_input.setPlaceholderText("已完成")
            self.complete_input.setFixedWidth(80)
            self.layout.addWidget(self.complete_input)

    def get_text(self):
        return self.main_edit.text()
    
    def format_output(self, index):
        main_text = self.main_edit.text().strip()
        if not main_text:
            return ""
            
        if not self.is_night:
            time_val = self.time_combo.currentText()
            pri_val = self.priority_combo.currentText()
            return f"{index}、{main_text} 预计耗时{time_val} {pri_val}\n"
        else:
            comp_val = self.complete_input.text().strip()
            if comp_val.isdigit() and 1 <= int(comp_val) <= 99:
                status = f"已完成{comp_val}%"
            else:
                status = "已完成"
            return f"{index}、{main_text} {status}\n"

class Calendar(QWidget):
    reportGenerated = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_night_shift = False
        self.rows = []
        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)

        self.header_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入您的姓名...")
        
        # Load saved name if any
        cfg = load_config()
        saved_name = cfg.get("calendar_user_name", "")
        if saved_name:
            self.name_edit.setText(saved_name)
            
        self.time_label = QLabel(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.time_label.setStyleSheet("color: #a0a0a0; font-weight: bold; font-size: 14px;")
        
        self.header_layout.addWidget(self.name_edit, stretch=1)
        self.header_layout.addWidget(self.time_label, stretch=0)
        self.main_layout.addLayout(self.header_layout)
        
        # Real-time clock updater
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(60000) # Update every minute

        # Shift Mode Toggle Row
        self.shift_layout = QHBoxLayout()
        self.shift_label = QLabel("模式: 上班模式")
        self.shift_label.setStyleSheet("font-weight:bold; color: #5865F2;")
        
        self.shift_toggle = ToggleSwitch()
        # Customizing colors for Morning/Night logic
        # Default (False/Left) = Morning (Blue). Checked (True/Right) = Night (Purple)
        self.shift_toggle.stateChanged.connect(self.on_shift_toggled)
        
        self.shift_layout.addWidget(self.shift_label)
        self.shift_layout.addWidget(self.shift_toggle)
        self.shift_layout.addStretch()
        self.main_layout.addLayout(self.shift_layout)

        # Scroll area for dynamic inputs
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        
        self.scroll_content = QWidget()
        self.inputs_layout = QVBoxLayout(self.scroll_content)
        self.inputs_layout.setAlignment(Qt.AlignTop)
        self.inputs_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll)

        self.create_new_input()

        self.copy_button = QPushButton("生成并复制日报")
        self.copy_button.setObjectName("primaryButton")
        self.copy_button.clicked.connect(self.generate_and_copy)
        self.main_layout.addWidget(self.copy_button)
        
        # Overlay Toast
        self.success_toast = InAppToast("✅ 复制成功！", self)

    def update_clock(self):
        self.time_label.setText(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    def on_shift_toggled(self, state):
        self.is_night_shift = state
        if not state:
            self.shift_label.setText("模式: 上班模式")
            self.shift_label.setStyleSheet("font-weight:bold; color: #5865F2;")
        else:
            self.shift_label.setText("模式: 下班模式")
            self.shift_label.setStyleSheet("font-weight:bold; color: #9A5CFF;")
            
        # Recreate list preserving main text
        saved_texts = [row.get_text() for row in self.rows if row.get_text().strip()]
        
        # Clear layout
        while self.inputs_layout.count():
            item = self.inputs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows.clear()
        
        if not saved_texts:
            self.create_new_input()
        else:
            for text in saved_texts:
                row = self.create_new_input()
                row.main_edit.setText(text)
            self.create_new_input() # Add an empty one at the end

    def create_new_input(self):
        row = CalendarRow(is_night_shift=self.is_night_shift)
        self.rows.append(row)
        
        row.main_edit.returnPressed.connect(lambda r=row: self.on_return_pressed(r))
        row.main_edit.backspacePressedWhenEmpty.connect(lambda r=row: self.on_backspace_empty(r))
        
        self.inputs_layout.addWidget(row)
        row.main_edit.setFocus()
        
        self.scroll_content.adjustSize()
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        return row

    def on_return_pressed(self, sender_row):
        if sender_row == self.rows[-1] and sender_row.get_text().strip():
            self.create_new_input()

    def on_backspace_empty(self, sender_row):
        if len(self.rows) > 1:
            idx = self.rows.index(sender_row)
            self.inputs_layout.removeWidget(sender_row)
            sender_row.deleteLater()
            self.rows.remove(sender_row)
            
            # Focus the previous row
            prev_row = self.rows[idx - 1] if idx > 0 else self.rows[0]
            prev_row.main_edit.setFocus()

    def generate_and_copy(self):
        name_input = self.name_edit.text().strip()
        name = name_input or "未命名"
        today_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Save name on generate if provided
        if name_input:
            cfg = load_config()
            cfg["calendar_user_name"] = name_input
            save_config(cfg)
            
        result = f"【{name}-{today_date} 日报】\n"
        idx = 1
        for row in self.rows:
            formatted = row.format_output(idx)
            if formatted:
                result += formatted
                idx += 1
                
        cb = QGuiApplication.clipboard()
        cb.setText(result.strip())
        self.reportGenerated.emit(self.is_night_shift)
        
        # Show success toast on screen
        self.success_toast.show_toast()
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Calendar()
    ex.resize(600, 500)
    ex.show()
    sys.exit(app.exec())
