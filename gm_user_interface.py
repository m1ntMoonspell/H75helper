import sys
import os
from PySide6.QtWidgets import (QApplication, QPushButton, QLineEdit, QFileDialog,
                               QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel, QComboBox)
import csv
from pathlib import Path
from popup_window import Popups
from quick_gm import GMList
from auto_typer import send_command_to_hwnd, get_window_choices
from custom_widgets import show_error_toast
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
        file_name, _ = QFileDialog.getOpenFileName(self, "选择原数据表", filter="CSV Files (*.csv)")
        if file_name:
            self.path = file_name
            config = load_config()
            config["gm_content_path"] = file_name
            save_config(config)

    def quick_gm(self):
        config = load_config()
        quick_file_path = config.get("gm_quick_path", "")
        path_obj = Path(quick_file_path) if quick_file_path else None
        
        if path_obj and path_obj.exists():
            quick_dict = self._parse_quick_file(path_obj)
            self.quick_list = GMList(quick_dict, self)
            self.quick_list.show()
        else:
            file_name, _ = QFileDialog.getOpenFileName(self, "选择 Quick GM 配置文件", filter="Text Files (*.txt)")
            if file_name and file_name.endswith(".txt"):
                config["gm_quick_path"] = file_name
                save_config(config)
                quick_dict = self._parse_quick_file(Path(file_name))
                self.quick_list = GMList(quick_dict, self)
                self.quick_list.show()

    @staticmethod
    def _parse_quick_file(path):
        """Parse a Quick GM config file into a {title: gm_command} dict."""
        quick_dict = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split("^")
            if len(parts) >= 2:
                quick_dict[parts[1]] = parts[0]
        return quick_dict

    def get_gm_data(self):
        if not self.path:
            QMessageBox.critical(self, "错误", "请选择物品ID全量统计表")
            return

        suffix = os.path.splitext(self.path)[1].lower()
        if suffix != ".csv":
            QMessageBox.critical(self, "错误", "请选择有效的物品ID全量统计表 (.csv)")
            return

        try:
            path = Path(self.path)
            content = ""
            # Try multiple encodings for robustness, utf-8-sig handles BOM
            for enc in ["utf-8-sig", "gb18030"]:
                try:
                    content = path.read_text(encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                raise ValueError("无法识别文件编码或文件为空")

            lines = content.splitlines()
            reader = csv.reader(lines)
            try:
                # Sanitize header by stripping whitespace and BOM if any
                reader_chn_header = [c.strip().replace('\ufeff', '') for c in next(reader)]
                _ = next(reader)  # Skip second header line
            except StopIteration:
                raise ValueError("CSV文件格式不正确（缺少表头）")

            item_id_index = item_name_index = -1
            for index, colum in enumerate(reader_chn_header):
                # Fuzzy matching for robustness
                if "物品id" in colum or "物品ID" in colum:
                    item_id_index = index
                elif "物品名称" in colum:
                    item_name_index = index

            if item_id_index == -1 or item_name_index == -1:
                raise ValueError(f"未在CSV中找到'物品id'或'物品名称'列\n当前检测到的表头: {', '.join(reader_chn_header)}")

            item_dict = {}
            for row in reader:
                try:
                    item_id = int(row[item_id_index])
                    item_name = row[item_name_index].strip()
                    if item_name:
                        item_dict[item_name] = item_id
                except (ValueError, IndexError):
                    continue

            input_name = self.edit.text().strip()
            result_dict = {}
            if input_name:
                for name, iid in item_dict.items():
                    if input_name in name:
                        result_dict[name] = iid

            if result_dict:
                self.popwindow(result_dict)
            elif input_name:
                QMessageBox.information(self, "搜索结果", f"未找到与'{input_name}'有关的内容")
                
        except Exception as e:
            QMessageBox.critical(self, "读取错误", f"处理表格文件时发生错误:\n{str(e)}")
            
    def popwindow(self, dict):
        self.popup = Popups(dict, self)
        self.popup.exec()

    def refresh_consoles(self):
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
        hwnd = self.get_selected_hwnd()
        success = send_command_to_hwnd(hwnd, command) if hwnd else False
        
        if not success:
            show_error_toast(self, command)

if __name__ == "__main__":
    app = QApplication()
    form = Form()
    form.show()
    sys.exit(app.exec())
