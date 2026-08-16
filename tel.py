import threading
import requests
import sqlite3
import os
import json
from uuid import uuid4
import random
import string
import qrcode
from io import BytesIO
import time as time_module
import time
import math
from telebot import TeleBot, types
import telebot
import urllib.parse
import re
list_inbound='panel/api/inbounds/list'
# --- توکن API ربات و آیدی‌های مدیران ---
login_url =  'login'
data = {
    'username': 'admin',
    'password': 'admin'
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}
API_TOKEN = "8872814549:AAHpFjlg-5sX_QuQMv3p9gFp60wl3vylKdw" # توکن API خود را اینجا قرار دهید
special_user_ids = [7309976768,5013103880]  # آیدی‌های عددی مجاز برای مدیریت (تغییر دهید)
bot = telebot.TeleBot(API_TOKEN)
# --- پایان توکن و آیدی‌ها ---

# نگاشت نوع کانفیگ به نام فارسی برای نمایش بهتر
CONFIG_TYPE_NAMES = {
    "volume_config": "کانفیگ حجمی",
    "unlimited_volume_config": "کانفیگ حجمی بدون تاریخ",
    "unlimited_config_one": "کانفیگ نامحدود تک کاربر",
    "unlimited_config_two": "کانفیگ نامحدود دو کاربر",
    "meli_config": "کانفیگ نت ملی"
}

# کلیدهای مربوط به قیمت ها در جدول bot_config (برای قیمت‌های عمومی)
GENERAL_PRICE_KEYS = {
    "volume_config_price": "کانفیگ حجمی",
    "unlimited_volume_config_price": "کانفیگ حجمی بدون تاریخ",
    "unlimited_config_one_price": "کانفیگ نامحدود تک کاربر",
    "unlimited_config_two_price": "کانفیگ نامحدود دو کاربر",
    "meli_config_price": "کانفیگ نت ملی",
    
}


def get_db_connection():
    """یک اتصال جدید به دیتابیس باز می‌کند و آن را برمی‌گرداند."""
    return sqlite3.connect('users.db')

def get_bot_status():
    """وضعیت فعلی ربات (ON/OFF) را برمی‌گرداند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT config_value FROM bot_config WHERE config_key = ?", ('bot_status',))
        result = c.fetchone()
        return result[0] if result else 'ON'
    finally:
        conn.close()

def set_bot_status(status):
    """وضعیت ربات را تنظیم می‌کند (ON/OFF)."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO bot_config (config_key, config_value) VALUES (?, ?)",
                  ('bot_status', status))
        conn.commit()
    finally:
        conn.close()

def random_string(length):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))









def get_panel_stats(row,panel_id):
    """وضعیت فعلی تانل پنل مشخص را برمی‌گرداند (ON/OFF)."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(f"SELECT {row} FROM panels WHERE id = ?", (panel_id,))
        result = c.fetchone()
        return result[0]
    finally:
        conn.close()











def change_capacity(panel_id, capacity):
    """وضعیت تانل پنل مشخص را تنظیم می‌کند (ON/OFF)."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE panels SET capacity = ? WHERE id = ?",
            (capacity, panel_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()





def change_subscription(panel_id, subscription_link):
    """وضعیت تانل پنل مشخص را تنظیم می‌کند (ON/OFF)."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE panels SET subscription_link = ? WHERE id = ?",
            (subscription_link, panel_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()





def get_config_value(key):
    """یک مقدار پیکربندی را از جدول bot_config (قیمت‌های عمومی) برمی‌گرداند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT config_value FROM bot_config WHERE config_key = ?", (key,))
        result = c.fetchone()
        return result[0] if result else '0' # اگر مقداری یافت نشد، '0' برگردانده شود
    finally:
        conn.close()

def set_config_value(key, value):
    """یک مقدار پیکربندی را در جدول bot_config (قیمت‌های عمومی) تنظیم می‌کند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO bot_config (config_key, config_value) VALUES (?, ?)",
                  (key, str(value)))
        conn.commit()
    finally:
        conn.close()

# --- توابع جدید/اصلاح شده برای قیمت‌های اختصاصی در جدول users ---
def get_user_specific_price(user_id, config_column_name):
    """قیمت اختصاصی یک نوع کانفیگ را برای یک کاربر خاص از جدول **users** برمی‌گرداند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # حالا از جدول users قیمت‌ها را می‌خوانیم
        c.execute(f"SELECT {config_column_name} FROM users WHERE username = ?", (str(user_id),))
        result = c.fetchone()
        return result[0] if result and result[0] is not None else 0
    except sqlite3.Error as e:
        print(f"Error retrieving user specific price for {user_id}, column {config_column_name} from users table: {e}")
        return 0
    finally:
        conn.close()

def get_all_user_prices_from_user_table(user_id):
    """تمام قیمت‌های اختصاصی کاربر را از جدول **users** برمی‌گرداند."""
    conn = get_db_connection()
    c = conn.cursor()
    prices_dict = {}
    try:
        # حالا از جدول users قیمت‌ها را می‌خوانیم
        c.execute("SELECT volume_config_price, unlimited_volume_config_price, unlimited_config_one_price,unlimited_config_two_price,meli_config_price FROM users WHERE username = ?", (str(user_id),))
        result = c.fetchone()
        
        if result:
            prices_dict['volume_config'] = result[0] if result[0] is not None else 0
            prices_dict['unlimited_volume_config'] = result[1] if result[1] is not None else 0
            prices_dict['unlimited_config_one'] = result[2] if result[2] is not None else 0
            prices_dict['unlimited_config_two'] = result[3] if result[3] is not None else 0
            prices_dict['meli_config'] = result[4] if result[4] is not None else 0
    except sqlite3.Error as e:
        print(f"Error getting all user prices for {user_id} from users table: {e}")
    finally:
        conn.close()
    return prices_dict



def reset_user_balance(user_id_str):
    """Resets a user's balance to zero in the database.

    Args:
        user_id_str (str): The Telegram user ID as a string.

    Returns:
        bool: True if the balance was successfully reset (i.e., user found and updated), False otherwise.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET balance = 0 WHERE username = ?", (user_id_str,))
        conn.commit()
        return c.rowcount > 0  # Returns True if a row was updated
    except Exception as e:
        print(f"Error resetting user balance: {e}")
        return False
    finally:
        conn.close()



def build_panel_keyboard(panel_id: int, new_status: str,tunnel_type,cdn_status=None) -> types.InlineKeyboardMarkup:
    """
    یک کیبورد برای پنل می‌سازد با دکمه‌های مدیریت پنل و فعال/غیرفعال کردن تانل.
    
    :param panel_id: شناسه پنل
    :param new_status: وضعیت تانل فعلی ('ON' یا 'OFF')
    :return: InlineKeyboardMarkup آماده برای استفاده
    """
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("تغییر ظرفیت پنل", callback_data=f"capacity_panel_{panel_id}"))
    keyboard.add(types.InlineKeyboardButton("تغییر لینک سابسکریپشن", callback_data=f"sublink_panel_{panel_id}"))
    keyboard.add(types.InlineKeyboardButton("❌ حذف این پنل", callback_data=f"delete_panel_{panel_id}"))
    return keyboard





def set_user_specific_price_in_user_table(user_id, config_type, price):
    """
    قیمت اختصاصی یک نوع کانفیگ را برای یک کاربر خاص در جدول **users** تنظیم می‌کند.
    `config_type` باید یکی از مقادیر "volume_config", "unlimited_volume_config", "unlimited_config" باشد.
    """
    conn = None 
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        user_id_str = str(user_id) 
        
        allowed_config_types = ["volume_config", "unlimited_volume_config", "unlimited_config_one","unlimited_config_two","meli_config"]
        if config_type not in allowed_config_types:
            print(f"ERROR: Invalid config_type '{config_type}' provided. Aborting price update.")
            return False

        column_name = f"{config_type}_price" # ساخت نام ستون صحیح (مثلاً volume_config_price)
        
        print(f"DEBUG: Attempting to set price for user {user_id_str}, config_type: {config_type}, column: {column_name}, price: {price}")
        
        # 1. ابتدا بررسی می‌کنیم که کاربر وجود دارد یا خیر
        c.execute("SELECT username FROM users WHERE username = ?", (user_id_str,))
        if c.fetchone() is None:
            print(f"ERROR: User {user_id_str} not found in users table. Cannot set specific price for them.")
            return False 

        # 2. حالا اقدام به بروزرسانی می‌کنیم در جدول users
        # ستون های مربوط به قیمت همیشه باید وجود داشته باشند چون در init_db ساخته می شوند.
        query = f"UPDATE users SET is_friend = 1, {column_name} = ? WHERE username = ?"
        c.execute(query, (price, user_id_str))
        conn.commit()
        
        # 3. بررسی می‌کنیم که آیا ردیفی واقعاً به‌روزرسانی شده است
        if c.rowcount > 0:
            print(f"DEBUG: Successfully updated {column_name} to {price} for user {user_id_str}.")
            return True
        else:
            print(f"WARNING: User {user_id_str} found, but no rows updated for column {column_name}. This should not happen if user exists and column is correct.")
            return False

    except sqlite3.OperationalError as e:
        print(f"SQLITE OPERATIONAL ERROR: {e} for user {user_id_str}. This might indicate a missing column, a locked database, or malformed SQL. Column attempted: {column_name}")
        return False
    except sqlite3.Error as e:
        print(f"SQLITE ERROR: {e} for user {user_id_str}, type {config_type}, column {column_name}. Database specific error.")
        return False
    except Exception as e:
        print(f"GENERAL ERROR in set_user_specific_price_in_user_table for user {user_id_str}: {e}")
        return False
    finally:
        if conn:
            conn.close()
            
def get_user_balance(user_id):
    """Retrieves a user's current balance from the database.

    Args:
        user_id (str): The Telegram user ID as a string.

    Returns:
        int: The user's balance, or 0 if the user is not found.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username = ?", (user_id,))
    balance = c.fetchone()
    conn.close()
    return balance[0] if balance else 0


def get_user_full_name(user_id):
    """Retrieves a user's current balance from the database.

    Args:
        user_id (str): The Telegram user ID as a string.

    Returns:
        int: The user's balance, or 0 if the user is not found.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE username = ?", (user_id,))
    full_name = c.fetchone()
    conn.close()
    return full_name[0]

def get_referral_link(username, bot_username):
    """
    لینک دعوت تلگرام را بر اساس username کاربر می‌سازد.
    
    :param username: یوزرنیم کاربر
    :param bot_username: یوزرنیم ربات بدون @
    :return: لینک دعوت کامل یا None اگر کاربر پیدا نشد
    """
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("SELECT referral_code FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        if row and row[0]:
            referral_code = row[0]
            return f"https://t.me/{bot_username}?start={referral_code}"
        else:
            return None  # کاربر پیدا نشد یا referral_code ندارد
    finally:
        c.close()
        conn.close()





def get_telegram_id(user_id):
    """Retrieves a user's current balance from the database.

    Args:
        user_id (str): The Telegram user ID as a string.

    Returns:
        int: The user's balance, or 0 if the user is not found.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users WHERE username = ?", (user_id,))
    telegram_id = c.fetchone()
    conn.close()
    return telegram_id[0]






def user_exists(user_id):
    """بررسی می‌کند که آیا کاربری با آیدی مشخص در دیتابیس وجود دارد."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT 1 FROM users WHERE username = ?", (str(user_id),))
        result = c.fetchone()
        return result is not None
    finally:
        conn.close()

def add_panel(panel_address, is_unlimited, capacity,subscription_link,panel_type):
    """
    یک پنل جدید را به دیتابیس اضافه می‌کند.
    سپس هر سرویسی که panel_address آن NULL است با آدرس جدید به‌روزرسانی می‌شود.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # اضافه کردن پنل جدید
        c.execute(
            "INSERT INTO panels (panel_address, is_unlimited, capacity,subscription_link,panel_type) VALUES (?, ?,?,?,?,?)",
            (panel_address, is_unlimited, capacity,subscription_link,panel_type)
        )

        # آپدیت جدول services برای رکوردهایی که panel_address آنها NULL است
        c.execute(
            "UPDATE services SET panel = ? WHERE panel IS NULL",
            (panel_address,)
        )

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Error: Panel with address {panel_address} already exists.")
        return False
    except Exception as e:
        print(f"Error adding panel or updating services: {e}")
        return False
    finally:
        conn.close()


def get_all_panels():
    """تمام پنل‌های ثبت شده را از دیتابیس برمی‌گرداند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM panels")
        panels = c.fetchall()
        return panels
    finally:
        conn.close()

def delete_panel_by_id(panel_id):
    """
    یک پنل را بر اساس ID آن حذف می‌کند و جدول services را به‌روزرسانی می‌کند.
    ستون panel_address در جدول services به None تنظیم می‌شود.
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # گرفتن مقدار آدرس پنل قبل از حذف
        c.execute("SELECT panel_address FROM panels WHERE id = ?", (panel_id,))
        row = c.fetchone()
        if not row:
            return False  # پنل وجود ندارد
        panel_address = row[0]

        # حذف پنل
        c.execute("DELETE FROM panels WHERE id = ?", (panel_id,))

        # آپدیت جدول services: قرار دادن None در ستون panel_address
        c.execute("UPDATE services SET panel = NULL WHERE panel = ?", (panel_address,))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting panel or updating services: {e}")
        return False
    finally:
        conn.close()




def show_totals(panel):
    response_data = single_with_retries('get', panel + list_inbound)
    
    if not response_data.get("success"):
        print(f"❌ پنل {panel} موفق به دریافت لیست نشد.")
        return 0

    inbounds = response_data.get("obj", [])
    total_clients = 0
    for inbound in inbounds:
        settings = json.loads(inbound.get('settings', '{}'))
        clients_settings = settings.get('clients', [])
        total_clients += len(clients_settings)

    return total_clients



def is_user_blocked(user_id):
    """بررسی می‌کند که آیا کاربر بلاک شده است یا خیر."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT is_blocked FROM users WHERE username = ?", (str(user_id),))
        result = c.fetchone()
        return result[0] == 1 if result else False
    finally:
        conn.close()

def block_user(username):
    """یک کاربر را بلاک می‌کند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if c.fetchone() is None:
            print(f"User {username} not found for blocking.")
            return False

        c.execute("UPDATE users SET is_blocked = 1 WHERE username = ?", (username,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in blocking user {username}: {e}")
        return False
    finally:
        conn.close()

def unblock_user(username):
    """یک کاربر را از حالت بلاک خارج می‌کند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET is_blocked = 0 WHERE username = ?", (username,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in unblocking user {username}: {e}")
        return False
    finally:
        conn.close()

def get_blocked_users():
    """لیست آیدی کاربران بلاک شده را برمی‌گرداند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT username FROM users WHERE is_blocked = 1")
        result = c.fetchall()
        return [row[0] for row in result]
    finally:
        conn.close()

def show_blocked_users(message):
    """لیست کاربران بلاک شده را به مدیر نمایش می‌دهد."""
    blocked_users = get_blocked_users()

    if not blocked_users:
        bot.send_message(
            message.chat.id,
            "هیچ کاربری بلاک نشده است."
        )
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for user_id in blocked_users:
        keyboard.add(
            types.InlineKeyboardButton(f"آنبلاک کاربر {user_id}", callback_data=f"unblock_{user_id}")
        )

    bot.send_message(
        message.chat.id,
        "لیست کاربران بلاک‌شده:",
        reply_markup=keyboard
    )
def add_user(username, full_name, telegram_id,referral_code,balance=0):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT full_name, telegram_id,referral_code FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            old_full_name = row[0]
            old_telegram_id = row[1]
            referral_code = row[2]
            
            # آپدیت full_name در صورت تفاوت
            if str(old_full_name) != str(full_name):
                c.execute("UPDATE users SET full_name = ? WHERE username = ?", (str(full_name), username))
                conn.commit()
                print(f"Updated full_name in users table for user {username}.")
            
            # آپدیت telegram_id در صورت تفاوت
            if str(old_telegram_id) != str(telegram_id):
                c.execute("UPDATE users SET telegram_id = ? WHERE username = ?", (str(telegram_id), username))
                conn.commit()
                print(f"Updated Telegram ID in users table for user {username}.")
                
                c.execute("UPDATE services SET telegram_id = ? WHERE username = ?", (str(telegram_id), username))
                conn.commit()
                print(f"Updated Telegram ID in services table for user {username}.")
            
            if str(old_full_name) == str(full_name) and str(old_telegram_id) == str(telegram_id):
                print(f"User {username} already exists with the same full_name and Telegram ID.")
            
            
            if not referral_code:
                c.execute("UPDATE users SET referral_code = ? WHERE username = ?", (encode_base62(username), username))
                conn.commit()
            return False
        
        else:
            c.execute("""
                INSERT INTO users (
                    username, full_name, telegram_id, balance, 
                    volume_config_price, 
                    unlimited_volume_config_price, unlimited_config_one_price,unlimited_config_two_price,meli_config_price, is_friend,is_blocked,referral_code 
                ) VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0,0,0,?)
            """, (username, str(full_name), str(telegram_id), balance,referral_code))
            conn.commit()
            print(f"User {username} added successfully.")
            return True
            
    except Exception as e:
        print(f"Error adding user {username}: {e}")
        return False
    finally:
        conn.close()




BASE62 = string.digits + string.ascii_lowercase + string.ascii_uppercase

def encode_base62(num):
    num = int(num)
    if num == 0:
        return BASE62[0]
    s = ""
    base = len(BASE62)
    while num > 0:
        num, rem = divmod(num, base)
        s = BASE62[rem] + s
    return s

def decode_base62(s):
    base = len(BASE62)
    num = 0
    for char in s:
        num = num * base + BASE62.index(char)
    return num






def update_balance_and_hash(amount_to_add, username,):
    """موجودی کاربر را به‌روزرسانی می‌کند و هش تراکنش را ثبت می‌کند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT balance FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        current_balance = row[0] if row and row[0] is not None else 0
        new_balance = current_balance + amount_to_add

        c.execute("UPDATE users SET balance = ?  WHERE username = ?", (new_balance,username))
        conn.commit()
    except Exception as e:
        print(f"Error updating balance or hash for user {username}: {e}")
    finally:
        conn.close()

def add_manual_balance(user_id, amount):
    """موجودی یک کاربر را به صورت دستی افزایش می‌دهد."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT balance FROM users WHERE username = ?", (user_id,))
        row = c.fetchone()

        if row is None:
            print(f"❌ کاربری با username = {user_id} یافت نشد.")
            return False

        current_balance = row[0] if row[0] is not None else 0
        new_balance = current_balance + amount

        c.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, user_id))
        conn.commit()
        return True

    except Exception as e:
        print("❌ خطا در بروزرسانی موجودی دستی:", e)
        return False
    finally:
        conn.close()




