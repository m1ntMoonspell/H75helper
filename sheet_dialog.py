from PySide6.QtWidgets import (QTableWidget,QPushButton)
from PySide6.QtGui import QGuiApplication

class Sheet(QTableWidget):
    def __init__(self,data,region):
        super().__init__()
        self.key_list = self.get_key_list(data)
        self.setRowCount(len(self.key_list))
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["所属系统","ID","负责程序","负责qa"])
        self.fill_the_table(data,region)
        self.setWindowTitle("Trace Helper")
        self.resize(750,400)
        self.setColumnWidth(1,300)
        self.setColumnWidth(0,150)
        

    def get_key_list(self, data):
        return list(data.keys())
    
    def fill_the_table(self, data, region):
        self.verticalHeader().setDefaultSectionSize(60)
        self.verticalHeader().setMinimumSectionSize(60)
        
        for row_idx, (k, v) in enumerate(data.items()):
            key_button = QPushButton(f"{k}")
            key_content = f"id:{k}\ntrace:{v[0]}"
            key_button.clicked.connect(lambda checked, t=key_content: self.toclip(t))
            
            title_button = QPushButton(f"{v[1]}")
            title_content = f"{region}{title_button.text()}"
            title_button.clicked.connect(lambda checked, t=title_content: self.toclip(t))
            
            code_button = QPushButton(f"{v[2]}")
            code_button.clicked.connect(lambda checked, t=code_button.text(): self.toclip(t))
            
            qa_button = QPushButton(f"{v[3]}")
            qa_button.clicked.connect(lambda checked, t=qa_button.text(): self.toclip(t))
            
            self.setCellWidget(row_idx, 0, title_button)
            self.setCellWidget(row_idx, 1, key_button)
            self.setCellWidget(row_idx, 2, code_button)
            self.setCellWidget(row_idx, 3, qa_button)

    def toclip(self,text):
        cb = QGuiApplication.clipboard()
        cb.setText(text)
