from PySide6.QtWidgets import (QPushButton, QFileDialog, QMessageBox, QApplication, 
                               QVBoxLayout, QLabel, QWidget, QHBoxLayout)
import csv, os
from pathlib import Path
from slice_dialog import SliceDia
from sheet_dialog import Sheet
from ident2link import TransLink
from custom_widgets import ToggleSwitch

class TraceDia(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.creat_subwidgets()

    def creat_subwidgets(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Trace Helper")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        self.file_button = QPushButton("Select File...")
        self.file_button.setObjectName("primaryButton")
        self.file_button.clicked.connect(self.open_files)
        
        self.slice_button = QPushButton("Slice...")
        self.slice_button.clicked.connect(self.slice_phrase)
        
        self.tolink_button = QPushButton("2 Link")
        self.tolink_button.clicked.connect(self.tolink_func)
        
        toolbar_layout.addWidget(self.file_button)
        toolbar_layout.addWidget(self.slice_button)
        toolbar_layout.addWidget(self.tolink_button)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Options row
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Region Setting:"))
        
        self.region_toggle = ToggleSwitch(self)
        self.region_toggle.stateChanged.connect(self.switch_region)
        
        self.status = QLabel("NA")
        self.status.setStyleSheet("color: #5865F2; font-weight: bold;")
        self.region = "【国际服trace】"
        
        options_layout.addWidget(self.region_toggle)
        options_layout.addWidget(self.status)
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        layout.addStretch()
        
        self.slicer = SliceDia(self)
        self.tolink = TransLink(self)

    def slice_phrase(self):
        self.slicer.exec()

    def tolink_func(self):
        self.tolink.exec()

    def switch_region(self, state):
        if state: # Checked (CN)
            self.status.setText("CN")
            self.status.setStyleSheet("color: #ED4245; font-weight: bold;")
            self.region = "【国服trace】"
        else: # Unchecked (NA)
            self.status.setText("NA")
            self.status.setStyleSheet("color: #5865F2; font-weight: bold;")
            self.region = "【国际服trace】"

    def open_files(self):
        fileName, _ = QFileDialog.getOpenFileName(self)
        if fileName:
            self.process_trace_file(fileName)
            
    def process_trace_file(self, fileName):
        suffix = os.path.splitext(fileName)[1] if fileName else ""
        if suffix == ".csv":
            data = self.get_data(fileName)
            self.sheet = Sheet(data, self.region)
            self.sheet.show()
        else:
            QMessageBox.critical(self, "Error", "Please choose a trace sheet (.csv)")

    def get_data(self, fileName):
        ID_dict = {}
        lines = Path(fileName).read_text(encoding="utf-8").splitlines()
        reader = csv.reader(lines)
        reader_head = next(reader)
        
        index_for_ID = index_for_link = index_for_title = index_for_code = index_for_qa = -1
        
        for index, colum in enumerate(reader_head):
            if colum == "ID":
                index_for_ID = index
            if colum == "Trace链接":
                index_for_link = index
            if colum == "所属系统":
                index_for_title = index
            if colum == "负责程序":
                index_for_code = index
            if colum == "负责qa":
                index_for_qa = index

        for row in reader:
            try:
                ID = row[index_for_ID]
                link = row[index_for_link]
                title = row[index_for_title]
                code = row[index_for_code]
                qa = row[index_for_qa]
            except (ValueError, IndexError):
                pass
            else:
                ID_dict[ID] = [link, title, code, qa]

        for k, v in ID_dict.copy().items():
            if not v[1] or not v[2] or not v[3]:
                del ID_dict[k]
        return ID_dict

if __name__ == "__main__":
    app = QApplication()
    window = TraceDia()
    window.show()
    app.exec()
