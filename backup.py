import telebot
import os
import datetime

# ===== تنظیمات =====
BOT_TOKEN = "8302271488:AAG3wD2ZUNv7ajQsYyuCd1HjOfyI858caME"  # ← توکن ربات از BotFather
CHAT_ID = 5013103880            # ← chat_id عددی خودت
FILE_PATH = "/var/www/bot/users.db"

bot = telebot.TeleBot(BOT_TOKEN)

def send_file():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "rb") as f:
            bot.send_document(CHAT_ID, f, caption=f"📦 فایل users.db - {datetime.date.today()}")
        print("✅ فایل ارسال شد.")
    else:
        bot.send_message(CHAT_ID, "❌ فایل users.db پیدا نشد.")
        print("⚠ فایل یافت نشد.")

if __name__ == "__main__":
    send_file()
