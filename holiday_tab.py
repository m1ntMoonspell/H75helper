import sys
import datetime
import urllib.request
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
import math

class HolidayFetcher(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            year = datetime.datetime.now().year
            url = f"https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                
            # Fetch next year if we are near the end of the year (e.g. Month >= 11)
            if datetime.datetime.now().month >= 11:
                next_year = year + 1
                try:
                    url2 = f"https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{next_year}.json"
                    req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req2, timeout=5) as response2:
                        data2 = json.loads(response2.read())
                        data['days'].extend(data2.get('days', []))
                except Exception:
                    pass
                    
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class HolidayTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.next_holiday_name = ""
        self.next_holiday_date = None
        self.holiday_duration = 0
        self.initUI()
        self.setMinimumSize(1, 1)
        
        self.fetcher = HolidayFetcher()
        self.fetcher.finished.connect(self.on_data)
        self.fetcher.error.connect(self.on_error)
        self.fetcher.start()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        layout.setSizeConstraint(QVBoxLayout.SetNoConstraint)
        layout.addStretch()
        
        self.title_label = QLabel("正在获取节假日数据...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setMinimumSize(1, 1)
        self.title_label.setStyleSheet("font-size: 24px; color: #e0e0e0; font-weight: bold;")
        
        self.days_label = QLabel("--")
        self.days_label.setAlignment(Qt.AlignCenter)
        self.days_label.setMinimumSize(1, 1)
        self.days_label.setStyleSheet("font-size: 140px; font-weight: bold; color: #ff4d4d;")
        
        self.time_label = QLabel("-- 小时 -- 分钟 -- 秒")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setMinimumSize(1, 1)
        self.time_label.setStyleSheet("font-size: 20px; color: #a0a0a0;")
        
        self.duration_label = QLabel("本次共放假: -- 天")
        self.duration_label.setAlignment(Qt.AlignCenter)
        self.duration_label.setMinimumSize(1, 1)
        self.duration_label.setStyleSheet("font-size: 18px; color: #5865F2; font-weight: bold;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.days_label, stretch=1)
        layout.addWidget(self.time_label)
        layout.addWidget(self.duration_label)
        layout.addStretch()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        # Scale the giant days label dynamically
        day_size = max(20, min(140, int(h * 0.4)))
        self.days_label.setStyleSheet(f"font-size: {day_size}px; font-weight: bold; color: #ff4d4d;")
        
        # Scale other labels appropriately
        title_size = max(12, min(24, int(w * 0.06)))
        self.title_label.setStyleSheet(f"font-size: {title_size}px; color: #e0e0e0; font-weight: bold;")
        
        time_size = max(10, min(20, int(w * 0.05)))
        self.time_label.setStyleSheet(f"font-size: {time_size}px; color: #a0a0a0;")
        
        dur_size = max(10, min(18, int(w * 0.045)))
        self.duration_label.setStyleSheet(f"font-size: {dur_size}px; color: #5865F2; font-weight: bold;")
        
    def on_error(self, err):
        self.title_label.setText("网络请求失败，请检查网络...")
        
    def on_data(self, data):
        now = datetime.datetime.now()
        upcoming = []
        for d in data.get('days', []):
            if d.get('isOffDay'):
                dt = datetime.datetime.strptime(d['date'], "%Y-%m-%d")
                if dt.date() >= now.date():
                    upcoming.append((dt, d['name']))
                    
        if not upcoming:
            self.title_label.setText("今年暂无更多法定节假日了！")
            return
            
        upcoming.sort(key=lambda x: x[0])
        self.next_holiday_date = upcoming[0][0]
        self.next_holiday_name = upcoming[0][1]
        
        # Calculate duration
        count = sum(1 for x in data.get('days', []) if x.get('isOffDay') and x.get('name') == self.next_holiday_name)
        self.holiday_duration = count
        
        self.title_label.setText(f"距离【{self.next_holiday_name}】还有")
        self.duration_label.setText(f"本次共放假: {self.holiday_duration} 天")
        
        self.update_countdown()
        
    def update_countdown(self):
        if not self.next_holiday_date:
            return
            
        now = datetime.datetime.now()
        target = datetime.datetime(self.next_holiday_date.year, self.next_holiday_date.month, self.next_holiday_date.day)
        
        if now.date() == target.date():
            self.title_label.setText(f"今天是【{self.next_holiday_name}】！")
            self.days_label.setText("0")
            self.time_label.setText("好好享受假期吧！")
            return
            
        diff = target - now
        if diff.total_seconds() < 0:
            # Refresh if passed
            self.fetcher.start()
            return

        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        self.days_label.setText(f"{days}")
        self.time_label.setText(f"{hours} 小时 {minutes} 分钟 {seconds} 秒")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HolidayTab()
    ex.resize(600, 500)
    ex.show()
    sys.exit(app.exec())
