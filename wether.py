import sys
import os
import json
import requests
import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor, QLinearGradient


class NaturalScrollArea(QScrollArea):
    """自然滚动：滚轮向下，内容也向下"""

    def wheelEvent(self, event):
        dy = event.pixelDelta().y() if not event.angleDelta().isNull() and event.pixelDelta().y() != 0 else event.angleDelta().y()
        # Qt: 向上滚为正、向下滚为负；我们减去 dy，实现自然方向
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
        event.accept()


class WeatherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌤️ 一款无聊的天气查询软件")
        self.setFixedSize(520, 900)  # 增加高度以容纳主题切换按钮

        # 当前主题模式
        self.is_dark_mode = False

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # 标题
        title_label = QLabel("无聊的天气查询软件")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei", 48, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setObjectName("title_label")
        layout.addWidget(title_label)

        # 主题切换按钮
        theme_button_layout = QHBoxLayout()
        theme_button_layout.addStretch()
        self.theme_button = QPushButton("🌙 切换到深色模式")
        self.theme_button.setFixedSize(180, 40)
        self.theme_button.setObjectName("theme_button")
        self.theme_button.clicked.connect(self.toggle_theme)
        theme_button_layout.addWidget(self.theme_button)
        theme_button_layout.addStretch()
        layout.addLayout(theme_button_layout)

        # 输入区域卡片
        input_frame = QFrame()
        input_frame.setObjectName("card")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 15, 15, 15)

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("请输入城市名称...")
        self.city_input.setObjectName("city_input")
        input_layout.addWidget(self.city_input)

        self.search_button = QPushButton("查询")
        self.search_button.setObjectName("search_button")
        self.search_button.clicked.connect(self.get_weather)
        input_layout.addWidget(self.search_button)

        # 城市历史记录下拉框
        self.history_box = QComboBox()
        self.history_box.setEditable(False)
        self.history_box.setObjectName("history_box")
        self.history_box.currentIndexChanged.connect(self.select_history_city)
        input_layout.addWidget(self.history_box)

        layout.addWidget(input_frame)

        # 天气信息卡片
        info_frame = QFrame()
        info_frame.setObjectName("card")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(15)

        self.city_label = QLabel("城市: --")
        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        info_layout.addWidget(self.city_label)

        weather_top_layout = QHBoxLayout()
        self.weather_icon = QLabel()
        self.weather_icon.setFixedSize(100, 100)
        weather_top_layout.addWidget(self.weather_icon, alignment=Qt.AlignCenter)

        self.temperature_label = QLabel("--°C")
        self.temperature_label.setFont(QFont("Arial", 34, QFont.Bold))
        weather_top_layout.addWidget(self.temperature_label, alignment=Qt.AlignCenter)
        info_layout.addLayout(weather_top_layout)

        self.weather_label = QLabel("天气状况: --")
        self.weather_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.weather_label)

        details_layout = QHBoxLayout()
        left_details = QVBoxLayout()
        self.humidity_label = QLabel("湿度: --")
        self.wind_label = QLabel("风速: --")
        left_details.addWidget(self.humidity_label)
        left_details.addWidget(self.wind_label)

        right_details = QVBoxLayout()
        self.pressure_label = QLabel("气压: --")
        self.visibility_label = QLabel("能见度: --")
        right_details.addWidget(self.pressure_label)
        right_details.addWidget(self.visibility_label)

        details_layout.addLayout(left_details)
        details_layout.addLayout(right_details)
        info_layout.addLayout(details_layout)

        layout.addWidget(info_frame)

        # 7日预报卡片 (可滚动)
        scroll_area = NaturalScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("card")

        forecast_container = QWidget()
        forecast_container.setObjectName("forecast_container")
        self.forecast_layout = QVBoxLayout(forecast_container)
        self.forecast_layout.setContentsMargins(15, 15, 15, 15)
        scroll_area.setWidget(forecast_container)

        layout.addWidget(scroll_area)
        self.scroll_area = scroll_area

        # 阴影效果
        for frame in [input_frame, info_frame, self.scroll_area]:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 5)
            frame.setGraphicsEffect(shadow)

        # 应用初始主题
        self.apply_theme()

        self.city_input.returnPressed.connect(self.get_weather)

        self.search_button.setDefault(True)
        self.search_button.setAutoDefault(True)

        # 默认城市
        self.city_input.setText("北京")
        self.weather_icon.clear()

        # 和风天气 API Key
        self.api_key = "ad81c73681034007ae896b4d9d32cf17"

        # 历史记录文件
        self.history_file = "history.json"
        self.load_history()

    def apply_theme(self):
        """应用当前主题的颜色方案"""
        # 创建渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())

        if self.is_dark_mode:
            # 深色模式渐变背景
            gradient.setColorAt(0, QColor(30, 30, 50))  # 顶部深蓝灰色
            gradient.setColorAt(1, QColor(15, 15, 35))  # 底部更深蓝灰色

            # 设置调色板
            palette = QPalette()
            palette.setBrush(QPalette.Window, gradient)
            palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))
            palette.setColor(QPalette.ToolTipText, QColor(240, 240, 240))
            palette.setColor(QPalette.Text, QColor(240, 240, 240))
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, QColor(240, 240, 240))
        else:
            # 浅色模式渐变背景
            gradient.setColorAt(0, QColor(135, 206, 250))  # 顶部天蓝色
            gradient.setColorAt(1, QColor(70, 130, 180))  # 底部钢蓝色

            # 设置调色板
            palette = QPalette()
            palette.setBrush(QPalette.Window, gradient)
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(240, 240, 240))
            palette.setColor(QPalette.AlternateBase, QColor(233, 231, 227))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(0, 0, 255))
            palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
            palette.setColor(QPalette.HighlightedText, Qt.white)

        self.setPalette(palette)
        self.update_stylesheet()

    def update_stylesheet(self):
        """更新样式表以匹配当前主题"""
        if self.is_dark_mode:
            stylesheet = """
                #title_label {
                    color: white;
                    font-size: 20pt;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
                }
                #card {
                    background: rgba(60, 60, 80, 0.85);
                    border-radius: 15px;
                    border: 1px solid #444;
                }
                #forecast_container {
                    background: rgba(60, 60, 80, 0.85);
                    border-radius: 15px;
                }
                QLabel {
                    font-size: 14px;
                    color: white;
                }
                #city_input {
                    padding: 8px;
                    border: 2px solid #555;
                    border-radius: 10px;
                    background: #333;
                    color: white;
                }
                #city_input:focus {
                    border: 2px solid #5D8AA8;
                }
                #search_button {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #5D8AA8, stop:1 #2F4F4F);
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    border: 1px solid #444;
                    font-weight: bold;
                }
                #search_button:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #6A9EC9, stop:1 #3A5F5F);
                }
                #search_button:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #4C6F8A, stop:1 #253737);
                }
                #history_box {
                    padding: 6px;
                    border-radius: 8px;
                    background: #333;
                    color: white;
                    border: 1px solid #555;
                }
                #theme_button {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #5D8AA8, stop:1 #2F4F4F);
                    color: white;
                    border-radius: 20px;
                    padding: 8px 16px;
                    border: 2px solid #87CEFA;
                    font-weight: bold;
                }
                #theme_button:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #6A9EC9, stop:1 #3A5F5F);
                }
                #theme_button:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #4C6F8A, stop:1 #253737);
                }
                QScrollBar:vertical {
                    border: none;
                    background: #444;
                    width: 10px;
                    margin: 0px 0px 0px 0px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical {
                    background: #666;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #888;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """
        else:
            stylesheet = """
                #title_label {
                    color: white;
                    font-size: 20pt;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                }
                #card {
                    background: rgba(255, 255, 255, 0.85);
                    border-radius: 15px;
                    border: 1px solid #DDD;
                }
                #forecast_container {
                    background: rgba(255, 255, 255, 0.85);
                    border-radius: 15px;
                }
                QLabel {
                    font-size: 14px;
                    color: black;
                }
                #city_input {
                    padding: 8px;
                    border: 2px solid #87CEEB;
                    border-radius: 10px;
                    background: white;
                }
                #city_input:focus {
                    border: 2px solid #1E90FF;
                }
                #search_button {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #1E90FF, stop:1 #104E8B);
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    border: 1px solid #87CEEB;
                    font-weight: bold;
                }
                #search_button:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #3CB0FD, stop:1 #1874CD);
                }
                #search_button:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #104E8B, stop:1 #0D3C6E);
                }
                #history_box {
                    padding: 6px;
                    border-radius: 8px;
                    border: 1px solid #87CEEB;
                }
                #theme_button {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #1E90FF, stop:1 #104E8B);
                    color: white;
                    border-radius: 20px;
                    padding: 8px 16px;
                    border: 2px solid #87CEFA;
                    font-weight: bold;
                }
                #theme_button:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #3CB0FD, stop:1 #1874CD);
                }
                #theme_button:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #104E8B, stop:1 #0D3C6E);
                }
                QScrollBar:vertical {
                    border: none;
                    background: #f0f0f0;
                    width: 10px;
                    margin: 0px 0px 0px 0px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical {
                    background: #4682B4;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #1E90FF;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """

        self.setStyleSheet(stylesheet)

    def toggle_theme(self):
        """切换浅色/深色模式"""
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

        # 更新按钮文本
        if self.is_dark_mode:
            self.theme_button.setText("☀️ 切换到浅色模式")
        else:
            self.theme_button.setText("🌙 切换到深色模式")

    # ---------------- 历史记录 ----------------
    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    cities = json.load(f)
                    for city in cities:
                        self.history_box.addItem(city)
            except:
                pass

    def save_history(self):
        cities = [self.history_box.itemText(i) for i in range(self.history_box.count())]
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(cities, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("保存历史失败:", e)

    def update_history(self, city_name):
        if city_name and self.history_box.findText(city_name) == -1:
            self.history_box.addItem(city_name)
            if self.history_box.count() > 10:
                self.history_box.removeItem(0)
        self.save_history()

    def select_history_city(self, index):
        if index >= 0:
            city = self.history_box.itemText(index)
            if city:
                self.city_input.setText(city)
                self.get_weather()

    def closeEvent(self, event):
        self.save_history()
        super().closeEvent(event)

    # ---------------- 天气查询 ----------------
    def get_weather(self):
        city = self.city_input.text().strip()
        if not city:
            QMessageBox.warning(self, "警告", "请输入城市名称!")
            return

        self.weather_icon.setText("加载中...")
        self.city_label.setText(f"城市: {city}")
        self.temperature_label.setText("--°C")
        self.weather_label.setText("天气状况: 查询中...")
        self.humidity_label.setText("湿度: --")
        self.wind_label.setText("风速: --")
        self.pressure_label.setText("气压: --")
        self.visibility_label.setText("能见度: --")

        QApplication.processEvents()

        try:
            location_url = f"https://geoapi.qweather.com/v2/city/lookup?location={city}&key={self.api_key}"
            location_data = requests.get(location_url, timeout=10).json()

            if location_data["code"] == "200" and location_data.get("location"):
                location_id = location_data["location"][0]["id"]
                city_name = location_data["location"][0]["name"]

                self.update_history(city_name)

                weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={self.api_key}"
                weather_data = requests.get(weather_url, timeout=10).json()

                if weather_data["code"] == "200":
                    now = weather_data["now"]
                    temp = now["temp"]
                    humidity = now["humidity"]
                    weather_desc = now["text"]
                    wind_speed = now["windSpeed"]
                    wind_scale = now["windScale"]
                    pressure = now["pressure"]
                    vis = now["vis"]
                    icon_code = now["icon"]

                    self.city_label.setText(f"城市: {city_name}")
                    self.temperature_label.setText(f"{temp}°C")
                    self.weather_label.setText(f"{weather_desc}")
                    self.humidity_label.setText(f"湿度: {humidity}%")
                    self.wind_label.setText(f"风速: {wind_speed}km/h ({wind_scale}级)")
                    self.pressure_label.setText(f"气压: {pressure}hPa")
                    self.visibility_label.setText(f"能见度: {vis}公里")

                    # 图标
                    icon_url = f"https://a.hecdn.net/img/common/icon/202106d/{icon_code}.png"
                    icon_resp = requests.get(icon_url, timeout=10)
                    if icon_resp.status_code == 200:
                        pixmap = QPixmap()
                        pixmap.loadFromData(icon_resp.content)
                        self.weather_icon.setPixmap(
                            pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                        self.weather_icon.setText("❓")

                self.get_forecast(location_id)
            else:
                QMessageBox.critical(self, "错误", f"找不到城市: {city}")
                self.weather_icon.setText("🏙️")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生异常: {str(e)}")
            self.weather_icon.setText("❌")

    # ---------------- 七日预报 ----------------
    def get_forecast(self, location_id):
        forecast_url = f"https://devapi.qweather.com/v7/weather/7d?location={location_id}&key={self.api_key}"
        data = requests.get(forecast_url, timeout=10).json()

        # 清空旧的预报信息
        while self.forecast_layout.count():
            child = self.forecast_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if data["code"] == "200":
            title = QLabel("未来7日预报")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("font-size:14pt; font-weight:bold;")
            self.forecast_layout.addWidget(title)

            week_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

            temps = [(int(d["tempMin"]), int(d["tempMax"])) for d in data["daily"]]
            min_all = min(t[0] for t in temps)
            max_all = max(t[1] for t in temps)
            span = max_all - min_all if max_all != min_all else 1

            for i, day in enumerate(data["daily"]):
                fxDate = day["fxDate"]
                date_obj = datetime.datetime.strptime(fxDate, "%Y-%m-%d")
                weekday = week_map[date_obj.weekday()]
                if i == 0:
                    weekday = "今天"

                temp_min = int(day["tempMin"])
                temp_max = int(day["tempMax"])
                icon_code = day["iconDay"]

                row = QHBoxLayout()

                # 日期（横向显示，避免换行挤占空间）
                date_label = QLabel(f"{weekday} {date_obj.month}/{date_obj.day}")
                date_label.setFixedWidth(90)
                row.addWidget(date_label)

                # 天气图标
                icon_label = QLabel()
                icon_label.setFixedSize(40, 40)
                icon_url = f"https://a.hecdn.net/img/common/icon/202106d/{icon_code}.png"
                try:
                    icon_resp = requests.get(icon_url, timeout=5)
                    if icon_resp.status_code == 200:
                        pixmap = QPixmap()
                        pixmap.loadFromData(icon_resp.content)
                        icon_label.setPixmap(
                            pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                except:
                    icon_label.setText("❓")
                row.addWidget(icon_label)

                # 温度条（自适应宽度）
                max_width = 150
                scaled_min = int(((temp_min - min_all) / span) * max_width)
                scaled_max = int(((temp_max - min_all) / span) * max_width)

                temp_layout = QHBoxLayout()
                max_label = QLabel(f"{temp_max}°")
                max_label.setStyleSheet("color:red; font-size:10pt;")
                min_label = QLabel(f"{temp_min}°")
                min_label.setStyleSheet("color:blue; font-size:10pt;")

                bar = QFrame()
                bar.setFixedHeight(6)
                bar.setFixedWidth(max(20, scaled_max - scaled_min))
                bar.setStyleSheet(
                    "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 red, stop:1 blue);"
                )

                temp_layout.addWidget(max_label)
                temp_layout.addWidget(bar)
                temp_layout.addWidget(min_label)

                row.addLayout(temp_layout)
                row.addStretch()

                row_widget = QWidget()
                row_widget.setLayout(row)
                row_widget.setFixedHeight(60)  # ✅ 固定高度，避免文字挤压
                self.forecast_layout.addWidget(row_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    weather_app = WeatherApp()
    weather_app.show()
    sys.exit(app.exec())