def decrease_manual_balance(user_id, amount):
    """موجودی یک کاربر را به صورت دستی کاهش می‌دهد."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT balance FROM users WHERE username = ?", (user_id,))
        row = c.fetchone()

        if row is None:
            print(f"❌ کاربری با username = {user_id} یافت نشد.")
            return False

        current_balance = row[0] if row[0] is not None else 0
        new_balance = current_balance - amount
        if new_balance < 0:
            new_balance = 0

        c.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, user_id))
        conn.commit()
        return True

    except Exception as e:
        print("❌ خطا در بروزرسانی موجودی دستی:", e)
        return False
    finally:
        conn.close()










def add_discount(user_id, discount_amount, expiry_time):
    """کد تخفیف را برای یک کاربر خاص اضافه می‌کند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO discounts (user_id, discount_amount, applied, expiry_time) VALUES (?, ?, 0, ?)",
                  (user_id, discount_amount, expiry_time))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in adding discount for user {user_id}: {e}")
        return False
    finally:
        conn.close()

def add_discount_to_all(discount_amount, expiry_time):
    """کد تخفیف را برای همه کاربران اضافه می‌کند."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT username FROM users")
        users = c.fetchall()
        for user in users:
            c.execute("INSERT INTO discounts (user_id, discount_amount, applied, expiry_time) VALUES (?, ?, 0, ?)",
                      (user[0], discount_amount, expiry_time))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error in adding discount to all: {e}")
        return False
    finally:
        conn.close()

def is_discount_valid(user_id, current_time):
    """بررسی می‌کند که آیا کد تخفیف معتبر برای کاربر وجود دارد."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT discount_amount, expiry_time FROM discounts WHERE user_id = ? AND applied = 0", (user_id,))
        discounts = c.fetchall()
        valid_discounts = []
        for discount in discounts:
            if discount[1] > current_time:
                valid_discounts.append(discount[0])
        return valid_discounts
    finally:
        conn.close()

def send_message_to_users(user_ids, message_text):
    """یک پیام را برای لیست مشخصی از کاربران ارسال می‌کند."""
    for user_id in user_ids:
        try:
            bot.send_message(user_id, message_text,parse_mode='Markdown')
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")

