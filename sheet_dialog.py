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
        

    def get_key_list(self,data):
        key_list = []
        for k in data.keys():
            key_list.append(k)
        return key_list
    
    def fill_the_table(self,data,region):
        index_for_row = 0
        index_for_column = 0
        for k,v in data.items():
            key_button = QPushButton(f"{k}")
            key_content = f"id:{k}\ntrace:{v[0]}"
            key_button.clicked.connect(lambda checked,
                                       t=key_content:self.toclip(t))
            title_button = QPushButton(f"{v[1]}")
            title_content = f"{region}{title_button.text()}"
            title_button.clicked.connect(lambda checked,
                                       t=title_content:self.toclip(t))
            code_button = QPushButton(f"{v[2]}")
            code_button.clicked.connect(lambda checked,
                                       t=code_button.text():self.toclip(t))
            qa_button = QPushButton(f"{v[3]}")
            qa_button.clicked.connect(lambda checked,
                                       t=qa_button.text():self.toclip(t))
            self.setCellWidget(index_for_row,index_for_column,title_button)
            index_for_column += 1 
            self.setCellWidget(index_for_row,index_for_column,key_button)
            index_for_column += 1 
            self.setCellWidget(index_for_row,index_for_column,code_button)
            index_for_column += 1 
            self.setCellWidget(index_for_row,index_for_column,qa_button)
            if index_for_column == 3 and index_for_row < len(self.key_list):
                index_for_row += 1
                index_for_column = 0

    def toclip(self,text):
        cb = QGuiApplication.clipboard()
        cb.setText(text)
