import sys
import os
from PySide6.QtWidgets import (QApplication, QPushButton, QLineEdit, QFileDialog,
                               QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel, QComboBox)
import csv
from pathlib import Path
import json
from popup_window import Popups
from quick_gm import GMList
from settings import load_config, save_config

class Form(QWidget):
    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.path = ""
        self.check_path()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("GM Item Helper")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)
        
        # Search Header
        search_layout = QHBoxLayout()
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("请输入想要搜索的物品名称...")
        
        self.search_button = QPushButton("搜索")
        self.search_button.setObjectName("primaryButton")
        self.search_button.clicked.connect(self.get_gm_data)
        
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.edit.clear)
        
        search_layout.addWidget(self.edit)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_button)
        layout.addLayout(search_layout)
        
        # Quick Add Equip Row
        equip_layout = QHBoxLayout()
        self.equip_id_edit = QLineEdit()
        self.equip_id_edit.setPlaceholderText("物品ID")
        
        self.equip_qty_edit = QLineEdit()
        self.equip_qty_edit.setPlaceholderText("数量 (默认: 1)")
        self.equip_qty_edit.setFixedWidth(100)
        
        self.equip_send_btn = QPushButton("执行")
        self.equip_send_btn.setObjectName("primaryButton")
        self.equip_send_btn.clicked.connect(self.send_add_equip)
        
        equip_layout.addWidget(self.equip_id_edit, stretch=1)
        equip_layout.addWidget(self.equip_qty_edit, stretch=0)
        equip_layout.addWidget(self.equip_send_btn, stretch=0)
        layout.addLayout(equip_layout)
        
        # Raw command row
        raw_layout = QHBoxLayout()
        self.raw_cmd_edit = QLineEdit()
        self.raw_cmd_edit.setPlaceholderText("输入自定义指令...")
        
        self.raw_send_btn = QPushButton("执行")
        self.raw_send_btn.setObjectName("primaryButton")
        self.raw_send_btn.clicked.connect(self.send_raw_command)
        
        raw_layout.addWidget(self.raw_cmd_edit, stretch=1)
        raw_layout.addWidget(self.raw_send_btn, stretch=0)
        layout.addLayout(raw_layout)
        
        layout.addStretch()
        
        # Console target selector
        console_layout = QHBoxLayout()
        console_layout.addWidget(QLabel("目标控制台:"))
        
        self.console_combo = QComboBox()
        self.console_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        console_layout.addWidget(self.console_combo, stretch=1)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_consoles)
        console_layout.addWidget(self.refresh_btn, stretch=0)
        
        layout.addLayout(console_layout)
        
        # Bottom Toolbars
        actions_layout = QHBoxLayout()
        self.choose_button = QPushButton("打开文件...")
        self.choose_button.clicked.connect(self.open_file)
        
        self.quick_button = QPushButton("Quick GM")
        self.quick_button.clicked.connect(self.quick_gm)
        
        actions_layout.addWidget(self.choose_button)
        actions_layout.addWidget(self.quick_button)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        # Initial console list load
        self.refresh_consoles()

    def check_path(self):
        config = load_config()
        self.path = config.get("gm_content_path", "")

    def open_file(self):
        fileName, idk = QFileDialog.getOpenFileName(self, "选择原数据表", filter="CSV Files (*.csv)")
        if fileName:
            self.path = fileName
            
            # Save to unified config
            config = load_config()
            config["gm_content_path"] = fileName
            save_config(config)

    def quick_gm(self):
        quick_dict = {}
        config = load_config()
        quick_file_path = config.get("gm_quick_path", "")
        
        path_obj = Path(quick_file_path) if quick_file_path else None
        
        if path_obj and path_obj.exists():
            quickFile = path_obj.read_text(encoding="utf-8")
            lines = quickFile.splitlines()
            for line in lines:
                parts = line.split("^")
                # Ensure parts length prevents index errors
                if len(parts) >= 2:
                    gm = parts[0]
                    title = parts[1]
                    quick_dict[title] = gm
            self.quick_list = GMList(quick_dict, self)
            self.quick_list.show()
        else:
            fileName, idk = QFileDialog.getOpenFileName(self, "选择 Quick GM 配置文件", filter="Text Files (*.txt)")
            if fileName and fileName.endswith(".txt"):
                # Save to unified config
                config["gm_quick_path"] = fileName
                save_config(config)
                
                content = Path(fileName).read_text(encoding="utf-8")
                lines = content.splitlines()
                for line in lines:
                    parts = line.split("^")
                    if len(parts) >= 2:
                        gm = parts[0]
                        title = parts[1]
                        quick_dict[title] = gm
                self.quick_list = GMList(quick_dict, self)
                self.quick_list.show()

    def get_gm_data(self):
        if not self.path:
            QMessageBox.critical(self, "错误", "请选择物品ID全量统计表")
        else:
            suffix = os.path.splitext(self.path)[1]
            if suffix == ".csv":
                path = Path(self.path)
                lines = path.read_text().splitlines()
                reader = csv.reader(lines)
                reader_chn_header = next(reader)
                reader_header = next(reader)
                
                item_id_index = item_name_index = -1
                for index, colum in enumerate(reader_chn_header):
                    if colum == "物品id":
                        item_id_index = index
                    elif colum == "物品名称":
                        item_name_index = index
                
                item_dict = {}
                for row in reader:
                    try:
                        item_id = int(row[item_id_index])
                        item_name = row[item_name_index].strip()
                    except (ValueError, IndexError):
                        pass
                    else:
                        item_dict[item_name] = item_id

                inputName = self.edit.text()
                result_dict = {}
                for k, v in item_dict.items():
                    if inputName in k and inputName:
                        result_dict[k] = v
                        
                if result_dict:
                    self.popwindow(result_dict)
                elif not result_dict and inputName:
                    QMessageBox.information(self, "搜索结果", f"未找到与'{inputName}'有关的内容")
            else:
                QMessageBox.critical(self, "错误", "请选择物品ID全量统计表 (.csv)")
            
    def popwindow(self, dict):
        self.popup = Popups(dict, self)
        self.popup.exec()

    def refresh_consoles(self):
        from auto_typer import get_window_choices
        cfg = load_config()
        title = cfg.get("console_title", "Console")
        
        self.console_combo.clear()
        choices = get_window_choices(title)
        if choices:
            for hwnd, label in choices:
                self.console_combo.addItem(label, hwnd)
        else:
            self.console_combo.addItem("未找到匹配的控制台窗口", 0)

    def get_selected_hwnd(self):
        """Returns the HWND selected in the console dropdown, or 0 if none."""
        return self.console_combo.currentData() or 0

    def send_add_equip(self):
        item_id = self.equip_id_edit.text().strip()
        qty = self.equip_qty_edit.text().strip() or "1"
        
        if not item_id:
            return
        
        command = f"#add_equip {item_id} {qty} 0 True"
        self._send_command(command)

    def send_raw_command(self):
        cmd = self.raw_cmd_edit.text().strip()
        if not cmd:
            return
        self._send_command(cmd)

    def _send_command(self, command):
        """Shared send logic: routes through the selected HWND in the dropdown."""
        from auto_typer import send_command_to_hwnd
        from custom_widgets import InAppToast
        
        hwnd = self.get_selected_hwnd()
        success = send_command_to_hwnd(hwnd, command) if hwnd else False
        
        if not success:
            from PySide6.QtGui import QGuiApplication
            cb = QGuiApplication.clipboard()
            cb.setText(command)
            
            win = self.window()
            if win:
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

if __name__ == "__main__":
    app = QApplication()
    form = Form()
    form.show()
    sys.exit(app.exec())
