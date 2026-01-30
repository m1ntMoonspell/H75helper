from PySide6.QtWidgets import (QPushButton,QFileDialog,
                               QMessageBox,QApplication,QVBoxLayout,
                               QLabel,QDialog,QHBoxLayout)
import csv,os
from pathlib import Path
from slice_dialog import SliceDia
from sheet_dialog import Sheet
from ident2link import TransLink


class TraceDia(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.creat_subwidgets()
        self.setWindowTitle("Trace Helper")

    def creat_subwidgets(self):
        self.file_button = QPushButton("Select...",self)
        self.file_button.clicked.connect(self.open_files)
        self.slice_button = QPushButton("Slice...",self)
        self.slice_button.clicked.connect(self.slice_phrase)
        self.tolink_button = QPushButton("2 Link",self)
        self.tolink_button.clicked.connect(self.tolink_func)
        layout = QVBoxLayout(self)
        hl = QHBoxLayout()
        hlbtn = QHBoxLayout()
        self.global_button = QPushButton("NA")
        self.cn_button = QPushButton("CN")
        hlbtn.addWidget(self.global_button)
        hlbtn.addWidget(self.cn_button)
        self.status_label = QLabel("Status:")
        self.status = QLabel("Null")
        self.global_button.clicked.connect(self.switch_to_NA)
        self.cn_button.clicked.connect(self.switch_to_CN)
        self.region = ""
        hl.addWidget(self.status_label)
        hl.addWidget(self.status)
        hl.addStretch()
        layout.addWidget(self.file_button)
        layout.addWidget(self.slice_button)
        layout.addWidget(self.tolink_button)
        layout.addLayout(hlbtn)
        layout.addLayout(hl)
        self.setLayout(layout)
        self.slicer = SliceDia()
        self.tolink = TransLink()

    def slice_phrase(self):
        self.slicer.exec()

    def tolink_func(self):
        self.tolink.exec()

    def switch_to_NA(self):
        self.status.setText("<p style='color:blue'>NA</p>")
        self.region = "【国际服trace】"
    
    def switch_to_CN(self):
        self.status.setText("<p style='color:red'>CN</p>")
        self.region = "【国服trace】"

    def open_files(self):
        fileName,_ = QFileDialog.getOpenFileName(self)
        suffix = os.path.splitext(fileName)[1]
        if fileName and suffix == ".csv":
            self.get_data(fileName)
            self.sheet = Sheet(self.get_data(fileName),self.region)
            self.sheet.show()
        elif fileName and suffix != ".csv":
            QMessageBox.critical(self,"Error","please choose trace sheet")
        else:
            pass

    def get_data(self,fileName):
        ID_dict = {}
        lines = Path(fileName).read_text(encoding="utf-8").splitlines()
        reader = csv.reader(lines)
        reader_head = next(reader)
        for index,colum in enumerate(reader_head):
            if colum == "ID":
                index_for_ID = int(index)
            if colum == "Trace链接":
                index_for_link = int(index)
            if colum == "所属系统":
                index_for_title = int(index)
            if colum == "负责程序":
                index_for_code = int(index)
            if colum == "负责qa":
                index_for_qa = int(index)

        for row in reader:
            try:
                ID = row[index_for_ID]
                link = row[index_for_link]
                title = row[index_for_title]
                code = row[index_for_code]
                qa = row[index_for_qa]
            except ValueError:
                print(f"Missing for {ID}")
            else:
                ID_dict[ID] = [link,title,code,qa]

        for k,v in ID_dict.copy().items():
            if not v[1] or not v[2] or not v[3]:
                del ID_dict[k]
        return  ID_dict
if __name__ == "__main__":
    app = QApplication()
    window = TraceDia()
    window.show()
    app.exec()