def is_txid_already_used(txid):
    """بررسی می‌کند که آیا یک هش تراکنش قبلاً استفاده شده است."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM payments WHERE hash_order = ?", (txid,))
        result = c.fetchone()[0]
        return result > 0
    finally:
        conn.close()

def get_last_trx_price():
    """قیمت لحظه‌ای TRX/IRT را از نوبیتکس دریافت می‌کند."""
    url = 'https://apiv2.nobitex.ir/v3/orderbook/TRXIRT'
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
        data = response.json()
        price = data.get("lastTradePrice")
        if price:
            return int(price)
        else:
            print("❌ قیمت TRX یافت نشد.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ خطای شبکه هنگام دریافت قیمت TRX: {e}")
        return None
    except Exception as e:
        print(f"❌ خطا هنگام پردازش قیمت TRX: {e}")
        return None

def check_trx_transfer(tx_hash, target_address):
    """جزئیات یک تراکنش TRX را بررسی می‌کند و مقدار تومانی آن را برمی‌گرداند."""
    url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={tx_hash}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        contract_type = data.get("contractType")
        contract_data = data.get("contractData", {})

        if contract_type == 1: # نوع قرارداد 1 برای انتقال TRX است.
            to_address = contract_data.get("to_address")
            amount = int(contract_data.get("amount", 0))

            if to_address and to_address.lower() == target_address.lower(): # مقایسه آدرس‌ها بدون حساسیت به حروف بزرگ و کوچک
                trx_amount = amount / 1_000_000 # TRX در ترون‌اسکن با 6 رقم اعشار ذخیره می‌شود
                price = get_last_trx_price()

                if price is None:
                    print(f"⚠️ {trx_amount} TRX به آدرس {target_address} ارسال شده، اما قیمت لحظه‌ای دریافت نشد.")
                    return trx_amount # در صورت عدم دریافت قیمت، فقط مقدار TRX را برمی‌گرداند.

                total_rial = trx_amount * price
                rounded_rial = math.ceil(total_rial / 1000) * 1000 # رند کردن به سمت بالا به نزدیک‌ترین هزار تومان (معمولا ریال)
                rounded_toman = int(rounded_rial / 10) # تبدیل ریال به تومان
                return rounded_toman
            else:
                return "❌ آدرس مقصد تراکنش با آدرس کیف پول ربات مطابقت ندارد."

        return "❌ تراکنش TRX به این آدرس وجود ندارد یا از نوع انتقال نیست."
    except requests.exceptions.RequestException as e:
        print(f"❌ خطای شبکه هنگام بررسی تراکنش: {e}")
        return None
    except Exception as e:
        print(f"❌ خطای نامشخص در بررسی تراکنش: {e}")
        return None





def get_trx_amount(tx_hash,target_address):

    url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={tx_hash}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        contract_type = data.get("contractType")
        contract_data = data.get("contractData", {})

        if contract_type == 1: # نوع قرارداد 1 برای انتقال TRX است.
            to_address = contract_data.get("to_address")
            amount = int(contract_data.get("amount", 0))

            if to_address and to_address.lower() == target_address.lower(): # مقایسه آدرس‌ها بدون حساسیت به حروف بزرگ و کوچک
                trx_amount = amount / 1_000_000 # TRX در ترون‌اسکن با 6 رقم اعشار ذخیره می‌شود
                return trx_amount 
    except requests.exceptions.RequestException as e:
        print(f"❌ خطای شبکه هنگام بررسی تراکنش: {e}")
        return None




def create_gift_link(license, target, stars, callback_url=None):
    headers = {"Authorization": f"Bearer {license}"}
    data = {"targetAccount": target, "stars": stars}
    if callback_url:
        data["callbackUrl"] = callback_url
    
    response = requests.post(
        'https://starsefar.xyz/api/create-gift-link',
        json=data,
        headers=headers
    )
    return response.json()

# استفاده - استارزها به شما اضافه می‌شوند






def add_commas(number):
    return "{:,.0f}".format(number)





def single_with_retries_login_test(method, url, json=None, max_retries=5):
    session = requests.session()
    attempt = 0
    response_data = None
    backoff_base = 1  # زمان اولیه تاخیر (1 ثانیه)
    max_backoff = 2  # حداکثر زمان backoff (2 ثانیه)

    while attempt < max_retries:
        try:
            # ارسال درخواست
            if json is not None:
                if method.lower() == "post":
                    response = session.post(url=url+login_url, json=json, timeout=10)
                else:
                    response = session.get(url=url+login_url, json=json, timeout=10)
            else:
                if method.lower() == "post":
                    response = session.post(url=url+login_url, timeout=10)
                else:
                    response = session.get(url=url+login_url, timeout=10)

            response_data = response.json()

            if response_data.get("success"):
                return response_data  # موفقیت‌آمیز بود
            else:
                raise Exception("API response unsuccessful")

        except Exception as e:
            print(f"❌ تلاش {attempt+1} برای درخواست به {url} ناموفق بود: {e}")

            # تلاش برای لاگین مجدد در صورت نیاز
            try:
                session.close()
                session = requests.Session()
                login_res = session.post(url + login_url, json=data, headers=headers)
                if login_res.status_code != 200 or not login_res.json().get("success"):
                    print("⚠️ لاگین مجدد هم شکست خورد.")
            except:
                print("⚠️ خطا در لاگین مجدد")

            # تاخیر با exponential backoff
            delay = min(backoff_base * (2 ** attempt), max_backoff)
            print(f"⏳ تاخیر {delay} ثانیه قبل از تلاش مجدد...")
            time.sleep(0.1)

        attempt += 1

    # اگر هیچ تلاشی موفق نبود
    print("🚨 تمام تلاش‌ها برای دریافت پاسخ شکست خورد.")
    return False





def single_with_retries(method,url, json=None, max_retries=5):
    panel_url = re.match(r"^(.*?)(?=panel)", url)
    panel_url=panel_url.group(1)
    session = requests.session()
    alpha = session.post(panel_url+login_url, json=data, timeout=5)
    attempt = 0
    response_data = None
    backoff_base = 1  # زمان اولیه تاخیر (1 ثانیه)
    max_backoff = 2  # حداکثر زمان backoff (10 ثانیه)
    while attempt < max_retries:
        try:
            if json is not None:
                 if method.lower() == "post":
                    response = session.post(url=url, json=json, timeout=10)
                 else:
                    response = session.get(url=url, json=json, timeout=10)

            else:
                if method.lower() == "post":
                   response = session.post(url=url, timeout=10)
                else:
                   response = session.get(url=url, timeout=10)  

            response_data = response.json()

            if response_data.get("success"):
                break  # موفقیت‌آمیز بود
            else:
                raise Exception("API response unsuccessful")

        except Exception as e:
            print(f"❌ تلاش {attempt+1} برای درخواست به {url} ناموفق بود: {e}")
            # تلاش برای لاگین مجدد
            session.close()
            session = requests.Session()
            login_res = session.post(panel_url+login_url, json=data, headers=headers)
            if login_res.status_code != 200 or not login_res.json().get("success"):
                print("⚠️ لاگین مجدد هم شکست خورد.")

            # ✅ Delay با Exponential Backoff
            delay = min(backoff_base * (2 ** attempt), max_backoff)
            print(f"⏳ تاخیر {delay} ثانیه قبل از تلاش مجدد...")
            time.sleep(0.1)
                

        attempt += 1
        if not response_data or not response_data.get("success"):
            print("🚨 تمام تلاش‌ها برای دریافت لیست شکست خورد. ریستارت کردن سرویس peak...")

            # try:
            #     subprocess.run(['/usr/bin/systemctl', 'restart', 'peak'])
            #     print("✅ سرویس peak با موفقیت ریستارت شد.")
            #     if json is not None:
            #         response = session.post(url=url, json=json, timeout=10)
            #     else:
            #         response = session.post(url=url, timeout=10)

            #     response_data = response.json()

            # except subprocess.CalledProcessError as e:
            #    print(f"❌ ریستارت peak با خطا مواجه شد: {e}")
    return response_data  # می‌تونه None یا response موفق باشه





# --- دیکشنری برای نگهداری وضعیت کاربران ---
user_states = {}


# --- هندلر دستور /start ---
@bot.message_handler(commands=['start'])

def send_welcome(message):
    """Handles the /start command, adds user, and shows main menu."""
    
    user_id = message.from_user.id
    CHANNEL = '@v2ray_nonstop_channel'  # آدرس کانال شما


    # --- بررسی عضویت کاربر ---
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        if member.status == 'left':
            # دکمه Join برای کانال
            keyboard = types.InlineKeyboardMarkup()
            join_button = types.InlineKeyboardButton(
                text="✅ عضو شدن در کانال",
                url=f"https://t.me/{CHANNEL.strip('@')}"
            )
            keyboard.add(join_button)
            bot.send_message(
                chat_id=message.chat.id,
                text="برای استفاده از ربات ابتدا باید در کانال ما عضو شوید. بعد از عضویت دوباره /start را بزنید.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
    except Exception as e:
        bot.send_message(
            chat_id=message.chat.id,
                text="برای استفاده از ربات ابتدا باید در کانال ما عضو شوید. بعد از عضویت دوباره /start را بزنید.",
                reply_markup=keyboard,
                parse_mode="Markdown"
        )
        return

    # --- ثبت و نمایش منو ---
    
    
    
    user_id = message.from_user.id  # آیدی عددی تلگرام کاربر
    user_states.pop(user_id, None) # Clear any previous state
    username = message.from_user.username or f"user_{user_id}"  # اگر username نداشت یک پیشفرض بساز
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = (first_name + " " + last_name).strip() or "کاربر گرامی"
    add_user(str(user_id),str(full_name),str(username),encode_base62(user_id)) # Add user to database if not already there
    args = message.text.split()
    possible_ref_code = args[1] if len(args) > 1 else None
    if possible_ref_code:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE referral_code = ?", (possible_ref_code,))
        ref_row = c.fetchone()
        if ref_row:
            parent_referral_code = ref_row[0]  # ✅ معرف پیدا شد
            if int(parent_referral_code)!=int(user_id):
             c.execute("UPDATE users SET parent = ? WHERE username = ?",(parent_referral_code, user_id))
             conn.commit()
    
        conn.close()    
    show_main_menu(message)

# --- Display Main Bot Menu ---
def show_main_menu(message, user_id=None):
    subscription_domain = get_config_value("subscription_domain") or "تنظیم نشده"
    miniapp_subdomain = get_config_value("miniapp_subdomain") or "تنظیم نشده"
    """Displays the main menu of the bot."""
    if user_id is None:
        user_id = message.from_user.id
        # username = message.from_user.username or f"user_{user_id}"  # اگر username نداشت یک پیشفرض بساز
        # encoded_username = urllib.parse.quote(username)
    username =get_telegram_id(user_id) or f"user_{user_id}"  # اگر username نداشت یک پیشفرض بساز
    bot_status = get_bot_status()

    # If bot is off and user is not an admin
    if bot_status == 'OFF' and user_id not in special_user_ids:
        bot.send_message(
            message.chat.id,
            "با عرض پوزش، ربات در حال حاضر برای انجام به‌روزرسانی‌های مهم و افزودن قابلیت‌های جدید موقتاً غیرفعال است. لطفاً کمی صبر کنید و بعداً دوباره امتحان کنید. از همراهی شما ممنونیم! 😊"
        )
        return

    # If user is blocked
    if is_user_blocked(user_id):
        bot.send_message(
            message.chat.id,
            "متأسفانه حساب شما مسدود شده است. لطفاً با پشتیبانی تماس بگیرید."
        )
        return

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    # دکمه‌های عمومی
    keyboard.add(
        types.InlineKeyboardButton(
            "حجمی",
            web_app=types.WebAppInfo(
                url=f"https://{miniapp_subdomain}/add_direct.html?user_id={user_id}&telegram_id={username}"
            )
        ),
        types.InlineKeyboardButton(
            "نامحدود",
            web_app=types.WebAppInfo(
                url=f"https://{miniapp_subdomain}/add_unlimited.html?user_id={user_id}&telegram_id={username}"
            )
        ),
        types.InlineKeyboardButton(
            "نت ملی",
            web_app=types.WebAppInfo(
                url=f"https://{miniapp_subdomain}/add.html?user_id={user_id}&telegram_id={username}"
            )
        )        
        
    )


    
    
    
    keyboard.add(
        types.InlineKeyboardButton("لیست کاربرها", web_app=types.WebAppInfo(url=f"https://{miniapp_subdomain}/list.html?user_id={user_id}&telegram_id={username}")
    )),
    keyboard.add(
        types.InlineKeyboardButton("💎 شارژ کیف پول با ترون", callback_data="charge_wallet_trx"),
        types.InlineKeyboardButton("💳 کارت به کارت", callback_data="charge_wallet")
    )  
    keyboard.add(
            types.InlineKeyboardButton("لینک دعوت دوستان ", callback_data="referral_link")
    )
    keyboard.add(
            types.InlineKeyboardButton("ارتباط با پشتیبانی", callback_data="contact_support")
    )
    if user_id in special_user_ids: # Admin button only for admins
        keyboard.add(
            types.InlineKeyboardButton("مدیریت ویژه", callback_data="admin_panel")
        )

    # Try to edit the message if it already exists, otherwise send a new message
    if hasattr(message, 'message_id') and message.text:
        
        full_name=get_user_full_name(user_id)
        username=get_telegram_id(user_id)
        username = username.replace('_', '-') if username else None
        username_text=username
        if username.startswith("user"):
         username_text = "آیدی تلگرام ثبت نشده"
         
        balance = get_user_balance(user_id)  # تابع شما برای موجودی کاربر
        balance_str = f"{balance:,.0f}"
        print(full_name,username,balance)
        RLM = "\u200F"  # Right-to-Left Mark

        text = (
            f"{RLM}👋 سلام {full_name}!\n\n"
            f"{RLM}🆔 آیدی عددی شما: `{user_id}`\n"
            f"{RLM}💬 آیدی تلگرام شما: {username_text}\n"
            f"{RLM}💰 موجودی شما: {balance_str} تومان\n\n"
            f"{RLM}👇 یکی از گزینه‌های زیر را انتخاب کنید:"
        )
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception:
            bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text="سلام! یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=keyboard
        )



# --- Callback Query Handler ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Handles all incoming callback queries."""
    user_id = call.from_user.id
    bot_status = get_bot_status()

    # Check bot status for normal users
    if bot_status == 'OFF' and user_id not in special_user_ids and call.data != "admin_panel":
        bot.answer_callback_query(call.id, "ربات موقتاً غیرفعال است. لطفاً بعداً امتحان کنید.")
        return

    # Check block status for normal users
    if is_user_blocked(user_id) and user_id not in special_user_ids and call.data != "admin_panel":
        bot.answer_callback_query(call.id, "حساب شما مسدود شده است. لطفاً با پشتیبانی تماس بگیرید.")
        return

    # Handle various states based on callback_data
    WALLET_ADDRESS='TTvAaQ2EK3T83JF3Rg5undK83paXrHr1hF'
    if call.data == "charge_wallet_trx":
        user_states[user_id] = "waiting_txid"

        # گرفتن قیمت لحظه‌ای ترون
        try:
            trx_price = get_last_trx_price()   # مثلا 0.12 (دلار)
        except Exception as e:
            trx_price = None
            print("خطا در گرفتن قیمت ترون:", e)

        # پیام اول: قیمت و آدرس واریز
        if trx_price:
            text_price = (
            f"💰 قیمت فعلی ترون: *{add_commas(trx_price / 10)}* تومان\n\n"
            f"🔹 برای شارژ حساب، مقدار ترون مورد نظر خود را به آدرس زیر ارسال کنید:\n`{WALLET_ADDRESS}`\n\n"
            f"✨ با پرداخت از طریق ترون، کیف پول شما ۱۰٪ بیشتر شارژ می‌شود!"
            )
        else:
            text_price = (
                f"🔸 لطفاً مقدار ترون مورد نظر خود را به این آدرس واریز کنید:\n`{WALLET_ADDRESS}`\n"
                "(خطا در دریافت قیمت لحظه‌ای ترون)"
            )

        bot.send_message(
            call.message.chat.id,
            text_price,
            parse_mode='Markdown'
        )

        # پیام دوم: درخواست هش تراکنش
        bot.send_message(
            call.message.chat.id,
            "پس از واریز *هش تراکنش (TXID)* را ارسال کنید:",
            parse_mode='Markdown'
        )



    elif call.data=="charge_wallet":
        user_states[user_id] = "waiting_charge_amount"
        bot.send_message(
        call.message.chat.id,
        "💳 لطفاً مبلغ مورد نظر برای شارژ کیف پول را وارد کنید:\n"
        "🔹 حداقل: 100,000 تومان\n"
        "🔹 حداکثر: 10,000,000 تومان"
    )



    elif call.data=="referral_link":
        bot_username = "v2ray_nonstop_bot"

        invite_link = get_referral_link(call.message.chat.id, bot_username)
        if invite_link:
            message_text = (
                f"🔗 لینک دعوت شما:\n {invite_link}\n\n"
                f"🚀با اشتراک‌گذاری این لینک، دوستانتان می‌توانند به ربات بپیوندند و "
                f"شما ۵٪ از خریدهای آنها را به عنوان پاداش دریافت خواهید کرد!"
            )
            bot.send_message(call.message.chat.id, message_text)
        else:
            bot.send_message(call.message.chat.id, "⚠️ هنوز کد رفرال شما ساخته نشده است.")    


    elif call.data=="contact_support":
        SUPPORT_ID = "@v2ray_nonstop_support"
        text = "💬 برای ارتباط با پشتیبانی لطفاً با این آیدی در تماس باشید:\n" + SUPPORT_ID

        bot.send_message(call.message.chat.id, text)


        

    elif call.data == "admin_panel" and user_id in special_user_ids:
        # We always send a new admin panel message to ensure it's at the bottom
        # after any previous messages or confirmations.
        show_admin_panel(call.message)
    elif call.data == "manual_charge":
        user_states[user_id] = "waiting_user_id_for_balance_management"
        bot.send_message(
            call.message.chat.id,
            "لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:"
        )


    elif call.data == "manage_user_list":
        user_states[user_id] = "waiting_user_id_for_list_users"
        bot.send_message(
            call.message.chat.id,
            "لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:"
        )

    elif call.data.startswith("manage_balance_"):
        parts = call.data.split("_")
        target_user_id = parts[2]
        current_balance = get_user_balance(target_user_id)

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("افزایش موجودی", callback_data=f"increase_balance_{target_user_id}"),
            types.InlineKeyboardButton("کسر موجودی", callback_data=f"decrease_balance_{target_user_id}"),
            types.InlineKeyboardButton("صفر کردن موجودی", callback_data=f"reset_balance_{target_user_id}"),
            types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel")
        )
        # Always edit the message that contained the "manage_balance_" button
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"موجودی فعلی کاربر `{target_user_id}`: *{add_commas(current_balance)}* تومان\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception:
            # If editing fails (e.g., message too old, or no buttons were present), send a new one.
            bot.send_message(
                chat_id=call.message.chat.id,
                text=f"موجودی فعلی کاربر `{target_user_id}`: *{add_commas(current_balance)}* تومان\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    elif call.data.startswith("increase_balance_"):
        target_user_id = call.data.split("_")[2]
        user_states[user_id] = {"state": "waiting_increase_amount_manual_charge", "target_user_id": target_user_id}
        bot.send_message(call.message.chat.id, f"لطفاً مقدار شارژ (به تومان) را برای کاربر `{target_user_id}` وارد کنید:",parse_mode='Markdown')


    elif call.data.startswith("decrease_balance_"):
        target_user_id = call.data.split("_")[2]
        user_states[user_id] = {"state": "waiting_decrease_amount_manual_charge", "target_user_id": target_user_id}
        bot.send_message(call.message.chat.id, f"لطفاً مقدار کسر شارژ (به تومان) را برای کاربر `{target_user_id}` وارد کنید:",parse_mode='Markdown')

    elif call.data.startswith("reset_balance_"):
        target_user_id = call.data.split("_")[2]
        
        # Try to remove buttons from the original message to avoid stale buttons
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None # Remove buttons
            )
        except Exception as e:
            print(f"Error removing reply markup: {e}")
            pass # Continue even if it fails

        if reset_user_balance(target_user_id):
            updated_balance = get_user_balance(target_user_id) # Fetch new balance
            # Send the confirmation message directly before showing the admin panel.
            bot.send_message(call.message.chat.id, f" موجودی کاربر `{target_user_id}` با موفقیت صفر شد.✅ \nموجودی جدید: {updated_balance} تومان", parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, f"❌ خطا در صفر کردن موجودی کاربر `{target_user_id}`.")
        
        # Then, show the admin panel again, which will appear AFTER the confirmation message.
        show_admin_panel(call.message)





    elif call.data == "add_discount":
        user_states[user_id] = {"state": "waiting_user_id_discount"}
        bot.send_message(
            call.message.chat.id,
            "لطفاً آیدی عددی کاربر یا 'all' برای همه کاربران را وارد کنید:"
        )
    elif call.data == "toggle_bot":
        current_status = get_bot_status()
        new_status = 'OFF' if current_status == 'ON' else 'ON'
        set_bot_status(new_status)
        bot.send_message(
            call.message.chat.id,
            f"وضعیت ربات به {new_status} تغییر کرد."
        )
        show_admin_panel(call.message)
    elif call.data == "block_user":
        user_states[user_id] = "waiting_user_id_block"
        bot.send_message(
            call.message.chat.id,
            "لطفاً آیدی عددی کاربر را برای بلاک کردن وارد کنید:"
        )
    elif call.data == "show_blocked_users":
        show_blocked_users(call.message)
    elif call.data.startswith("unblock_"):
        target_user_id = call.data.split("_")[1]
        if unblock_user(target_user_id):
            bot.send_message(
                call.message.chat.id,
                f"✅ کاربر `{target_user_id}` با موفقیت آنبلاک شد.",parse_mode='Markdown'
            )
            # Refresh blocked users list
            ##show_blocked_users(call.message)
        else:
            bot.send_message(
                call.message.chat.id,
                f"❌ خطا در آنبلاک کردن کاربر {target_user_id}."
            )
    elif call.data == "send_config":
        user_states[user_id] = "waiting_user_id_config"
        bot.send_message(
            call.message.chat.id,
            "لطفاً آیدی عددی کاربر یا 'all' برای همه کاربران را وارد کنید:" # Changed for clarity, assuming user ID is for the config
        )

    elif call.data == "send_message":
        user_states[user_id] = "waiting_user_id_message"
        bot.send_message(
            call.message.chat.id,
            "لطفاً آیدی عددی کاربر یا 'all' برای همه کاربران را وارد کنید:"
        )

    elif call.data == "get_single_config_price": # Set general prices
        if user_id in special_user_ids:
            # Create message text with current prices
            message_text = "لطفاً نوع کانفیگ را برای تنظیم **قیمت عمومی** انتخاب کنید:\n\n"
            for key, name in GENERAL_PRICE_KEYS.items():
                current_price = get_config_value(key)
                message_text += f"*{name}:*{add_commas(int(current_price))} تومان\n"
            message_text += "\nبرای تغییر هر مورد، روی دکمه مربوطه کلیک کنید:"

            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                types.InlineKeyboardButton("کانفیگ حجمی", callback_data="set_volume_config_price"),
                types.InlineKeyboardButton("کانفیگ حجمی بدون تاریخ", callback_data="set_unlimited_volume_config_price"),
                types.InlineKeyboardButton("کانفیگ نامحدود تک کاربر ", callback_data="set_unlimited_config_one_price"),
                types.InlineKeyboardButton("کانفیگ نامحدود دو کاربر ", callback_data="set_unlimited_config_two_price"),
                types.InlineKeyboardButton("کانفیگ نت ملی ", callback_data="set_meli_config_price"),
                types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel")
            )
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            except Exception as e: # If editing is not possible (e.g., message changed or new)
                print(f"Error editing message for get_single_config_price: {e}")
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        else:
            bot.answer_callback_query(call.id, "شما اجازه دسترسی به این بخش را ندارید.")










    elif call.data == "get_domains":

        if user_id in special_user_ids:
            subscription_domain = get_config_value("subscription_domain") or "تنظیم نشده"
            miniapp_subdomain = get_config_value("miniapp_subdomain") or "تنظیم نشده"

            # گرفتن مقادیر از دیتابیس


            message_text = (
                "⚙️ تنظیمات دامنه‌ها\n\n"
                f"🔗 *لینک سابسکریپشن:* \n`{subscription_domain}`\n\n"
                f"🌐 *ساب‌دامنه مینی اپ:* \n`{miniapp_subdomain}`\n\n"
                "برای تغییر هر مورد روی دکمه مربوطه کلیک کنید:"
            )

            keyboard = types.InlineKeyboardMarkup(row_width=1)

            keyboard.add(
                types.InlineKeyboardButton(
                    "تغییر لینک سابسکریپشن",
                    callback_data="change_subscription_domain"
                ),

                types.InlineKeyboardButton(
                    "تغییر ساب‌دامنه مینی اپ",
                    callback_data="change_miniapp_subdomain"
                ),

                types.InlineKeyboardButton(
                    "بازگشت به پنل مدیریت",
                    callback_data="admin_panel"
                )
            )

            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

            except Exception as e:
                print(f"Error editing message for get_domains: {e}")

                bot.send_message(
                    chat_id=call.message.chat.id,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

        else:
            bot.answer_callback_query(
                call.id,
                "شما اجازه دسترسی به این بخش را ندارید."
            )

    # -------------------------------------------------------
    # تغییر لینک سابسکریپشن
    # -------------------------------------------------------
    elif call.data == "change_subscription_domain":

        msg = bot.send_message(
            call.message.chat.id,
            "لطفاً لینک جدید سابسکریپشن را ارسال کنید:"
        )

        def save_subscription_domain(message):

            new_value = message.text.strip()

            conn = sqlite3.connect("users.db")
            c = conn.cursor()

            c.execute("""
                INSERT OR REPLACE INTO bot_config
                (config_key, config_value)
                VALUES (?, ?)
            """, ("subscription_domain", new_value))

            conn.commit()
            conn.close()

            bot.send_message(
                message.chat.id,
                "✅ لینک سابسکریپشن با موفقیت بروزرسانی شد."
            )

        bot.register_next_step_handler(
            msg,
            save_subscription_domain
        )
    # -------------------------------------------------------
    # تغییر ساب دامنه مینی اپ
    # -------------------------------------------------------
    elif call.data == "change_miniapp_subdomain":

        msg = bot.send_message(
            call.message.chat.id,
            "لطفاً ساب‌دامنه جدید مینی اپ را بدون http ارسال کنید:"
        )

        def save_miniapp_subdomain(message):

            new_value = message.text.strip()

            conn = sqlite3.connect("users.db")
            c = conn.cursor()

            c.execute("""
                INSERT OR REPLACE INTO bot_config
                (config_key, config_value)
                VALUES (?, ?)
            """, ("miniapp_subdomain", new_value))

            conn.commit()
            conn.close()

            bot.send_message(
                message.chat.id,
                "✅ ساب‌دامنه مینی اپ با موفقیت بروزرسانی شد."
            )

        bot.register_next_step_handler(
            msg,
            save_miniapp_subdomain
        )






    elif call.data == "set_volume_config_price":
        user_states[user_id] = {"state": "waiting_general_price_input", "config_key": "volume_config_price"}
        bot.send_message(call.message.chat.id, "لطفاً قیمت *کانفیگ حجمی* (به تومان) را وارد کنید:",parse_mode='Markdown')

    elif call.data == "set_unlimited_volume_config_price":
        user_states[user_id] = {"state": "waiting_general_price_input", "config_key": "unlimited_volume_config_price"}
        bot.send_message(call.message.chat.id, "لطفاً قیمت *کانفیگ حجمی بدون تاریخ* (به تومان) را وارد کنید:",parse_mode='Markdown')
    elif call.data == "set_unlimited_config_one_price":
        user_states[user_id] = {"state": "waiting_general_price_input", "config_key": "unlimited_config_one_price"}
        bot.send_message(call.message.chat.id, "لطفا قیمت *کانفیگ نامحدود تک کاربر* (به تومان) را وارد کنید:",parse_mode='Markdown')
    
    elif call.data == "set_unlimited_config_two_price":
        user_states[user_id] = {"state": "waiting_general_price_input", "config_key": "unlimited_config_two_price"}
        bot.send_message(call.message.chat.id, "لطفا قیمت *کانفیگ نامحدود دو کاربر* (به تومان) را وارد کنید:",parse_mode='Markdown')    


    elif call.data == "set_meli_config_price":
        user_states[user_id] = {"state": "waiting_general_price_input", "config_key": "meli_config_price"}
        bot.send_message(call.message.chat.id, "لطفا قیمت *کانفیگ نت ملی* (به تومان) را وارد کنید:",parse_mode='Markdown')   


    elif call.data == "set_user_specific_prices": # Set user-specific prices
        if user_id in special_user_ids:
            user_states[user_id] = {"state": "waiting_target_user_id_for_specific_prices"}
            bot.send_message(
                call.message.chat.id,
                "لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:"
            )
        else:
            bot.answer_callback_query(call.id, "شما اجازه دسترسی به این بخش را ندارید.")

    elif call.data.startswith("set_specific_price_type_"):
        parts = call.data.split("_")
        # Ensure indices are correct.
        # call.data: "set_specific_price_type_USERID_CONFIGTYPE"
        if len(parts) >= 6:
            target_user_id = parts[4]
            config_type = "_".join(parts[5:]) # This should correctly be the full key, e.g., 'unlimited_config'
        else:
            bot.send_message(call.message.chat.id, "❌ خطای داخلی: فرمت داده‌های کال‌بک نامعتبر است.")
            user_states.pop(user_id, None)
            show_admin_panel(call.message)
            return

        user_states[user_id] = {
            "state": "waiting_user_specific_price_input",
            "target_user_id": target_user_id,
            "config_type": config_type # Storing the full config_type
        }
        display_name = CONFIG_TYPE_NAMES.get(config_type, config_type)
        bot.send_message(
            call.message.chat.id,
            f"لطفاً قیمت *{display_name}* را برای کاربر `{target_user_id}` (به تومان) وارد کنید:", parse_mode='Markdown'
        )
    
    elif call.data.startswith("discount_duration_"):
        duration = call.data.split("_")[-1]
        # Ensure user_states[user_id] is a dictionary
        if not isinstance(user_states.get(user_id), dict):
            user_states[user_id] = {}
        user_states[user_id]["duration"] = duration
        user_states[user_id]["state"] = "waiting_amount_discount"
        bot.send_message(
            call.message.chat.id,
            "مقدار (درصد) تخفیف رو وارد کنید:"
        )
    elif call.data == "back_to_main":
        show_main_menu(call.message, user_id=user_id)
        user_states.pop(user_id, None) # Clear user state




    # elif call.data == "add_new_panel":
    #     if user_id in special_user_ids:
    #         user_states[user_id] = {"state": "waiting_panel_address"}
    #         bot.send_message(call.message.chat.id, "لطفاً آدرس پنل را وارد کنید:")
    #     else:
    #         bot.answer_callback_query(call.id, "شما اجازه دسترسی به این بخش را ندارید.")

    # elif call.data == "view_panels":
    #     if user_id in special_user_ids:
    #         show_panels(call.message)
    #     else:
    #         bot.answer_callback_query(call.id, "شما اجازه دسترسی به این بخش را ندارید.")




    elif call.data.startswith("capacity_panel_"):
        print(call.data)
        if user_id in special_user_ids:
            panel_id = int(call.data.split("_")[2])  # جدا کردن آیدی پنل
            user_states[user_id] = {
                "state": "waiting_edit_capacity_panel",
                "panel_id": panel_id
            }
            bot.send_message(call.message.chat.id, f"لطفاً ظرفیت جدید برای پنل با ID `{panel_id}` را وارد کنید:",parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "شما اجازه دسترسی به این بخش را ندارید.")


    elif call.data.startswith("sublink_panel_"):
        if user_id in special_user_ids:
            panel_id = int(call.data.split("_")[2])  # جدا کردن آیدی پنل
            user_states[user_id] = {
                "state": "waiting_edit_sublink_panel",
                "panel_id": panel_id
            }
            bot.send_message(
                call.message.chat.id,
                f"🔗 لطفاً لینک سابسکریپشن جدید برای پنل با ID `{panel_id}` را وارد کنید:",
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "❌ شما اجازه دسترسی به این بخش را ندارید.")











    elif call.data.startswith("delete_panel_"):
        if user_id in special_user_ids:
            panel_id_to_delete = int(call.data.split("_")[2])
            if delete_panel_by_id(panel_id_to_delete):
                bot.send_message(call.message.chat.id, f"✅ پنل با ID: `{panel_id_to_delete}` با موفقیت حذف شد.")
                show_panels(call.message) # Refresh panel list
            else:
                bot.send_message(call.message.chat.id, f"❌ خطا در حذف پنل با ID: `{panel_id_to_delete}`.")
        else:
            bot.answer_callback_query(call.id, "شما اجازه دسترسی به این بخش را ندارید.")

    else:
        bot.answer_callback_query(call.id, "دستور نامشخص است.")


# --- Display Special Admin Panel ---
def show_admin_panel(message):
    subscription_domain = get_config_value("subscription_domain") or "تنظیم نشده"
    miniapp_subdomain = get_config_value("miniapp_subdomain") or "تنظیم نشده"
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    current_status = get_bot_status()
    toggle_text = "خاموش کردن ربات" if current_status == 'ON' else "روشن کردن ربات"
    keyboard.add(
        types.InlineKeyboardButton("شارژ دستی کیف پول", callback_data="manual_charge"),
        types.InlineKeyboardButton("اعمال کد تخفیف", callback_data="add_discount")
    )
    keyboard.add(
        types.InlineKeyboardButton("بلاک کاربر", callback_data="block_user"),
        types.InlineKeyboardButton("لیست کاربران بلاک‌شده", callback_data="show_blocked_users")
    )
    keyboard.add(
        types.InlineKeyboardButton("ارسال کانفیگ", callback_data="send_config"),
        types.InlineKeyboardButton("ارسال پیام", callback_data="send_message")
    )
    keyboard.add(
        types.InlineKeyboardButton("تنظیم قیمت‌های عمومی", callback_data="get_single_config_price"),
        types.InlineKeyboardButton("تنظیم قیمت برای کاربر", callback_data="set_user_specific_prices")
    )
    keyboard.add(
        types.InlineKeyboardButton("لیست کاربر ها", callback_data="manage_user_list")
    )  


    keyboard.add(
        types.InlineKeyboardButton("تنظیم دامنه ها", callback_data="get_domains")
    )    
    keyboard.add(
        types.InlineKeyboardButton(
            "مدیریت پنل ها ",
            web_app=types.WebAppInfo(
                url=f"https://{miniapp_subdomain}/manage_panel.html"
            )
        )
    )    
    keyboard.add(
        types.InlineKeyboardButton(toggle_text, callback_data="toggle_bot")
    )

    keyboard.add(
        types.InlineKeyboardButton("بازگشت", callback_data="back_to_main")
    )

    if hasattr(message, 'message_id') and message.text: # مطمئن می‌شویم پیام متنی است
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=f"پنل مدیریت ویژه (وضعیت ربات: {current_status})",
                reply_markup=keyboard
            )
        except Exception:
            bot.send_message(
                message.chat.id,
                f"پنل مدیریت ویژه (وضعیت ربات: {current_status})",
                reply_markup=keyboard
            )
    else:
        bot.send_message(
            message.chat.id,
            f"پنل مدیریت ویژه (وضعیت ربات: {current_status})",
            reply_markup=keyboard
        )

