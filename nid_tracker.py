from PySide6.QtWidgets import (QPushButton, QFileDialog,
                               QMessageBox, QApplication, QVBoxLayout,
                               QLabel, QDialog, QHBoxLayout)
import csv, os
from pathlib import Path

class NidTracker(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NID Tracker")
        self.resize(300, 150)
        
        self.file_button = QPushButton("Select File...")
        self.file_button.setObjectName("primaryButton")
        self.file_button.clicked.connect(self.open_files)
        
        vl1 = QVBoxLayout(self)
        vl1.setSpacing(15)
        
        title_label = QLabel("NID Tracker")
        title_label.setObjectName("titleLabel")
        vl1.addWidget(title_label)
        
        vl1.addWidget(self.file_button)
        vl1.addStretch()

    def open_files(self):
        fileName, _ = QFileDialog.getOpenFileName(self)
        suffix = os.path.splitext(fileName)[1] if fileName else ""
        if fileName and suffix == ".csv":
            self.get_data(fileName)
        elif fileName and suffix != ".csv":
            QMessageBox.critical(self, "Error", "Please choose a trace sheet (.csv)")
    
    def get_data(self, fileName):
        lines = Path(fileName).read_text(encoding="utf-8").splitlines()
        reader = csv.reader(lines)
        reader_head = next(reader)
        content = ""
        nids = ""
        for row in reader:
            content += row[1]
        content_items = content.strip().split(",")
        nid = []
        result = []
        for items in content_items:
            if "nid" in items and "0" not in items and "seller" not in items and "buyer" not in items:
                nid.append(items)
        nid = set(nid)
        for nid in nid:
            nids += nid
        nid = nids.split(" ")
        for item in nid:
            if len(item) == 10:
                result.append(item)
        result = set(result)
        print(result)
                

if __name__ == "__main__":
    app = QApplication()
    window = NidTracker()
    window.show()
    app.exec()