# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QApplication, QSizeGrip)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QCursor

from settings import load_config, save_config

class FloatingHolidayWindow(QWidget):
    def __init__(self, content_widget, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.content_widget = content_widget
        self.is_locked = False
        self._drag_pos = None
        self.setAcceptDrops(True)
        
        cfg = load_config()
        opacity = cfg.get("holiday_floating_opacity", 80) / 100.0
        self.setWindowOpacity(opacity)
        
        self.initUI()
        self.setMinimumSize(1, 1)
        self.resize(300, 350)
        
    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Transparent background wrapper
        self.bg_widget = QWidget()
        self.bg_widget.setObjectName("floatBg")
        self.bg_widget.setStyleSheet("""
            QWidget#floatBg {
                background-color: #1e1e24;
                border: 1px solid #333333;
                border-radius: 10px;
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_widget)
        bg_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header for dragging and buttons
        self.header = QWidget()
        self.header.setStyleSheet("background-color: transparent;")
        self.header.setMinimumSize(1, 1)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        from PySide6.QtWidgets import QSizePolicy
        self.title = QLabel("日历倒计时")
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title.setMinimumSize(1, 1)
        self.title.setStyleSheet("color: #a0a0a0; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;")
        
        self.btn_lock = QPushButton("锁定")
        self.btn_lock.setFixedSize(65, 30)
        self.btn_lock.setCursor(Qt.PointingHandCursor)
        self.btn_lock.setStyleSheet("background-color: #5865F2; color: white; border-radius: 5px; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;")
        self.btn_lock.clicked.connect(self.toggle_lock)
        
        self.btn_close = QPushButton("关闭")
        self.btn_close.setFixedSize(65, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("background-color: #ED4245; color: white; border-radius: 5px; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;")
        self.btn_close.clicked.connect(self.close_floating)
        
        header_layout.addWidget(self.title, stretch=1)
        header_layout.addWidget(self.btn_lock, stretch=0)
        header_layout.addWidget(self.btn_close, stretch=0)
        
        # Embed content
        bg_layout.addWidget(self.header)
        bg_layout.addWidget(self.content_widget, stretch=1)
        
        # Footer for size grip
        self.footer = QWidget()
        self.footer.setStyleSheet("background-color: transparent;")
        self.footer.setFixedHeight(15)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch()
        self.size_grip = QSizeGrip(self.footer)
        footer_layout.addWidget(self.size_grip)
        
        bg_layout.addWidget(self.footer)
        self.bg_widget.setMinimumSize(1, 1)
        bg_layout.setSizeConstraint(QVBoxLayout.SetNoConstraint)
        self.main_layout.addWidget(self.bg_widget)
        self.main_layout.setSizeConstraint(QVBoxLayout.SetNoConstraint)
        
    def toggle_lock(self):
        self.is_locked = not self.is_locked
        cfg = load_config()
        base_opacity = cfg.get("holiday_floating_opacity", 80) / 100.0
        
        if self.is_locked:
            self.btn_lock.setText("解锁")
            self.bg_widget.setStyleSheet("QWidget#floatBg { background-color: transparent; border: none; }")
            self.size_grip.hide()
            
            # Make the content transparent to clicks but keep the header clickable
            self.content_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        else:
            self.btn_lock.setText("锁定")
            self.bg_widget.setStyleSheet("QWidget#floatBg { background-color: #1e1e24; border: 1px solid #333333; border-radius: 10px; }")
            self.size_grip.show()
            
            # Restore clicks to content
            self.content_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
    def close_floating(self):
        cfg = load_config()
        cfg["holiday_floating_enabled"] = False
        save_config(cfg)
        self.close()
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and not self.is_locked:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None and not self.is_locked:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    def update_opacity(self, value):
        self.setWindowOpacity(value / 100.0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
            
        file_path = urls[0].toLocalFile()
        if file_path.lower().endswith('.csv'):
            # Grab the main window instance to trigger the trace dialogue logic
            import __main__
            if hasattr(__main__, 'window'):
                __main__.window.trace_dia.process_trace_file(file_path)
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "出错", "只能拖拽 .csv 格式的文件！")
