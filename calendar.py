import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit
from datetime import datetime

class DynamicLineEditWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Dynamic LineEdit Example')
        self.setGeometry(100, 100, 300, 200)
        
        # 创建垂直布局
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # 创建第一个LineEdit并添加到布局中
        self.currentLineEdit = QLineEdit(self)
        self.layout.addWidget(self.currentLineEdit)
        
        # 为第一个LineEdit设置回车事件处理
        self.currentLineEdit.returnPressed.connect(self.addNewLineEdit)

    def addNewLineEdit(self):
        # 创建新的LineEdit
        newLineEdit = QLineEdit(self)
        self.layout.addWidget(newLineEdit)  # 添加到布局中
        newLineEdit.returnPressed.connect(self.addNewLineEdit)  # 为新LineEdit设置回车事件处理
        newLineEdit.setFocus()  # 设置新LineEdit获得焦点
        self.currentLineEdit = newLineEdit  # 更新当前LineEdit引用，以便可以连续添加更多LineEdit

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DynamicLineEditWidget()
    ex.show()
    sys.exit(app.exec())
