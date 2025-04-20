import sys
import os
import requests
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QWidget, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, Qt
from plyer import notification
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# مسیر API
API_URL = "https://BrsApi.ir/Api/Market/Gold_Currency.php?key=FreedrDvAEq7OzdTAnANEYby04DiO5dk"

headers = {

        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/106.0.0.0",

        "Accept": "application/json, text/plain, */*"

    }
response = requests.get(API_URL, headers=headers)

if response.status_code == 200:

   print(response.text)

else:

        print(f"Error: {response.status_code}")
# تنظیم مسیر آیکون
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, "icon.ico")


# ایجاد دیتابیس و جدول فقط در بار اول
def create_db():
    conn = sqlite3.connect('market_prices.db')  # فایل دیتابیس محلی
    cursor = conn.cursor()

    # ایجاد جدول قیمت‌ها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS GoldMarketPrices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        gold_price REAL NOT NULL,
        coin_price REAL NOT NULL,
        dollar_price REAL NOT NULL,
        euro_price REAL NOT NULL
    )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

# ذخیره قیمت‌ها در دیتابیس
def save_prices_to_db(gold_price, coin_price, dollar_price, euro_price):
    conn = sqlite3.connect('market_prices.db')
    cursor = conn.cursor()

    # ذخیره قیمت‌ها در دیتابیس
    cursor.execute('''
    INSERT INTO GoldMarketPrices (date, gold_price, coin_price, dollar_price, euro_price)
    VALUES (?, ?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), gold_price, coin_price, dollar_price, euro_price))

    conn.commit()
    cursor.close()
    conn.close()

# بازیابی داده‌ها از دیتابیس
def fetch_prices_from_db():
    conn = sqlite3.connect('market_prices.db')
    cursor = conn.cursor()

    # بازیابی داده‌ها از جدول
    cursor.execute('SELECT date, gold_price, coin_price, dollar_price, euro_price FROM GoldMarketPrices ORDER BY date DESC LIMIT 100')
    rows = cursor.fetchall()

    conn.close()

    # استخراج داده‌ها برای نمودار
    dates = [row[0] for row in rows]
    gold_prices = [row[1] for row in rows]
    coin_prices = [row[2] for row in rows]
    dollar_prices = [row[3] for row in rows]
    euro_prices = [row[4] for row in rows]

    return dates, gold_prices, coin_prices, dollar_prices, euro_prices

# کلاس اصلی برنامه
class GoldMarketApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # تنظیم آیکون و عنوان پنجره
        self.setWindowTitle("برنامه بررسی قیمت طلا و سکه")
        self.setGeometry(300, 300, 800, 600)

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.init_ui()
        self.init_tray()

        # تنظیم تایمر برای بررسی قیمت‌ها
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_market)
        self.timer.start(600000)  # هر ۱۰ دقیقه (۶۰۰۰۰۰ میلی‌ثانیه)

        # دریافت اولیه اطلاعات بازار
        self.check_market()

    def init_ui(self):
        """ایجاد رابط کاربری"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()

        self.gold_price_label = QLabel("طلای 18 عیار: در حال دریافت ...")
        self.coin_price_label = QLabel("سکه امامی: در حال دریافت ...")
        self.euro_price_label = QLabel("یورو: در حال دریافت ...")
        self.dollar_price_label = QLabel("دلار: در حال دریافت ...")
        self.coin_to_gold_ratio_label = QLabel("نسبت قیمت سکه به طلا: در حال محاسبه ...")
        self.purchase_suggestion_label = QLabel("پیشنهاد: در حال محاسبه ...")

        for label in [self.gold_price_label, self.coin_price_label, self.euro_price_label, self.dollar_price_label,
                      self.coin_to_gold_ratio_label, self.purchase_suggestion_label]:
            self.layout.addWidget(label)

        self.refresh_button = QPushButton("به‌روزرسانی")
        self.refresh_button.clicked.connect(self.check_market)
        self.layout.addWidget(self.refresh_button)

        self.close_button = QPushButton("بستن")
        self.close_button.clicked.connect(self.close_app)
        self.layout.addWidget(self.close_button)

        # افزودن نمودار به پنجره
        self.chart_canvas = FigureCanvas(plt.figure(figsize=(6, 4)))
        self.layout.addWidget(self.chart_canvas)

        self.central_widget.setLayout(self.layout)

    def init_tray(self):
        """تنظیم System Tray"""
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))

        self.tray_icon.setVisible(True)
        tray_menu = QMenu()

        show_action = QAction("نمایش", self)
        show_action.triggered.connect(self.restore_window)
        tray_menu.addAction(show_action)

        quit_action = QAction("خروج", self)
        quit_action.triggered.connect(self.close_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.showMessage("برنامه فعال شد", "برنامه بررسی قیمت طلا و سکه در پس‌زمینه اجرا می‌شود.")

    def check_market(self):
        """دریافت قیمت‌ها از API و به‌روزرسانی رابط کاربری"""
        data = self.fetch_prices()

        if not data:
            self.send_notification("خطا", "عدم دریافت داده از API")
            return

        try:
            gold_price = next((item["price"] for item in data.get("gold", []) if item["name"] == "طلای 18 عیار"), 0)
            coin_price = next((item["price"] for item in data.get("gold", []) if item["name"] == "سکه امامی"), 0)
            dollar_price = next((item["price"] for item in data.get("currency", []) if item["name"] == "دلار"), 0)
            euro_price = next((item["price"] for item in data.get("currency", []) if item["name"] == "يورو"), 0)

            # ذخیره قیمت‌ها در دیتابیس
            save_prices_to_db(gold_price, coin_price, dollar_price, euro_price)

            # به‌روزرسانی برچسب‌ها
            self.gold_price_label.setText(f"طلای 18 عیار: {gold_price:,} تومان")
            self.coin_price_label.setText(f"سکه امامی: {coin_price:,} تومان")
            self.dollar_price_label.setText(f"دلار: {dollar_price:,} تومان")
            self.euro_price_label.setText(f"یورو: {euro_price:,} تومان")

            self.suggest_purchase(gold_price, coin_price)

            # به‌روزرسانی نمودار
            self.update_chart()

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
            return {}

    def send_notification(self, title, message):
        """ارسال نوتیفیکیشن"""
        notification.notify(
            title=title or "اطلاع‌رسانی قیمت طلا",
            message=message,
            timeout=10,
            app_icon=icon_path if os.path.exists(icon_path) else None
        )

    def suggest_purchase(self, gold_price, coin_price):
        """پیشنهاد خرید یا فروش"""
        if gold_price == 0:
            return

        coin_to_gold_ratio = coin_price / gold_price
        self.coin_to_gold_ratio_label.setText(f"نسبت قیمت سکه به طلا: {coin_to_gold_ratio:.2f}")

        middle_ratio = 10.45
        tolerance = 0.75

        if coin_to_gold_ratio < middle_ratio - tolerance:
            self.purchase_suggestion_label.setText("پیشنهاد تبدیل طلا به سکه: حباب سکه کم است.")
            self.send_notification("پیشنهاد تبدیل طلا به سکه", "حباب سکه کم است.")
        elif coin_to_gold_ratio > middle_ratio + tolerance:
            self.purchase_suggestion_label.setText("پیشنهاد تبدیل سکه به طلا: حباب سکه زیاد است.")
            self.send_notification("پیشنهاد تبدیل سکه به طلا", "حباب سکه زیاد است.")
        else:
            self.purchase_suggestion_label.setText("پیشنهاد: نگهداری موجودی طلا و سکه.")
            self.send_notification("پیشنهاد نگهداری موجودی", "حباب سکه مناسب است.")

    def update_chart(self):
        """بروزرسانی نمودار قیمت‌ها"""
        dates, gold_prices, coin_prices, dollar_prices, euro_prices = fetch_prices_from_db()

        if not dates:
            return

        plt.clf()  # پاک کردن نمودار قبلی

        # رسم قیمت‌ها
        plt.plot(dates, gold_prices, color='yellow', label="Gold")
        plt.plot(dates, coin_prices, color='red', label="Coin")
        plt.plot(dates, dollar_prices, color='green', label="Dolar")
        plt.plot(dates, euro_prices, color='blue', label="Euro")

        # تنظیمات نمودار
        plt.xticks(rotation=45, ha="right")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.title("Price Chart")
        plt.legend()

        self.chart_canvas.draw()

    def restore_window(self):
        self.show()
        self.setWindowState(Qt.WindowActive)

    def close_app(self):
        self.tray_icon.hide()
        QApplication.quit()

# اجرای برنامه
if __name__ == "__main__":
    create_db()  # ایجاد دیتابیس در صورت نیاز

    app = QApplication(sys.argv)
    window = GoldMarketApp()
    window.show()
    sys.exit(app.exec_())
