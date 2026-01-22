import sys
import os
from PySide6.QtWidgets import (QApplication,QPushButton,QLineEdit,QFileDialog,
                               QDialog,QVBoxLayout,QMessageBox,QLabel)
import csv
from pathlib import Path
import json
from popup_window import Popups
from quick_gm import GMList

class Form(QDialog):
    def __init__(self, parent=None):
        super(Form,self).__init__(parent)
        self.edit = QLineEdit(placeholderText="请输入想要搜索的物品名称")
        self.search_button = QPushButton("搜索")
        self.clear_button = QPushButton("清空输入内容")
        self.contentPath = Path("contentPath.json")
        self.quickPath = Path("quickPath.json")
        self.clear_button.clicked.connect(self.edit.clear)
        self.search_button.clicked.connect(self.get_gm_data)
        self.choose_button = QPushButton("打开文件")
        self.choose_button.clicked.connect(self.open_file)
        self.quick_button = QPushButton("Quick GM")
        self.quick_button.clicked.connect(self.quick_gm)

        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addWidget(self.search_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.choose_button)
        layout.addWidget(self.quick_button)
        self.setLayout(layout)
        self.setWindowTitle("H75 Item ID Helper")
        self.path = ""
        self.check_path()

    def check_path(self):
        if self.contentPath.exists():
            content = self.contentPath.read_text()
            self.path = json.loads(content)
    def open_file(self):
        fileName,idk = QFileDialog.getOpenFileName(self)
        if fileName:
            self.path = fileName
            content = json.dumps(fileName)
            self.contentPath.write_text(content)

    def quick_gm(self):
        quick_dict = {}
        if self.quickPath.exists():
            quickPath = self.quickPath.read_text(encoding="utf-8")
            quickFile = Path(json.loads(quickPath)).read_text(encoding="utf-8")
            lines = quickFile.splitlines()
            for line in lines:
                parts = line.split("^")
                gm = parts[0]
                title = parts[1]
                quick_dict[title]=gm
            quick_list = GMList(quick_dict)
            quick_list.show()
        else:
            fileName,idk = QFileDialog.getOpenFileName(self)
            suffix = os.path.splitext(fileName)[1]
            if fileName and suffix == ".txt":
                path = json.dumps(fileName)
                self.quickPath.write_text(path)
                content = Path(fileName).read_text(encoding="utf-8")
                lines = content.splitlines()
                for line in lines:
                    parts = line.split("^")
                    gm = parts[0]
                    title = parts[1]
                    quick_dict[title]=gm
                quick_list = GMList(quick_dict)
                quick_list.show()
            else:
                pass


    def get_gm_data(self):
        if not self.path:
            QMessageBox.critical(self,"错误","请选择物品ID全量统计表")
        else:
            suffix = os.path.splitext(self.path)[1]
            if suffix == ".csv":
                path = Path(self.path)
                lines = path.read_text().splitlines()
                reader = csv.reader(lines)
                reader_chn_header = next(reader)
                reader_header = next(reader)
                for index,colum in enumerate(reader_chn_header):
                    if colum == "物品id":
                        item_id_index = index
                    elif colum == "物品名称":
                        item_name_index = index
                
                item_dict = {}

                for row in reader:
                    try:
                        item_id = int(row[item_id_index])
                        item_name = row[item_name_index].strip()
                    except ValueError:
                        print(f"未找到{item_name}相关的ID")
                    else:
                        item_dict[item_name] = item_id

                inputName = self.edit.text()
                result_dict = {}
                for k,v in item_dict.items():
                    if inputName in k and inputName:
                        result_dict[k] = v
                if result_dict:
                    self.popwindow(result_dict)
                elif not result_dict and inputName:
                    QMessageBox.critical(self,"搜索结果",
                                    f"未找到与'{inputName}'有关的内容")
            else:
                QMessageBox.critical(self,"错误","请选择物品ID全量统计表")
            
    def popwindow(self,dict):
        popup = Popups(dict)
        if popup.exec():
            popup.show()

if __name__ == "__main__":
    app = QApplication()
    form = Form()
    form.show()
    sys.exit(app.exec())