# --- Display Panels List ---
def show_panels(message):
    panels = get_all_panels()
    if not panels:
        bot.send_message(message.chat.id, "هیچ پنلی ثبت نشده است.")
        return

    for panel in panels:
        panel_id, address, is_unlimited, capacity, subscription_link, panel_type, tunnel_status, tunnel_type, iran_panel, second_kharej_panel, kahrej_local_ip, iran_ip, iran_password, *rest = panel
        current_users=show_totals(address)
        show_is_unlimited='نامحدود ' if int(is_unlimited) == 1 else 'حجمی'
        RLM = "\u200F"  # Right-to-Left Mark
        LRM = "\u200E" 
        panel_info = (
            f"{RLM}📌 **آدرس پنل:** `{address}`\n"
            f"{RLM}⚡ **وضعیت پنل:** {panel_type}\n"
            f"{RLM}💾 **حداکثر ظرفیت:** {capacity}\n"
            f"{RLM}👥 **ظرفیت فعلی:** {current_users}\n"
            f"{RLM}👥 **لینک سابسکریپشن:** `{subscription_link}`\n"
        )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(" تغییر ظرفیت پنل", callback_data=f"capacity_panel_{panel_id}")
        ) 
        keyboard.add(
            types.InlineKeyboardButton(" تغییر لینک سابسکریپشن ", callback_data=f"sublink_panel_{panel_id}")
        )              
            
                                        
        keyboard.add(
            types.InlineKeyboardButton("❌ حذف این پنل", callback_data=f"delete_panel_{panel_id}")
        )
        
        bot.send_message(
            message.chat.id,
            panel_info,
            reply_markup=keyboard,
            parse_mode='Markdown'
        ) 
    keyboard_back = types.InlineKeyboardMarkup()
    keyboard_back.add(types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel"))
    bot.send_message(message.chat.id, "لیست پنل‌ها به پایان رسید.", reply_markup=keyboard_back)
    
    


# --- Global Text Message Handler ---
@bot.message_handler(func=lambda m: True)
def global_handler(message):
    """Handles all incoming text messages based on the user's current state."""
    user_id = message.from_user.id
    bot_status = get_bot_status()

    # Check bot status for normal users
    if bot_status == 'OFF' and user_id not in special_user_ids:
        bot.send_message(
            message.chat.id,
            "با عرض پوزش، ربات در حال حاضر برای انجام به‌روزرسانی‌های مهم و افزودن قابلیت‌های جدید موقتاً غیرفعال است. لطفاً کمی صبر کنید و بعداً دوباره امتحان کنید. از همراهی شما ممنونیم! 😊"
        )
        return

    # Check block status for normal users
    if is_user_blocked(user_id) and user_id not in special_user_ids:
        bot.send_message(
            message.chat.id,
            "متأسفانه حساب شما مسدود شده است. لطفاً با پشتیبانی تماس بگیرید."
        )
        return

    state_data = user_states.get(user_id)
    if isinstance(state_data, dict):
        state = state_data.get("state")
    else:
        state = state_data

    if state == "waiting_txid":
        handle_txid_input(message)
    
    elif state == "waiting_charge_amount":
        miniapp_subdomain = get_config_value("miniapp_subdomain")
        callback_url = f"https://{miniapp_subdomain}/payment-callback"
        user_id = message.from_user.id
        text = message.text.strip()
        username = message.from_user.username or f"user_{user_id}"

        try:
            amount = int(text.replace(",", "").strip())

            if 100_000 <= amount <= 10_000_000:

                bot.send_message(
                    message.chat.id,
                    f"✅ مبلغ {amount:,} تومان ثبت شد. در حال پردازش پرداخت..."
                )

                # ---------------------------
                #  🔥 ایجاد سفارش tetra98
                # ---------------------------

                url = "https://tetra98.ir/api/create_order"
                payload = {
                    "ApiKey": "fe9decb5da565d5b4bc866b05d915e20",
                    "Hash_id":random_string(6),
                    "Amount": amount*10,
                    "Description": f"شارژ کیف پول کاربر {username}",
                    "Email": "",
                    "Mobile": "",
                    "CallbackURL": f"{callback_url}?user_id={user_id}&username={username}&amount={amount}"
                }

                response = requests.post(url, json=payload)
                result = response.json()
                print("PAYMENT RESULT:", result)

                # ---------------------------
                #  🔥 بررسی نتیجه
                # ---------------------------
                if result.get("status") == "100":
                    payment_link = result["payment_url_web"]

                    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("🔗 پرداخت آنلاین", url=payment_link))

                    bot.send_message(
                        message.chat.id,
                        "🎯 لینک پرداخت شما ایجاد شد.\n\n"
                        "برای تکمیل خرید روی دکمه زیر بزنید:",
                        reply_markup=markup
                    )

                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ خطا در ایجاد سفارش: {result}"
                    )

                user_states.pop(user_id, None)

            else:
                bot.send_message(
                    message.chat.id,
                    "⚠️ مبلغ باید بین 100,000 تا 10,000,000 تومان باشد.\n"
                    "لطفاً دوباره وارد کنید:"
                )

        except ValueError:
            bot.send_message(
                message.chat.id,
                "⚠️ لطفاً فقط عدد صحیح وارد کنید: (بین 100,000 تا 10,000,000)"
            )


        
           
        
        
        
        
    elif state == "waiting_user_id_for_balance_management":
        target_user_id_str = message.text.strip()
        if not target_user_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی کاربر نامعتبر است. لطفاً یک آیدی عددی وارد کنید:")
            return

        if not user_exists(target_user_id_str):
            bot.send_message(message.chat.id, f"❌ کاربری با آیدی `{target_user_id_str}` یافت نشد. لطفاً آیدی معتبر وارد کنید.")
            ##user_states.pop(user_id, None)
            ##show_admin_panel(message)
            return

        user_states[user_id] = {"state": "managing_balance", "target_user_id": target_user_id_str}
        
        current_balance = get_user_balance(target_user_id_str)
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("افزایش موجودی", callback_data=f"increase_balance_{target_user_id_str}"),
            types.InlineKeyboardButton("کسر موجودی", callback_data=f"decrease_balance_{target_user_id_str}"),
            types.InlineKeyboardButton("صفر کردن موجودی", callback_data=f"reset_balance_{target_user_id_str}"),
            types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel")
        )
        bot.send_message(
            message.chat.id,
            f"💰موجودی فعلی کاربر`{target_user_id_str}`: {add_commas(current_balance)} تومان\n\n👇یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


    elif state == "waiting_increase_amount_manual_charge":
        try:
            amount = int(message.text.strip())
            target_user_id = user_states[user_id]["target_user_id"] # Use string ID
            
            # Get balance before update
            balance_before_charge = get_user_balance(target_user_id)

            if add_manual_balance(target_user_id, amount):
                updated_balance = get_user_balance(target_user_id) # Fetch new balance
                bot.send_message(
                    message.chat.id, 
                    f" کیف پول کاربر `{target_user_id}` با {add_commas(amount)} تومان شارژ شد.✅ \n"
                    f"موجودی قبلی: {add_commas(balance_before_charge)} تومان\n"
                    f"موجودی جدید: {add_commas(updated_balance)} تومان", 
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(message.chat.id, "❌ خطا در شارژ کیف پول. (ممکن است کاربر وجود نداشته باشد)")
            user_states.pop(user_id, None)
            show_admin_panel(message)
        except ValueError:
            bot.send_message(message.chat.id, "❌ مقدار نامعتبر است. لطفاً عدد وارد کنید:")




    elif state == "waiting_decrease_amount_manual_charge":
        try:
            amount = int(message.text.strip())
            target_user_id = user_states[user_id]["target_user_id"] # Use string ID
            
            # Get balance before update
            balance_before_charge = get_user_balance(target_user_id)

            if decrease_manual_balance(target_user_id, amount):
                updated_balance = get_user_balance(target_user_id) # Fetch new balance
                bot.send_message(
                    message.chat.id, 
                    f" از کیف پول کاربر`{target_user_id}` {add_commas(amount)} تومان کسر شد.✅ \n"
                    f"موجودی قبلی: {add_commas(balance_before_charge)} تومان\n"
                    f"موجودی جدید: {add_commas(updated_balance)} تومان", 
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(message.chat.id, "❌ خطا در شارژ کیف پول. (ممکن است کاربر وجود نداشته باشد)")
            user_states.pop(user_id, None)
            show_admin_panel(message)
        except ValueError:
            bot.send_message(message.chat.id, "❌ مقدار نامعتبر است. لطفاً عدد وارد کنید:")



    elif state == "waiting_user_id_discount":
        user_states[user_id] = {"state": "waiting_duration_discount", "target_user_id": message.text.strip()}
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        durations = [("1 روز", 3600*24), ("2 روز", 3600*48), ("3 روز", 3600*72), ("1 هفته", 3600*168)]
        for text, seconds in durations:
            keyboard.add(types.InlineKeyboardButton(text, callback_data=f"discount_duration_{seconds}"))
        bot.send_message(
            message.chat.id,
            "مدت زمان اعتبار تخفیف را انتخاب کنید:",
            reply_markup=keyboard
        )

    elif state == "waiting_amount_discount":
        try:
            discount_amount = int(message.text.strip())
            print(discount_amount)
            target_user_id = user_states[user_id]["target_user_id"]
            duration = int(user_states[user_id]["duration"])
            if duration == 3600*24:
                duration_text = "1 روز"
            elif duration == 3600*48:
                duration_text = "2 روز"
            elif duration == 3600*72:
                duration_text = "3 روز"
            elif duration == 3600*168:
                duration_text = "1 هفته"
            expiry_time = int(time.time()) + duration

            if target_user_id.lower() == "all":
                if add_discount_to_all(discount_amount, expiry_time):
                    bot.send_message(message.chat.id, f"✅ تخفیف {discount_amount} درصد برای همه کاربران با اعتبار {duration_text}اعمال شد.")
                else:
                    bot.send_message(message.chat.id, "❌ خطا در اعمال تخفیف.")
            else:
                if add_discount(target_user_id, discount_amount, expiry_time):
                    bot.send_message(message.chat.id, f"✅ تخفیف {discount_amount} درصد برای کاربر {target_user_id} با اعتبار {duration_text}اعمال شد.")
                else:
                    bot.send_message(message.chat.id, "❌ خطا در اعمال تخفیف.")

            user_states.pop(user_id, None)
            show_admin_panel(message)
        except ValueError:
            bot.send_message(message.chat.id, "❌ مقدار نامعتبر است. لطفاً عدد وارد کنید:")

    elif state == "waiting_user_id_block":
        target_user_id = message.text.strip()
        if block_user(target_user_id):
            bot.send_message(message.chat.id, f"✅ کاربر `{target_user_id}` با موفقیت بلاک شد.", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, f"❌ خطا در بلاک کردن کاربر {target_user_id}.")
        user_states.pop(user_id, None)
        show_admin_panel(message)

    elif state == "waiting_user_id_config":
        # In this state, the user is expected to input the target user ID for config
        target_user_id_str = message.text.strip()
        # Basic validation for target_user_id_str (can be 'all' or a digit)
        if target_user_id_str.lower() != "all" and not target_user_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی کاربر نامعتبر است. لطفاً یک آیدی عددی یا 'all' وارد کنید:")
            return # Stay in this state or clear it and return to admin panel
        
        user_states[user_id] = {"state": "waiting_config_text", "target_user_id": target_user_id_str}
        bot.send_message(message.chat.id, "لطفاً متن کانفیگ را وارد کنید:")

    elif state == "waiting_config_text":
        config_text = message.text
        target_user_id = user_states[user_id]["target_user_id"]
        if target_user_id.lower() == "all":
            conn = get_db_connection()
            c = conn.cursor()
            try:
                c.execute("SELECT username FROM users WHERE is_blocked = 0")
                users = c.fetchall()
                user_ids_to_send = [user[0] for user in users]
                send_message_to_users(user_ids_to_send, f"کانفیگ جدید:\n`{config_text}`")
            finally:
                conn.close()
            bot.send_message(message.chat.id, "✅ کانفیگ برای همه کاربران ارسال شد.")
        else:
            try:
                # Ensure target_user_id is numeric and valid
                send_message_to_users([target_user_id], f"کانفیگ جدید:\n`{config_text}`")
                bot.send_message(message.chat.id, f"✅ کانفیگ برای کاربر `{target_user_id}` ارسال شد.",parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ خطا در ارسال کانفیگ به کاربر {target_user_id}: {e}")

        user_states.pop(user_id, None)
        show_admin_panel(message)

    elif state == "waiting_user_id_message":
        # In this state, the user is expected to input the target user ID for message
        target_user_id_str = message.text.strip()
        # Basic validation for target_user_id_str (can be 'all' or a digit)
        if target_user_id_str.lower() != "all" and not target_user_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی کاربر نامعتبر است. لطفاً یک آیدی عددی یا 'all' وارد کنید:")
            return # Stay in this state or clear it and return to admin panel

        user_states[user_id] = {"state": "waiting_message_text", "target_user_id": target_user_id_str}
        bot.send_message(message.chat.id, "لطفاً متن پیام را وارد کنید:")

    elif state == "waiting_message_text":
        message_text = message.text
        target_user_id = user_states[user_id]["target_user_id"]
        if target_user_id.lower() == "all":
            conn = get_db_connection()
            c = conn.cursor()
            try:
                c.execute("SELECT username FROM users WHERE is_blocked = 0")
                users = c.fetchall()
                user_ids_to_send = [user[0] for user in users]
                send_message_to_users(user_ids_to_send, message_text)
            finally:
                conn.close()
            bot.send_message(message.chat.id, "✅ پیام برای همه کاربران ارسال شد.")
        else:
            try:
                send_message_to_users([target_user_id], message_text)
                bot.send_message(message.chat.id, f"✅ پیام برای کاربر `{target_user_id}` ارسال شد.",parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ خطا در ارسال پیام به کاربر {target_user_id}: {e}")

        user_states.pop(user_id, None)
        show_admin_panel(message)

    elif state == "waiting_general_price_input":
        try:
            price = int(message.text.strip())
            config_key = user_states[user_id].get("config_key")
            if config_key:
                set_config_value(config_key, price)
                display_name = GENERAL_PRICE_KEYS.get(config_key, config_key) 
                bot.send_message(message.chat.id, f" قیمت *{display_name}* (عمومی) تنظیم شد: {add_commas(price)} تومان✅", parse_mode='Markdown')
                
                # Refresh the general prices menu after setting a price
                message_text = "لطفاً نوع کانفیگ را برای تنظیم **قیمت عمومی** انتخاب کنید:\n\n"
                
                # Update current prices display in the menu text
                for key, name in GENERAL_PRICE_KEYS.items():
                    current_price = get_config_value(key)
                    message_text += f"*{name}:*{add_commas(int(current_price))} تومان\n"
                message_text += "\nبرای تغییر هر مورد، روی دکمه مربوطه کلیک کنید:"

                keyboard = types.InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    types.InlineKeyboardButton("کانفیگ حجمی", callback_data="set_volume_config_price"),
                    types.InlineKeyboardButton("کانفیگ حجمی بدون تاریخ", callback_data="set_unlimited_volume_config_price"),
                    types.InlineKeyboardButton("کانفیگ نامحدود تک کاربر", callback_data="set_unlimited_config_one_price"),
                    types.InlineKeyboardButton("کانفیگ نامحدود دو کاربر", callback_data="set_unlimited_config_two_price"),
                    types.InlineKeyboardButton("کانفیگ نت ملی", callback_data="set_meli_config_price"),

                    types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel")
                )
                bot.send_message(
                    message.chat.id,
                    message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                user_states.pop(user_id, None) # Clear state after completion
            else:
                bot.send_message(message.chat.id, "❌ خطا: نوع کانفیگ مشخص نیست.")
                user_states.pop(user_id, None) # Clear state in case of error
                show_admin_panel(message)
        except ValueError:
            bot.send_message(message.chat.id, "❌ لطفاً فقط عدد وارد کنید.")
            # Keep the state so the user can re-enter the correct value
            if isinstance(user_states.get(user_id), dict) and "config_key" in user_states[user_id]:
                pass # Stay in the same state
            else: # Otherwise, clear state and return to admin panel
                user_states.pop(user_id, None) 
                show_admin_panel(message)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطایی رخ داد: {e}")
            user_states.pop(user_id, None) # Clear on general error
            show_admin_panel(message)
            
    elif state == "waiting_target_user_id_for_specific_prices":
        target_user_id_str = message.text.strip()
        
        # Ensure user_id is a numeric string
        if not target_user_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی کاربر نامعتبر است. لطفاً یک آیدی عددی صحیح وارد کنید:")
            ##user_states.pop(user_id, None) 
            ##show_admin_panel(message)
            return

        if not user_exists(target_user_id_str):
            bot.send_message(message.chat.id, f"❌ کاربری با آیدی `{target_user_id_str}` یافت نشد. لطفاً آیدی معتبر وارد کنید.")
            user_states.pop(user_id, None) 
            show_admin_panel(message)
            return

        user_states[user_id] = {"state": "setting_user_specific_price_type", "target_user_id": target_user_id_str}

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        
        message_text = f"قیمت‌های اختصاصی برای کاربر `{target_user_id_str}`:\n\n"
        user_specific_prices_dict = get_all_user_prices_from_user_table(target_user_id_str)
        
        for config_key, display_name in CONFIG_TYPE_NAMES.items():
            price_to_display = user_specific_prices_dict.get(config_key, 0) # Default value 0
            message_text += f"*{display_name}:*{add_commas(price_to_display)} تومان\n"

        message_text += "\nبرای تغییر یا تنظیم قیمت جدید، نوع کانفیگ را انتخاب کنید:"

        keyboard.add(
            types.InlineKeyboardButton(" کانفیگ حجمی", callback_data=f"set_specific_price_type_{target_user_id_str}_volume_config"),
            types.InlineKeyboardButton("کانفیگ حجمی بدون تاریخ", callback_data=f"set_specific_price_type_{target_user_id_str}_unlimited_volume_config"),
            types.InlineKeyboardButton("کانفیگ نامحدود تک کاربر", callback_data=f"set_specific_price_type_{target_user_id_str}_unlimited_config_one"),
            types.InlineKeyboardButton("کانفیگ نامحدود دو کاربر", callback_data=f"set_specific_price_type_{target_user_id_str}_unlimited_config_two"),
            types.InlineKeyboardButton("کانفیگ نت ملی", callback_data=f"set_specific_price_type_{target_user_id_str}_meli_config"),          
            types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel")
        )
        bot.send_message(
            message.chat.id,
            message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
            
    elif state == "waiting_user_specific_price_input":
            try:
                price = int(message.text.strip())
                target_user_id = user_states[user_id]["target_user_id"]
                config_type = user_states[user_id]["config_type"] # این config_type اکنون شامل نام کامل است
                print(config_type)
                if set_user_specific_price_in_user_table(target_user_id, config_type, price):
                    display_name = CONFIG_TYPE_NAMES.get(config_type, config_type)
                    bot.send_message(message.chat.id, f" قیمت *{display_name}* برای کاربر `{target_user_id}` تنظیم شد: {add_commas(price)} تومان✅", parse_mode='Markdown')
                else:
                    bot.send_message(message.chat.id, f"❌ خطا در تنظیم قیمت برای کاربر {target_user_id}.")
                
                # پس از تنظیم قیمت، دوباره لیست قیمت‌های اختصاصی کاربر را نمایش می‌دهیم.
                # این کار باعث می‌شود کاربر بتواند قیمت‌های دیگر را نیز تنظیم کند یا به پنل مدیریت بازگردد.
                user_states[user_id] = {"state": "setting_user_specific_price_type", "target_user_id": target_user_id}
                
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                message_text = f"قیمت‌های اختصاصی برای کاربر `{target_user_id}`:\n\n"
                
                user_specific_prices_dict = get_all_user_prices_from_user_table(target_user_id)
                for config_key, display_name_conf in CONFIG_TYPE_NAMES.items():
                    price_to_display = user_specific_prices_dict.get(config_key, 0)
                    message_text += f"*{display_name_conf}:* {add_commas(price_to_display)} تومان\n"
                
                message_text += "\nبرای تغییر یا تنظیم قیمت جدید، نوع کانفیگ را انتخاب کنید:"

                # !!! این دکمه‌ها همان‌هایی هستند که باید نام‌های کامل کانفیگ را به callback_data اضافه کنند !!!
                keyboard.add(
                    types.InlineKeyboardButton(" کانفیگ حجمی", callback_data=f"set_specific_price_type_{target_user_id}_volume_config"),
                    types.InlineKeyboardButton(" کانفیگ حجمی بدون تاریخ", callback_data=f"set_specific_price_type_{target_user_id}_unlimited_volume_config"),
                    types.InlineKeyboardButton(" کانفیگ نامحدود تک کاربر", callback_data=f"set_specific_price_type_{target_user_id}_unlimited_config_one"),
                    types.InlineKeyboardButton(" کانفیگ نامحدود دو کاربر", callback_data=f"set_specific_price_type_{target_user_id}_unlimited_config_two"), 
                    types.InlineKeyboardButton(" کانفیگ نت ملی", callback_data=f"set_specific_price_type_{target_user_id}_meli_config"),                   

                    types.InlineKeyboardButton("بازگشت به پنل مدیریت", callback_data="admin_panel")
                )
                bot.send_message(
                    message.chat.id,
                    message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
            except ValueError:
                bot.send_message(message.chat.id, "❌ لطفاً فقط عدد وارد کنید.")
                # در این حالت، وضعیت را حفظ می‌کنیم تا کاربر بتواند مجدداً ورودی صحیح را وارد کند.
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ خطایی رخ داد: {e}")
                user_states.pop(user_id, None)
                show_admin_panel(message)
        



    elif state == "waiting_user_id_for_list_users":
        target_user_id_str = message.text.strip()
        miniapp_subdomain = get_config_value("miniapp_subdomain")

        if not target_user_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی کاربر نامعتبر است. لطفاً یک آیدی عددی وارد کنید:")
            return

        if not user_exists(target_user_id_str):
            bot.send_message(
                message.chat.id,
                f"❌ کاربری با آیدی `{target_user_id_str}` یافت نشد. لطفاً آیدی معتبر وارد کنید:"
            )
            return

        username = get_telegram_id(target_user_id_str) or f"user_{target_user_id_str}"

        keyboard = types.InlineKeyboardMarkup()

        keyboard.add(
            types.InlineKeyboardButton(
                "📋 لیست کاربرها",
                web_app=types.WebAppInfo(
                    url=f"https://{miniapp_subdomain}/list.html?user_id={target_user_id_str}&telegram_id={username}"
                )
            )
        )

        keyboard.add(
            types.InlineKeyboardButton(
                "🔙 بازگشت به پنل مدیریت",
                callback_data="admin_panel"
            )
        )

        bot.send_message(
            message.chat.id,
            "👇 برای مشاهده لیست کاربران یا بازگشت به پنل یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=keyboard
        )




            
    # elif state == "waiting_panel_address":
    #     panel_address = message.text.strip()
    #     if not (panel_address.startswith("https://") or panel_address.startswith("http://")):
    #         bot.send_message(
    #             message.chat.id,
    #             "❌ آدرس پنل باید با `http://` یا `https://` شروع شود. لطفاً مجدداً وارد کنید:"
    #         )
    #         return
    #     user_states[user_id]["panel_address"] = panel_address 
    #     user_states[user_id]["state"] = "waiting_panel_is_unlimited"
    #     bot.send_message(message.chat.id, "نوع پنل را مشخص کنید:نامحدود،حجمی،نت ملی")

    # elif state == "waiting_panel_is_unlimited":
    #     is_unlimited_input = message.text.strip()
    #     if is_unlimited_input not in ("حجمی ","نت ملی", "نامحدود"):
    #         bot.send_message(message.chat.id, "❌ لطفاازاین موارد نامحدود،حجمی ،نت ملی یکی راانتخاب کنید.")
    #         return
    #     user_states[user_id]["is_unlimited"] = 1 if is_unlimited_input in ("نامحدود", "حجمی") else 0
    #     user_states[user_id]["panel_type"] =is_unlimited_input
    #     user_states[user_id]["state"] = "waiting_panel_capacity"
    #     bot.send_message(message.chat.id, "لطفاً ظرفیت پنل را وارد کنید:")

    # elif state == "waiting_panel_capacity":
    #     capacity_input = message.text.strip()
    #     if not capacity_input.isdigit():
    #         bot.send_message(message.chat.id, "❌ لطفاً یک عدد صحیح برای ظرفیت وارد کنید.")
    #         return
    #     user_states[user_id]["capacity"] = int(capacity_input)
    #     user_states[user_id]["state"] = "waiting_subscription_link"
    #     bot.send_message(message.chat.id, "لطفاً لینک سابسکریپشن را وارد کنید:")

    # elif state == "waiting_subscription_link":
    #     subscription_link = message.text.strip()
    #     if subscription_link.isdigit():
    #         bot.send_message(
    #             message.chat.id,
    #             "❌ دامنه یا ساب دامنه نمی‌تواند فقط عدد باشد. لطفاً دوباره وارد کنید."
    #         )
    #         return
    #     # گرفتن همه داده‌ها
    #     panel_type=(user_states[user_id]["panel_type"])
    #     panel_address = user_states[user_id]["panel_address"]
    #     is_unlimited = int(user_states[user_id]["is_unlimited"])
    #     capacity = user_states[user_id]["capacity"]
    #     alpha_status = single_with_retries_login_test('post', panel_address,data)
    #     if alpha_status != False:
    #         if alpha_status.get('success'):
    #             try:
    #                 if add_panel(panel_address, is_unlimited, capacity,subscription_link,panel_type):
    #                     bot.send_message(message.chat.id, "✅ پنل با موفقیت اضافه شد!")
    #                 else:
    #                     bot.send_message(message.chat.id, "❌ پنل مورد نظر تکراری است!")
    #             except:
    #                 bot.send_message(message.chat.id, "❌ لینک سابسکریپشن اشتباه است!")       
    #     else:
    #         bot.send_message(message.chat.id, "❌ پنل مورد نظر اشتباه وارد شده است!")

    #     user_states.pop(user_id, None)
    #     show_admin_panel(message)




    # elif state == "waiting_edit_capacity_panel":
    #     capacity_input = message.text.strip()
    #     if not capacity_input.isdigit():
    #         bot.send_message(message.chat.id, "❌ لطفاً یک عدد صحیح برای تغییر ظرفیت وارد کنید:")
    #         return
    #     user_states[user_id]["capacity"] = int(capacity_input)
    #     panel_id = user_states[user_id]["panel_id"]
    #     try:
    #       if change_capacity(panel_id,user_states[user_id]["capacity"]):
    #        bot.send_message(message.chat.id, "✅ ظرفیت پنل با موفقیت تغییر کرد!")
    #       else: 
    #         bot.send_message(message.chat.id, "❌ ظرفیت پنل تغییر پیدا نکرد!")
    #     except:
    #         bot.send_message(message.chat.id, "❌ اشتباهی در تغییر ظرفیت پنل به وجود آمد!")




    # elif state == "waiting_edit_sublink_panel":
    #     sublink = message.text.strip()
    #     if not (sublink.startswith("https://") or sublink.startswith("http://")):
    #         bot.send_message(
    #             message.chat.id,
    #             "❌ آدرس پنل باید با `http://` یا `https://` شروع شود. لطفاً مجدداً وارد کنید:"
    #         )
    #         return
    #     try:
    #         subscription_request=requests.post(sublink,timeout=5)
    #         #if "html" in subscription_request.text:
    #         if False:
    #             bot.send_message(message.chat.id, "❌ لینک سابسکریپشن اشتباه است!") 
    #         else:
    #             user_states[user_id]["sublink"] = sublink
    #             panel_id = user_states[user_id]["panel_id"]
    #             if change_subscription(panel_id,user_states[user_id]["sublink"]):
    #               bot.send_message(message.chat.id, "✅ لینک سابسکریپشن با موفقیت تغییر کرد!")
    #             else:
    #               bot.send_message(message.chat.id, "❌ لینک سابسکریپشن تغییر پیدا نکرد!")
                     
    #     except:
    #         bot.send_message(message.chat.id, "❌ اشتباهی در تغییر لینک سابسکریپشن به وجود آمد!")







    else:
        if message.text != '/start':
            bot.send_message(
                message.chat.id,
                "❓ دستور نامشخص. لطفاً از منو استفاده کنید یا /start بزنید."
            )









# --- تابع هندل کردن ورودی هش تراکنش ---
def handle_txid_input(message):
    user_id = message.from_user.id
    text = message.text.strip()
    user_id = message.from_user.id  # آیدی عددی تلگرام کاربر
    username = message.from_user.username or f"user_{user_id}"  # اگر username نداشت یک پیشفرض بساز
    if text.startswith("/"):
        bot.send_message(message.chat.id, "⛔️ دستور جدید ثبت شد. مرحله شارژ لغو شد.")
        user_states.pop(user_id, None)
        return

    # آدرس کیف پول ترون خود را اینجا قرار دهید
    wallet = "TTvAaQ2EK3T83JF3Rg5undK83paXrHr1hF" 
    txid = text

    print(f"📥 دریافت TXID از {user_id}: {txid}")

    result= check_trx_transfer(txid, wallet)
    print(f"🔍 نتیجه بررسی بلاک‌چین: {result}")

    if result is None:
        bot.send_message(message.chat.id, "❌ تراکنش یافت نشد یا مشکلی در ارتباط با بلاک‌چین وجود دارد.\n🔁 لطفاً یک هش معتبر وارد کنید یا بعداً تلاش کنید.")
        return
    
    if isinstance(result, str) and result.startswith("❌"): # پیام خطای اختصاصی از check_trx_transfer
        bot.send_message(message.chat.id, result + "\n🔁 لطفاً مجدد تلاش کنید:")
        return

    if not isinstance(result, (int, float)): # اگر نتیجه عددی نبود (مثل "آدرس مقصد مطابقت ندارد")
        bot.send_message(message.chat.id, "❌ مشکلی در اعتبار سنجی تراکنش شما پیش آمد.\n🔁 لطفاً مجدد تلاش کنید:")
        return

    if is_txid_already_used(txid):
        bot.send_message(message.chat.id, "⚠️ این تراکنش قبلاً استفاده شده است.\n🔁 لطفاً یک هش جدید وارد کنید:")
        return

    # افزودن هش تراکنش به دیتابیس (برای جلوگیری از تکرار)
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # در اینجا فرض بر این است که ستون 'hash' در جدول 'users' برای ذخیره آخرین هش استفاده شده است.
        # اگر کاربر وجود دارد، هش را به‌روزرسانی می‌کنیم، در غیر این صورت کاربر جدید با هش و موجودی اولیه صفر ایجاد می‌کنیم.
        c.execute("SELECT COUNT(*) FROM payments WHERE hash_order = ?", (txid,))
        hash_result=c.fetchone()[0]
        result_with_bonus = int(result * 1.1)
        if hash_result == 0:
            c.execute("INSERT INTO payments (username,telegram_id,hash_order,price) VALUES (?,?,?,?)", (str(user_id),username,txid,add_commas(result_with_bonus)))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error saving txid to database: {e}")
    finally:
        conn.close()
    result_with_bonus = int(result * 1.1)
    update_balance_and_hash(result_with_bonus, str(user_id)) # فقط موجودی را افزایش می‌دهد.
    bonus_amount=int(result*0.1)
    trx_amount=get_trx_amount(txid,wallet)
    RLM = "\u200F"  # Right-to-Left Mark
    bot.send_message(
        message.chat.id,
        f"{RLM}🎉 {add_commas(result * 1.1)} تومان با موفقیت به کیف پول شما اضافه شد!\n"
        f"{RLM}💎 شارژ هدیه: {add_commas(bonus_amount)} تومان\n"
        f"{RLM}🔺مقدار ترون واریز شده:{trx_amount}ترون",
        parse_mode="Markdown"
    )    
    
 
    
    
    user_states.pop(user_id, None)
    show_main_menu(message)

# --- شروع به گوش دادن به پیام‌ها ---
bot.infinity_polling()
