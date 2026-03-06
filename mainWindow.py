from PySide6.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QWidget,
                               QStackedWidget, QMessageBox, QDialog, QLabel,
                               QHBoxLayout, QPushButton, QFrame, QButtonGroup,
                               QSystemTrayIcon, QStyle, QMenu)
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QIcon, QCloseEvent
from trace_helper_main_window import TraceDia
from gm_user_interface import Form
from daily_report_tab import Calendar as CalendarView
from settings import SettingsDia, load_config, _resource_dir
from custom_toast import ToastNotification
from holiday_tab import HolidayTab

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(800, 500)
        self.setWindowTitle("H75 Helper")
        
        # Tracking flags for daily reports
        self.morning_report_done = False
        self.night_report_done = False
        self.last_checked_date = None
        
        self.creat_subwidgets()
        self.setup_tray_and_timers()
        
        self.floating_holiday = None
        self.sync_holiday_float_state()

    def setup_tray_and_timers(self):
        # Create System Tray
        self.tray_icon = QSystemTrayIcon(self)
        
        icon_path = str(_resource_dir() / "icon.png")
        self.app_icon = QIcon(icon_path)
        
        if self.app_icon.isNull():
            self.app_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(self.app_icon)
        self.setWindowIcon(self.app_icon)
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("打开主面板")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("退出 H75 Helper")
        quit_action.triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.messageClicked.connect(self.on_tray_message_clicked)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Setup Timer for precise checks (every 5 seconds) to avoid missing minute boundaries
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_time_for_notifications)
        self.check_timer.start(5000)
        self.last_alerted_time = None
        
        # Connect Calendar submission to mark as done
        self.calendar_view.reportGenerated.connect(self.mark_report_done)

    def mark_report_done(self, is_night):
        if is_night:
            self.night_report_done = True
        else:
            self.morning_report_done = True

    def closeEvent(self, event: QCloseEvent):
        # Prevent app from closing, minimize it to the system tray instead.
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("H75 Helper", "已最小化到托盘，程序仍在后台运行监听打卡时间！", QSystemTrayIcon.Information, 3000)

    def check_time_for_notifications(self):
        current_time = QTime.currentTime()
        now_str = f"{current_time.hour():02d}:{current_time.minute():02d}"
        
        # Reset flags on a new day (e.g., at midnight)
        if current_time.hour() == 0 and current_time.minute() == 0:
            self.morning_report_done = False
            self.night_report_done = False
            
        # Load user-defined times
        config = load_config()
        m_h, m_m = config.get("morning_time", [10, 30])
        n_h, n_m = config.get("night_time", [18, 30])
            
        # If we already alerted this exact minute, skip to prevent spam
        if self.last_alerted_time == now_str:
            return
            
        # Morning Check
        if current_time.hour() == m_h and current_time.minute() == m_m:
            if not self.morning_report_done:
                self.last_alerted_time = now_str
                self.pending_notification_type = "morning"
                self.show_custom_toast("日报提醒", f"现在是 {m_h:02d}:{m_m:02d}。请填写您的上班日报！")
                
        # Night Check
        elif current_time.hour() == n_h and current_time.minute() == n_m:
            if not self.night_report_done:
                self.last_alerted_time = now_str
                self.pending_notification_type = "night"
                self.show_custom_toast("日报提醒", f"现在是 {n_h:02d}:{n_m:02d}。请填写您的下班日报！")

    def show_custom_toast(self, title, message):
        self.active_toast = ToastNotification(title, message, click_callback=self.on_tray_message_clicked)
        self.active_toast.show_toast()

    def on_tray_message_clicked(self):
        self.show()
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.activateWindow()
        self.raise_()
        
        # Switch to Calendar tab (index 2)
        self.btn_calendar.setChecked(True)
        self.stacked_widget.setCurrentIndex(2)
        
        if hasattr(self, 'pending_notification_type'):
            if self.pending_notification_type == "morning":
                self.calendar_view.shift_toggle.setChecked(False) # Turn to morning mode
            elif self.pending_notification_type == "night":
                self.calendar_view.shift_toggle.setChecked(True) # Turn to night mode
            del self.pending_notification_type

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
            self.activateWindow()
            self.raise_()

    def creat_subwidgets(self):
        menuBar = self.menuBar()
        helpMenu = menuBar.addMenu("其他")
        luckyNode = helpMenu.addAction("How's the luck today")
        
        settingsNode = helpMenu.addAction("Settings")
        settingsNode.triggered.connect(self.settings_clicked)
        
        abotNode = helpMenu.addAction("About")
        abotNode.triggered.connect(self.aboutclicked)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("QFrame#sidebar { background-color: #23232b; border-right: 1px solid #3e3e4a; }")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(10)
        
        title_label = QLabel("H75 Helper")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(30)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.btn_gm = QPushButton("GM Helper")
        self.btn_gm.setCheckable(True)
        self.btn_gm.setChecked(True)
        self.btn_gm.setProperty("navBtn", True)
        self.btn_group.addButton(self.btn_gm, 0)
        
        self.btn_trace = QPushButton("Trace Helper")
        self.btn_trace.setCheckable(True)
        self.btn_trace.setProperty("navBtn", True)
        self.btn_group.addButton(self.btn_trace, 1)

        self.btn_calendar = QPushButton("日报")
        self.btn_calendar.setCheckable(True)
        self.btn_calendar.setProperty("navBtn", True)
        self.btn_group.addButton(self.btn_calendar, 2)
        
        self.btn_holiday = QPushButton("日历")
        self.btn_holiday.setCheckable(True)
        self.btn_holiday.setProperty("navBtn", True)
        self.btn_group.addButton(self.btn_holiday, 3)
        
        sidebar_layout.addWidget(self.btn_gm)
        sidebar_layout.addWidget(self.btn_trace)
        sidebar_layout.addWidget(self.btn_calendar)
        sidebar_layout.addWidget(self.btn_holiday)
        sidebar_layout.addStretch()
        
        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        
        self.gm_form = Form(self)
        self.trace_dia = TraceDia(self)
        self.calendar_view = CalendarView(self)
        self.holiday_view = HolidayTab(self)
        
        self.stacked_widget.addWidget(self.embed_into_vlayout(self.gm_form, 20))
        self.stacked_widget.addWidget(self.embed_into_vlayout(self.trace_dia, 20))
        self.stacked_widget.addWidget(self.embed_into_vlayout(self.calendar_view, 20))
        self.stacked_widget.addWidget(self.embed_into_vlayout(self.holiday_view, 20))
        
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stacked_widget)
        
        self.btn_group.idClicked.connect(self.stacked_widget.setCurrentIndex)

    def embed_into_vlayout(self, w, margin=5):
        result = QWidget()
        layout = QVBoxLayout(result)
        layout.addWidget(w)
        layout.setContentsMargins(margin, margin, margin, margin)
        return result
    
    def settings_clicked(self):
        settings_dia = SettingsDia(self)
        settings_dia.exec()
        self.sync_holiday_float_state()
        
    def sync_holiday_float_state(self):
        cfg = load_config()
        is_floating = cfg.get("holiday_floating_enabled", False)
        opacity = cfg.get("holiday_floating_opacity", 80)
        
        if is_floating:
            if self.floating_holiday is None:
                from holiday_float import FloatingHolidayWindow
                from holiday_tab import HolidayTab
                self.floating_holiday = FloatingHolidayWindow(HolidayTab())
                
            self.floating_holiday.update_opacity(opacity)
            self.floating_holiday.show()
        else:
            if self.floating_holiday is not None:
                self.floating_holiday.close()
                self.floating_holiday = None
        
    def aboutclicked(self):
        popDia = QDialog(self)
        popDia.setMinimumSize(300, 150)
        popDia.setWindowTitle("About")
        label = QLabel("All Rights Reserved<br><br>" \
        "<a href='https://github.com/m1ntMoonspell?tab=repositories' style='color:#5865F2;'>@m1nt</a>")
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(label)
        popDia.setLayout(layout)
        if popDia.exec():
            popDia.show()

if __name__ == "__main__":
    from pathlib import Path
    app = QApplication()
    style_path = Path(__file__).parent / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text())
    window = MyWindow()
    window.show()
    app.exec()
