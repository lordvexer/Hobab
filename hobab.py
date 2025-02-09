import sys
import os
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QWidget, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer
from plyer import notification
from PyQt5.QtCore import Qt

# API URL
API_URL = "https://brsapi.ir/FreeTsetmcBourseApi/Api_Free_Gold_Currency_v2.json"

current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, "icon.ico")
if not os.path.exists(icon_path):
    print("آیکون وجود ندارد.")
else:
    print("آیکون پیدا شد.")

class GoldMarketApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # تنظیم آیکون پنجره اصلی
        self.setWindowTitle("برنامه بررسی قیمت طلا و سکه")
        self.setGeometry(300, 300, 400, 400)  # اندازه پنجره تغییر کرد

        # بررسی و تنظیم آیکون
        if not os.path.exists(icon_path):
            print("آیکون وجود ندارد.")
        else:
            self.setWindowIcon(QIcon(icon_path))

        # تنظیمات اولیه GUI
        self.init_ui()

        # تنظیم System Tray
        self.init_tray()

        # تایمر برای بررسی خودکار
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_market)
        self.timer.start(9000000)  # چک کردن قیمت‌ها هر 9000000 میلی‌ثانیه (2.5 ساعت)

        # اولین بار چک کردن قیمت‌ها
        self.check_market()



    def init_ui(self):
        """ایجاد رابط کاربری"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # طرح‌بندی
        self.layout = QVBoxLayout()

        # نمایش قیمت‌ها
        self.gold_price_label = QLabel("طلای 18 عیار: در حال دریافت ...")
        self.coin_price_label = QLabel("سکه امامی: در حال دریافت ...")
        self.euro_price_label = QLabel("یورو: در حال دریافت ...")
        self.dollar_price_label = QLabel("دلار: در حال دریافت ...")
        self.layout.addWidget(self.gold_price_label)
        self.layout.addWidget(self.coin_price_label)
        self.layout.addWidget(self.euro_price_label)
        self.layout.addWidget(self.dollar_price_label)

        # نمایش نسبت قیمت سکه به طلا
        self.coin_to_gold_ratio_label = QLabel("نسبت قیمت سکه به طلا: در حال محاسبه ...")
        self.layout.addWidget(self.coin_to_gold_ratio_label)

        # نمایش پیشنهاد خرید یا فروش
        self.purchase_suggestion_label = QLabel("پیشنهاد: در حال محاسبه ...")
        self.layout.addWidget(self.purchase_suggestion_label)

        # دکمه به‌روزرسانی
        self.refresh_button = QPushButton("به‌روزرسانی")
        self.refresh_button.clicked.connect(self.check_market)
        self.layout.addWidget(self.refresh_button)

        # دکمه بستن
        self.close_button = QPushButton("بستن")
        self.close_button.clicked.connect(self.close_app)
        self.layout.addWidget(self.close_button)

        self.central_widget.setLayout(self.layout)

    def init_tray(self):
        """تنظیمات System Tray"""
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))  # آیکون را تنظیم کنید
        self.tray_icon.setVisible(True)

        # منوی System Tray
        tray_menu = QMenu()
        show_action = QAction("نمایش")
        show_action.triggered.connect(self.restore_window)
        tray_menu.addAction(show_action)

        quit_action = QAction("خروج")
        quit_action.triggered.connect(self.close_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # نمایش نوتیفیکیشن اولیه
        self.tray_icon.showMessage("برنامه فعال شد", "برنامه بررسی قیمت طلا و سکه در پس‌زمینه اجرا می‌شود.")

    def check_market(self):
        """دریافت قیمت‌ها از API و به‌روزرسانی رابط کاربری با مدیریت خطا"""
        data = self.fetch_prices()

        if not data:
            self.send_notification("خطا", "عدم دریافت داده از API")
            return

        try:
            gold_price = next((item["price"] for item in data.get("gold", []) if item["name"] == "طلای 18 عیار"), None)
            coin_price = next((item["price"] for item in data.get("gold", []) if item["name"] == "سکه امامی"), None)
            dollar_price = next((item["price"] for item in data.get("currency", []) if item["name"] == "دلار"), None)
            euro_price = next((item["price"] for item in data.get("currency", []) if item["name"] == "يورو"), None)

            # بررسی مقدار None برای جلوگیری از خطا
            if None in (gold_price, coin_price, dollar_price, euro_price):
                self.send_notification("خطا", "برخی از قیمت‌ها دریافت نشدند!")
                return

            # به‌روزرسانی برچسب‌ها
            self.gold_price_label.setText(f"طلای 18 عیار: {gold_price:,} تومان")
            self.coin_price_label.setText(f"سکه امامی: {coin_price:,} تومان")
            self.dollar_price_label.setText(f"دلار: {dollar_price:,} تومان")
            self.euro_price_label.setText(f"يورو: {euro_price:,} تومان")

            # پیشنهاد خرید یا فروش بر اساس نسبت قیمت سکه به طلا
            self.suggest_purchase(gold_price, coin_price)

            # ارسال نوتیفیکیشن شامل قیمت دلار و یورو
            self.send_notification(
                "به‌روزرسانی قیمت‌ها",
                f"طلای 18 عیار: {gold_price:,} تومان\n"
                f"سکه امامی: {coin_price:,} تومان\n"
                f"دلار: {dollar_price:,} تومان\n"
                f"یورو: {euro_price:,} تومان"
            )

        except Exception as e:
            self.send_notification("خطا", f"مشکلی پیش آمد: {str(e)}")

    def fetch_prices(self):
        """دریافت قیمت‌ها از API"""
        try:
            response = requests.get(API_URL, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت داده‌ها: {e}")
            return None


    def send_notification(self, title, message):
        """ارسال نوتیفیکیشن"""
        notification.notify(
            title=title if title else "اطلاع‌رسانی قیمت طلا",
            message=message,
            timeout=10,  # مدت زمان نوتیفیکیشن
            app_icon=icon_path  # آیکون نوتیفیکیشن
        )

    def suggest_purchase(self, gold_price, coin_price):
        """پیشنهاد خرید یا فروش"""
        coin_to_gold_ratio = coin_price / gold_price
        self.coin_to_gold_ratio_label.setText(f"نسبت قیمت سکه به طلا: {coin_to_gold_ratio:.2f}")

        middle_ratio = 10.45
        tolerance = 0.75  # تلورانس

        if coin_to_gold_ratio < middle_ratio - tolerance:  # حباب کم است
            self.purchase_suggestion_label.setText("پیشنهاد تبدیل طلا به سکه: حباب سکه کم است.")
            self.send_notification("پیشنهاد تبدیل طلا به سکه", "حباب سکه کم است، پیشنهاد تبدیل طلا به سکه.")
        elif coin_to_gold_ratio > middle_ratio + tolerance:  # حباب زیاد است
            self.purchase_suggestion_label.setText("پیشنهاد تبدیل سکه به طلا: حباب سکه زیاد است.")
            self.send_notification("پیشنهاد تبدیل سکه به طلا", "حباب سکه زیاد است، پیشنهاد تبدیل سکه به طلا.")
        else:
            self.purchase_suggestion_label.setText("پیشنهاد: هیچ پیشنهاد خاصی در حال حاضر وجود ندارد.")

    def close_app(self):
        """خروج از برنامه"""
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """مدیریت بسته شدن پنجره و انتقال به System Tray"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "برنامه در پس‌زمینه اجرا می‌شود",
            "برای بازگرداندن برنامه، روی آیکون در System Tray کلیک کنید.",
            QSystemTrayIcon.Information,
            3000
        )


    def restore_window(self):
        """بازگرداندن پنجره از System Tray"""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()

# اجرای برنامه
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # برنامه با بستن پنجره اصلی بسته نشود

    window = GoldMarketApp()
    window.show()

    sys.exit(app.exec_())
