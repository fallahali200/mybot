from flask import Flask, request, jsonify, send_from_directory,render_template
import telebot
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
import re
import math
import secrets
from urllib.parse import quote
import concurrent.futures
from datetime import datetime
# ---------- تنظیمات اولیه ----------
# ---------- تنظیمات اولیه ----------
login_url =  'login'
list_inbound='panel/api/inbounds/list'
add_inbound =  'panel/api/inbounds/add'
add_client='panel/api/inbounds/addClient'
delete_client='panel/api/inbounds/'
update_client='panel/api/inbounds/updateClient/'
delete_inbound='panel/api/inbounds/del/'
reset_traffic='panel/api/inbounds/'
update_inbound='panel/api/inbounds/update/'
get_traffic_client='panel/api/inbounds/getClientTraffics/' 
update_traffic_client='panel/api/inbounds/updateClientTraffic/'
reset_all_traffic_client='panel/api/inbounds/resetAllClientTraffics'
reset_all_traffic_inbounds='panel/api/inbounds/resetAllTraffics'                                                                 
reset_client_traffic='panel/api/inbounds/resetClientTraffic'
delete_client_by_email='panel/api/inbounds/delClientByEmail/'
api_clients_list = "panel/api/clients/list"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}
# ---------- تنظیمات ربات ----------
API_TOKEN = "8872814549:AAHpFjlg-5sX_QuQMv3p9gFp60wl3vylKdw"
bot = telebot.TeleBot(API_TOKEN)

# ---------- تنظیمات Flask ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)



def get_balance(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

    

def update_balance(username, new_balance):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username))
    conn.commit()
    conn.close()
    
    



def get_config_value(key):
    """یک مقدار پیکربندی را از جدول bot_config (قیمت‌های عمومی) برمی‌گرداند."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT config_value FROM bot_config WHERE config_key = ?", (key,))
        result = c.fetchone()
        return result[0] if result else '0' # اگر مقداری یافت نشد، '0' برگردانده شود
    finally:
        conn.close()




    
def get_user_full_name(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE username = ?", (user_id,))
    full_name = c.fetchone()
    conn.close()
    return full_name[0]    
    
    
    
def add_bonus(username, price):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # بررسی اینکه کاربر و parentش وجود دارند
    c.execute("SELECT parent FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return None  # کاربر پیدا نشد
    
    parent = result[0]

    # فقط اگر parent وجود دارد
    if parent:
        full_name=get_user_full_name(username)
        # اینجا می‌تونی پاداش به parent بدهی، مثلاً ۵٪ از new_balance:
        bonus = price * 0.05
        message_text = (
            f"💰کاربر {full_name} یک خرید به مبلغ {add_commas(int(price))} تومان انجام داد و\n"
            f" {add_commas(int(bonus))} تومان معادل (۵٪) به کیف پول شما اضافه شد! \n"
        )
        c.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (bonus,parent))
        conn.commit()
        bot.send_message(parent,message_text)
    else:
        print(f"❌ کاربر {username} هیچ parent ندارد. پاداش اعمال نشد.")

    conn.close()
    
    
def random_string(length):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
   
   
   
def gb_to_bytes(gb_value):
    """تبدیل گیگابایت به بایت"""
    return int(gb_value * (1024 ** 3))  
 
def bytes_to_gigabytes(bytes_value):
    return round(bytes_value / (1024 ** 3), 2)  # بر حسب گیگابایت با دقت دو رقم اعشار
   
def send_qrcode(text, user_id, title=""):
    # ساخت QR کد
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    # تبدیل به بایت
    bio = BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)

    # ارسال عکس QR با کپشن عنوان و ذخیره پیام
    photo_message = bot.send_photo(user_id, bio, caption=title)

    # ارسال لینک با ایموجی 👇 و گرفتن message_id پیام ارسالی
    text_message = bot.send_message(user_id, text)

    # تابع حذف پیام‌ها بعد ۱۰ دقیقه
    def delete_later():
        time.sleep(600)  # 10 دقیقه
        try:
            bot.delete_message(user_id, photo_message.message_id)
        except Exception as e:
            print(f"خطا در حذف پیام عکس: {e}")

        try:
            bot.delete_message(user_id, text_message.message_id)
        except Exception as e:
            print(f"خطا در حذف پیام متن: {e}")

    # اجرای حذف پیام‌ها در یک Thread جدا
    threading.Thread(target=delete_later).start()





def insert_sql(username,telegram_id,panel_id,panel,subscription_link,created_at,subid,config_name,expire_days=30):

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO services (username,telegram_id,panel_id,panel,subscription_link,created_at,subid,config_name,expire_days)
        VALUES (?, ?, ?,?,?,?,?,?,?)
    ''', (username,telegram_id,panel_id,panel ,subscription_link,created_at,subid,config_name,expire_days))

    conn.commit()
    conn.close()



def delete_sql(username, subid):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
        DELETE FROM services
        WHERE username = ? AND subid = ?
    ''', (username, subid))

    conn.commit()
    conn.close()




def update_sql(config_name,timestamp, username, subid,expire_days):

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    now = int(time.time() * 1000)
    c.execute('''
        UPDATE services
        SET created_at =? , config_name=?, time = ?,expire_days = ?
        WHERE username = ? AND subid = ?
    ''', (now,config_name,timestamp,expire_days, username, subid))

    conn.commit()
    conn.close()


def get_expiry_timestamp(days):
    now = int(time.time() * 1000)  # زمان فعلی به میلی ثانیه
    expiry = now + (days * 24 * 60 * 60 * 1000) if days > 0 else 0
    return expiry



def calculate_expire_days(expiry_timestamp):
    if expiry_timestamp is None or not isinstance(expiry_timestamp, (int, float)):
        return 29  # 30 روز پیش‌فرض → 1 روز کمتر

    abs_expiry = abs(expiry_timestamp)
    now = int(time.time() * 1000)  # زمان فعلی به میلی‌ثانیه
    diff = abs_expiry - now

    one_day_ms = 1000 * 60 * 60 * 24  # تعداد میلی‌ثانیه در یک روز

    if diff > 0:
        return max(math.ceil(diff / one_day_ms), 0)
    else:
        return 0



def get_all_times(username, subid):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT expire_days FROM services WHERE username = ? AND subid = ?", (username, str(subid)))
    times = [row[0] for row in c.fetchall()]
    conn.close()
    return times









def get_all_enables(username, subid):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT config_status FROM services WHERE username = ? AND subid = ?", (username, str(subid)))
    times = [row[0] for row in c.fetchall()]
    conn.close()
    return times



def show_totals(panel):
    response_data = single_with_retries('get',panel+ api_clients_list)

    
    if not response_data.get("success"):
        print(f"❌ پنل {panel} موفق به دریافت لیست نشد.")
        return 0

    clients = response_data.get("obj", [])
    
    # تعداد کل کاربران به سادگی با گرفتن طول آرایه مشخص می‌شود
    total_clients = len(clients)
    print(total_clients,1000)

    return total_clients





def get_all_panels_with_capacity():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM panels ")
    rows = c.fetchall()

    conn.close()

    return [dict(row) for row in rows]






def get_specific_panel_with_capacity(panel_id):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT * FROM panels WHERE id = ?",
        (panel_id,)
    )

    row = c.fetchone()
    conn.close()

    return dict(row) if row else None



def get_specific_panel_with_address(panel):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT * FROM panels WHERE panel_address = ?",
        (panel,)
    )

    row = c.fetchone()
    conn.close()

    return dict(row) if row else None








def get_panels_with_capacity_unlimited(is_unlimited, panel_type):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT * FROM panels WHERE is_unlimited = ? AND panel_type = ? ",
        (int(is_unlimited), panel_type)
    )

    rows = c.fetchall()
    conn.close()

    return [dict(row) for row in rows]





def get_panels_with_capacity(is_unlimited):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT * FROM panels WHERE is_unlimited = ?",
        (int(is_unlimited),)
    )

    rows = c.fetchall()
    conn.close()

    return [dict(row) for row in rows]
    





                    
def single_with_retries(
    method,
    url,
    data=None,
    json=None,
    max_retries=5
):
    panel_match = re.match(r"^(.*?)(?=panel)", url)

    if not panel_match:
        raise ValueError(f"Invalid panel URL: {url}")

    panel_url = panel_match.group(1)

    panel_data = get_specific_panel_with_address(panel_url)

    session = requests.Session()

    login_data = {
        "username": "admin",
        "password": "admin"
    }

    # Login اولیه
    try:
        login_res = session.post(
            panel_url + login_url,
            json=login_data,
            timeout=5
        )

        if login_res.status_code != 200:
            print("⚠️ Login اولیه شکست خورد.")

    except Exception as e:
        print(f"⚠️ خطا در Login اولیه: {e}")

    response_data = None

    backoff_base = 1
    max_backoff = 2

    for attempt in range(max_retries):

        try:
            # -------------------------
            # POST
            # -------------------------
            if method.lower() == "post":

                if data is not None:
                    response = session.post(
                        url=url,
                        data=data,
                        timeout=10
                    )

                elif json is not None:
                    response = session.post(
                        url=url,
                        json=json,
                        timeout=10
                    )

                else:
                    response = session.post(
                        url=url,
                        timeout=10
                    )

            # -------------------------
            # GET
            # -------------------------
            else:

                if data is not None:
                    response = session.get(
                        url=url,
                        params=data,
                        timeout=10
                    )

                elif json is not None:
                    response = session.get(
                        url=url,
                        json=json,
                        timeout=10
                    )

                else:
                    response = session.get(
                        url=url,
                        timeout=10
                    )

            response_data = response.json()

            if response_data.get("success"):
                print(
                    f"✅ درخواست در تلاش {attempt + 1} موفق بود."
                )
                return response_data

            raise Exception(
                f"API response unsuccessful: {response_data}"
            )

        except Exception as e:

            print(
                f"❌ تلاش {attempt + 1} برای درخواست "
                f"به {url} ناموفق بود: {e}"
            )

            # -------------------------
            # Login مجدد
            # -------------------------
            try:
                session.close()
            except:
                pass

            session = requests.Session()

            try:
                login_res = session.post(
                    panel_url + login_url,
                    json=login_data,
                    headers=headers,
                    timeout=5
                )

                if (
                    login_res.status_code != 200
                    or not login_res.json().get("success")
                ):
                    print("⚠️ لاگین مجدد هم شکست خورد.")

            except Exception as login_error:
                print(
                    f"⚠️ خطا در لاگین مجدد: {login_error}"
                )

            # -------------------------
            # # Delay
            # # -------------------------
            # if attempt < max_retries - 1:

            #     delay = min(
            #         backoff_base * (2 ** attempt),
            #         max_backoff
            #     )

            #     print(
            #         f"⏳ تاخیر {delay} ثانیه قبل از "
            #         f"تلاش مجدد..."
            #     )

            #     time.sleep(delay)

    print("🚨 تمام تلاش‌ها شکست خورد.")

    return response_data




def choose_panel_meli():

    panels = get_panels_with_capacity('0')

    for panel in panels:
        print(panel['panel_address'])
        current_users = show_totals(panel['panel_address'])

        if current_users >= panel["capacity"] or panel['status'] == 0:
            continue
        
        get_inbound = [int(x) for x in panel['get_inbound'].split(",")]
        token = panel.get("token")
        if not token:
            continue
        return panel['id'],panel['panel_address'],panel['subscription_link'],get_inbound,panel['name']




def choose_panel_direct():

    panels = get_panels_with_capacity_unlimited('1', 'حجمی')

    for panel in panels:
        print(panel['panel_address'])
        current_users = show_totals(panel['panel_address'])

        if current_users >= panel["capacity"] or panel['status'] == 0:
            continue
        
        get_inbound = [int(x) for x in panel['get_inbound'].split(",")]
        token = panel.get("token")
        if not token:
            continue
        return panel['id'],panel['panel_address'],panel['subscription_link'],get_inbound,panel['name']





def choose_panel_unlimited():

    panels = get_panels_with_capacity_unlimited('1', 'نامحدود')

    for panel in panels:
        print(panel['panel_address'])
        current_users = show_totals(panel['panel_address'])

        if current_users >= panel["capacity"] or panel['status'] == 0:
            continue
        get_inbound = [int(x) for x in panel['get_inbound'].split(",")]
        token = panel.get("token")
        if not token:
            continue
        print(1000000)
        return panel['id'],panel['panel_address'],panel['subscription_link'],get_inbound,panel['name']




def post_with_retries(method,url, json=None, max_retries=10):
    panels=get_all_panels_with_capacity()
    result=[]     
    for panel in panels:
     attempt = 0
     response_data = None
     backoff_base = 1  # زمان اولیه تاخیر (1 ثانیه)
     max_backoff = 2  # حداکثر زمان backoff (10 ثانیه)
     session = requests.session()
     data = {
        'username': 'admin',
        'password': 'admin'
    }
     alpha = session.post(panel['panel_address']+login_url, json=data, timeout=5)
     while attempt < max_retries:
         try:
             if json is not None:
                 if method.lower() == "post":
                     response = session.post(panel['panel_address']+url, json=json, timeout=10)
                 else:
                     response = session.get(panel['panel_address']+url, json=json, timeout=10)

             else:
                 if method.lower() == "post":
                     response = session.post(panel['panel_address']+url, timeout=10)
                 else:
                     response = session.get(panel['panel_address']+url, timeout=10)  

             response_data = response.json()

             if response_data.get("success"):
                    result.append((response_data,panel['id'],panel['panel_address'],panel['is_unlimited'],panel['subscription_link'],panel['name'],panel['get_inbound']
                                   
                                   ))  # اضافه کردن به لیست نتایج
                    break  # موفقیت‌آمیز بود
             else:
                 raise Exception("API response unsuccessful")



         except Exception as e:
             print(f"❌ تلاش {attempt+1} برای درخواست به {panel['panel_address']+url} ناموفق بود: {e}")
             # تلاش برای لاگین مجدد
             session.close()
             session = requests.Session()
             login_res = session.post(panel['panel_address']+'login', json=data, headers=headers)
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
    return result







def get_panel_stats(row,panel_id):
    """وضعیت فعلی تانل پنل مشخص را برمی‌گرداند (ON/OFF)."""
    conn = sqlite3.connect('users.db') 
    c = conn.cursor()
    try:
        c.execute(f"SELECT {row} FROM panels WHERE id = ?", (panel_id,))
        result = c.fetchone()
        return result[0]
    finally:
        conn.close()








def user_exists(user_id):
    conn = sqlite3.connect('users.db')  # مسیر دیتابیس‌ات رو بزن
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE username = ? AND is_friend = 1", (user_id,))
    result = cursor.fetchone()

    conn.close()

    return result is not None



def get_specific_price(price,user_id):
    conn = sqlite3.connect('users.db')  # مسیر دیتابیس‌ات رو درست کن
    cursor = conn.cursor()

    cursor.execute(f"SELECT {price} FROM users WHERE username = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return float(result[0])  # مقدار volume_config_price
    else:
        return None  # کاربر پیدا نشد



def get_price_for_all(config_key):
    conn = sqlite3.connect('users.db')  # مسیر دیتابیس‌ات رو درست کن
    cursor = conn.cursor()
    cursor.execute("SELECT config_value FROM bot_config WHERE config_key = ?", (config_key,))
    result = cursor.fetchone()
    if result:
        return float(result[0])  # فرض می‌کنیم قیمت عددی هست
    else:
        return None  # یا مقدار پیش‌فرض

def add_commas(number):
    return "{:,}".format(number)




# ---------- روت‌های Flask ----------


@app.route('/payment-callback', methods=['POST'])
def payment_callback():
    try:
        # گرفتن پارامترهای URL
        user_id = request.args.get("user_id")
        username = request.args.get("username")
        amount_str= request.args.get("amount")
        amount=int(amount_str)
        user_id = int(user_id)

        # گرفتن JSON ارسال‌شده توسط tetra98
        data = request.get_json()
        print("CALLBACK DATA:", data)

        status = data.get("status")          # باید 100 باشد
        authority = data.get("authority")    # برای verify لازم است
        hashid = data.get("hashid")          # همان Hash_id سفارش
        
        # اگر status != 100 یعنی پرداخت از سمت بانک تأیید نشد
        if status != 100:
            bot.send_message(
                user_id,
                "❌ پرداخت انجام نشد یا توسط شما لغو شد."
            )
            return jsonify({"success": False}), 400

        # -----------------------
        # 🔵 مرحله verify
        # -----------------------
        verify_payload = {
            "authority": authority,
            "ApiKey": "fe9decb5da565d5b4bc866b05d915e20"
        }

        verify_res = requests.post("https://tetra98.ir/api/verify", json=verify_payload)
        verify_data = verify_res.json()

        print("VERIFY RESULT:", verify_data)

        # بررسی نهایی
        if verify_data.get("status") == 100:
            order_id = verify_data.get("order_id", hashid)
            ref_id = verify_data.get("ref_id", "unknown")

            # -----------------------
            #  🔵 افزایش موجودی کاربر
            # -----------------------
            balance = get_balance(user_id)
            new_balance = balance + amount
            update_balance(user_id, new_balance)

            # ذخیره در دیتابیس
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO payments (username, telegram_id, hash_order, price) VALUES (?,?,?,?)",
                    (username, user_id, order_id, add_commas(amount))
                )
                conn.commit()
            finally:
                conn.close()

            # پیام به کاربر
            RLM = "\u200F"
            text = (
                f"{RLM}🎉 پرداخت شما با موفقیت تأیید شد!\n"
                f"{RLM}💳 مبلغ واریزی: {add_commas(amount)} تومان\n"
                f"{RLM}🧾 شماره سفارش: {order_id}\n"
                f"{RLM}🔢 شماره پیگیری بانک: {ref_id}\n"
                f"{RLM}💰 موجودی قبلی: {add_commas(balance)} تومان\n"
                f"{RLM}💰 موجودی جدید: {add_commas(new_balance)} تومان\n"
            )

            bot.send_message(user_id, text, parse_mode="Markdown")
            print(f"✅ پرداخت موفق برای کاربر {user_id} — سفارش {order_id}")

            return jsonify({"success": True}), 200

        else:
            # verify ناموفق
            bot.send_message(
                user_id,
                "❌ پرداخت شما توسط سیستم بانکی تأیید نشد. اگر مبلغ کم شد، طی 72 ساعت برگشت می‌خورد."
            )
            print(f"❌ VERIFY FAILED for user {user_id} / authority {authority}")
            return jsonify({"success": False}), 400

    except Exception as e:
        print("Callback ERROR:", e)
        try:
            bot.send_message(
                user_id,
                "❌ خطا در پردازش پرداخت. اگر وجه کسر شده طی 72 ساعت برگشت می‌خورد."
            )
        except:
            pass
        return jsonify({"success": False}), 500

     





@app.route('/add.html')
def add():
    user_id = request.args.get('user_id')
    telegram_id = request.args.get('telegram_id')
    balance=get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"
    has_capacity = check_capacity_logic()
    if user_exists(user_id):
        unlimited_volume_config_price = get_specific_price('unlimited_volume_config_price',user_id)
        meli_config_price = get_specific_price('meli_config_price', user_id)
        price_tuple=(unlimited_volume_config_price,meli_config_price)    
    else:
        unlimited_volume_config_price = get_price_for_all('unlimited_volume_config_price')
        meli_config_price = get_price_for_all('meli_config_price') 
        price_tuple=(unlimited_volume_config_price,meli_config_price)      
    return render_template( 'add.html',balance=balance_formatted,has_capacity =has_capacity,price_tuple=price_tuple )
   
 
   
@app.route('/add_unlimited.html')
def add_unlimited():
    user_id = request.args.get('user_id')
    telegram_id = request.args.get('telegram_id')
    balance=get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"
    has_capacity = check_capacity_logic_unlimited()
    
    if user_exists(user_id):
            unlimited_config_one_price = get_specific_price('unlimited_config_one_price',user_id)
            unlimited_config_two_price = get_specific_price('unlimited_config_two_price',user_id)
            unlimited_config_price=(unlimited_config_one_price,unlimited_config_two_price)
    else:
            unlimited_config_one_price = get_price_for_all('unlimited_config_one_price')
            unlimited_config_two_price = get_price_for_all('unlimited_config_two_price') 
            unlimited_config_price=(unlimited_config_one_price,unlimited_config_two_price)
            print(unlimited_config_price) 
    return render_template( 'add_unlimited.html',balance=balance_formatted,has_capacity =has_capacity,unlimited_config_price=unlimited_config_price)


@app.route('/add_direct.html')
def add_direct():
    user_id = request.args.get('user_id')
    telegram_id = request.args.get('telegram_id')
    balance=get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"
    has_capacity = check_capacity_logic_direct()
    if user_exists(user_id):
        unlimited_volume_config_price = get_specific_price('unlimited_volume_config_price',user_id)
        volume_config_price = get_specific_price('volume_config_price', user_id)
        price_tuple=(unlimited_volume_config_price,volume_config_price)    
    else:
        unlimited_volume_config_price = get_price_for_all('unlimited_volume_config_price')
        volume_config_price = get_price_for_all('volume_config_price') 
        price_tuple=(unlimited_volume_config_price,volume_config_price)      
    return render_template( 'add_direct.html',balance=balance_formatted,has_capacity =has_capacity,price_tuple=price_tuple )




@app.route('/list.html')
def serve_list():

    user_id = request.args.get('user_id')

    # -----------------------------
    # balance
    # -----------------------------
    balance = get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"

    # -----------------------------
    # API
    # -----------------------------
    list_results = post_with_retries('get', api_clients_list)

    all_clients = []

    # -----------------------------
    # loop panels
    # -----------------------------
    for res, panel_id, panel_address, is_unlimited, subscription_link,server_name,get_inbound in list_results:

        if not isinstance(res, dict):
            continue

        if not res.get("success"):
            continue

        clients = res.get("obj", [])
        clients = clients.get("rows", [])

        # -----------------------------
        # loop clients مستقیم
        # -----------------------------
        for client in clients:
            uuid = client.get("memberships", [{}])[0].get("clientId")
            email = client.get("email", "")
            # فقط user خودش
            if str(user_id) not in email:
                continue
            traffic = client.get("traffic", {})
            email_changed=  client.get("email", "").split("_")[1] 
            email_changed = email_changed.replace(server_name, "")
            my_expire_values = get_all_times(user_id, client.get('subId', 'N/A'))
            my_expire = my_expire_values[0] if my_expire_values else 'N/A'
            my_status = 1 if client.get('enable') == True else 0

            # -----------------------------
            # DB
            # -----------------------------
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute(
                "SELECT created_at FROM services WHERE subid=? LIMIT 1",
                (client.get('subId', ''),)
            )
            row = c.fetchone()
            created_at = int(row[0]) if row else 0
            conn.close()
            client_config = {
                "panel_id": panel_id,
                "panel": panel_address,
                "is_unlimited": is_unlimited,
                "subscription_link": subscription_link,
                "id": client.get("id"),
                "email": email_changed,
                "subId": client.get("subId"),
                "enable":client.get("enable"),
                "uuid": uuid,
                "unchanged_email":email,
                "enable": client.get("enable"),
                "totalGB": client.get("totalGB"),
                "total": client.get("totalGB"),
                'flow': client.get('flow'),
                'auth':client.get('auth'),
                'limitip': client.get('limitIp'),
                'tgld': client.get('tgId'),                
                'password':client.get('password'),
                'comment': client.get('comment'),
                "expiryTime": client.get("expiryTime"),
                'server_name': server_name, 
                "up": client.get("up"),
                "down": client.get("down"),
                "comment": client.get("comment"),
                'my_expire': my_expire,
                "created_at": created_at,
                'config_status': my_status,
                'mytime': client.get('expiryTime'),
                'reset': client.get('reset'),
                "InboundIDs":get_inbound

            }

            all_clients.append(client_config)
            print(all_clients)

    # -----------------------------
    # sort
    # -----------------------------
    sorted_clients = sorted(
        all_clients,
        key=lambda x: x["created_at"],
        reverse=True
    )
    return render_template(
        'list.html',
        balance=balance_formatted,
        clients={
            "clients": sorted_clients,
            "balance": balance
        }
    )






@app.route('/update.html')
def serve_list2():
    user_id = request.args.get('user_id')
    telegram_id = request.args.get('telegram_id')
    balance=get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"
    if user_exists(user_id):
     unlimited_volume_config_price = get_specific_price('unlimited_volume_config_price',user_id)
     meli_config_price = get_specific_price('meli_config_price', user_id)
     price_tuple=(unlimited_volume_config_price,meli_config_price)    
    else:
     unlimited_volume_config_price = get_price_for_all('unlimited_volume_config_price')
     meli_config_price = get_price_for_all('meli_config_price') 
     price_tuple=(unlimited_volume_config_price,meli_config_price)  
    return render_template( 'update.html',balance=balance_formatted,price_tuple=price_tuple)




@app.route('/update_direct.html')
def update_direct():
    user_id = request.args.get('user_id')
    telegram_id = request.args.get('telegram_id')
    balance=get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"
    if user_exists(user_id):
     unlimited_volume_config_price = get_specific_price('unlimited_volume_config_price',user_id)
     volume_config_price = get_specific_price('volume_config_price', user_id)
     price_tuple=(unlimited_volume_config_price,volume_config_price)    
    else:
     unlimited_volume_config_price = get_price_for_all('unlimited_volume_config_price')
     volume_config_price = get_price_for_all('volume_config_price') 
     price_tuple=(unlimited_volume_config_price,volume_config_price)  
    return render_template( 'update_direct.html',balance=balance_formatted,price_tuple=price_tuple)



@app.route('/update_unlimited.html')
def update_unlimited():
    user_id = request.args.get('user_id')
    telegram_id = request.args.get('telegram_id')
    balance=get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"
    if user_exists(user_id):
            unlimited_config_one_price = get_specific_price('unlimited_config_one_price',user_id)
            unlimited_config_two_price = get_specific_price('unlimited_config_two_price',user_id)
            unlimited_config_price=(unlimited_config_one_price,unlimited_config_two_price)
    else:
            unlimited_config_one_price = get_price_for_all('unlimited_config_one_price')
            unlimited_config_two_price = get_price_for_all('unlimited_config_two_price') 
            unlimited_config_price=(unlimited_config_one_price,unlimited_config_two_price) 
    print(unlimited_config_price)        
    return render_template( 'update_unlimited.html',balance=balance_formatted,unlimited_config_price=unlimited_config_price)








def check_capacity_logic_unlimited():
    panels = get_panels_with_capacity_unlimited('1', 'نامحدود')
    for panel in panels:
        status = panel.get('status')

        # ⛔ اگر status = 0 بود، کلاً ردش کن
        if str(status).strip() == '0':
            continue

        response_data = single_with_retries('get',panel['panel_address'] + api_clients_list)

        if not response_data or not response_data.get("success"):
            print(f"❌ پنل {panel['panel_address']} موفق به دریافت لیست کاربران نشد.")
            continue

        # در API جدید، obj مستقیماً آرایه‌ای از کلاینت‌هاست
        clients = response_data.get("obj", [])
        
        # تعداد کل کاربران به سادگی با گرفتن طول آرایه مشخص می‌شود
        total_clients = len(clients)
        print(f"تعداد کاربران فعلی: {total_clients}")

        # محاسبه ظرفیت باقی‌مانده
        remaining = panel.get('capacity', 0) - total_clients
        print(f"📌 پنل {panel['panel_address']} ظرفیت باقی‌مانده: {remaining}")

        if remaining > 0:
            return True

    return False






def check_capacity_logic_direct():
    panels = get_panels_with_capacity_unlimited('1','حجمی')
    for panel in panels:
        status = panel.get('status')

        # ⛔ اگر status = 0 بود، کلاً ردش کن
        if str(status).strip() == '0':
            continue

        response_data = single_with_retries('get',panel['panel_address'] + api_clients_list)
        print(response_data)

        if not response_data or not response_data.get("success"):
            print(f"❌ پنل {panel['panel_address']} موفق به دریافت لیست کاربران نشد.")
            continue

        # در API جدید، obj مستقیماً آرایه‌ای از کلاینت‌هاست
        clients = response_data.get("obj", [])
        
        # تعداد کل کاربران به سادگی با گرفتن طول آرایه مشخص می‌شود
        total_clients = len(clients)
        print(f"تعداد کاربران فعلی: {total_clients}")

        # محاسبه ظرفیت باقی‌مانده
        remaining = panel.get('capacity', 0) - total_clients
        print(f"📌 پنل {panel['panel_address']} ظرفیت باقی‌مانده: {remaining}")

        if remaining > 0:
            return True

    return False




def check_capacity_logic():
    panels = get_panels_with_capacity('0')

    for panel in panels:
        status = panel.get('status')

        # ⛔ اگر status = 0 بود، کلاً ردش کن
        if str(status).strip() == '0':
            continue

        response_data = single_with_retries('get',panel['panel_address'] + api_clients_list)

        if not response_data or not response_data.get("success"):
            print(f"❌ پنل {panel['panel_address']} موفق به دریافت لیست کاربران نشد.")
            continue

        # در API جدید، obj مستقیماً آرایه‌ای از کلاینت‌هاست
        clients = response_data.get("obj", [])
        
        # تعداد کل کاربران به سادگی با گرفتن طول آرایه مشخص می‌شود
        total_clients = len(clients)
        print(f"تعداد کاربران فعلی: {total_clients}")

        # محاسبه ظرفیت باقی‌مانده
        remaining = panel.get('capacity', 0) - total_clients
        print(f"📌 پنل {panel['panel_address']} ظرفیت باقی‌مانده: {remaining}")

        if remaining > 0:
            return True

    return False

  



@app.route('/get_balance')
def get_balance_route():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'balance': 0})
    balance = get_balance(user_id)
    return jsonify({'balance': balance})






@app.route('/list_users')
def list_users():
    user_id = request.args.get('user_id')

    # -----------------------------
    # balance
    # -----------------------------
    balance = get_balance(user_id)
    balance_formatted = f"{balance:,.0f}"

    # -----------------------------
    # API
    # -----------------------------
    list_results = post_with_retries('get', api_clients_list)

    all_clients = []

    # -----------------------------
    # loop panels
    # -----------------------------
    for res, panel_id, panel_address, is_unlimited, subscription_link,server_name,get_inbound in list_results:

        if not isinstance(res, dict):
            continue

        if not res.get("success"):
            continue

        clients = res.get("obj", [])
        clients = clients.get("rows", [])

        # -----------------------------
        # loop clients مستقیم
        # -----------------------------
        for client in clients:
            uuid = client.get("memberships", [{}])[0].get("clientId")
            email = client.get("email", "")
            # فقط user خودش
            if str(user_id) not in email:
                continue
            traffic = client.get("traffic", {})
            email_changed=  client.get("email", "").split("_")[1] 
            email_changed = email_changed.replace(server_name, "")
            my_expire_values = get_all_times(user_id, client.get('subId', 'N/A'))
            my_expire = my_expire_values[0] if my_expire_values else 'N/A'
            my_status = 1 if client.get('enable') == True else 0

            # -----------------------------
            # DB
            # -----------------------------
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute(
                "SELECT created_at FROM services WHERE subid=? LIMIT 1",
                (client.get('subId', ''),)
            )
            row = c.fetchone()
            created_at = int(row[0]) if row else 0
            conn.close()
            client_config = {
                "panel_id": panel_id,
                "panel": panel_address,
                "is_unlimited": is_unlimited,
                "subscription_link": subscription_link,
                "id": client.get("id"),
                "email": email_changed,
                "subId": client.get("subId"),
                "enable":client.get("enable"),
                "uuid": uuid,
                "unchanged_email":email,
                "enable": client.get("enable"),
                "totalGB": client.get("totalGB"),
                "total": client.get("totalGB"),
                'flow': client.get('flow'),
                'auth':client.get('auth'),
                'limitip': client.get('limitIp'),
                'tgld': client.get('tgId'),                
                'password':client.get('password'),
                'comment': client.get('comment'),
                "expiryTime": client.get("expiryTime"),
                'server_name': server_name, 
                "up": client.get("up"),
                "down": client.get("down"),
                "comment": client.get("comment"),
                'my_expire': my_expire,
                "created_at": created_at,
                'config_status': my_status,
                'mytime': client.get('expiryTime'),
                'reset': client.get('reset'),
                "InboundIDs":get_inbound

            }

            all_clients.append(client_config)
            print(all_clients)

    # -----------------------------
    # sort
    # -----------------------------
    sorted_clients = sorted(
        all_clients,
        key=lambda x: x["created_at"],
        reverse=True
    )
    return jsonify({
        'clients': sorted_clients,
        'balance': balance
    }), 200







@app.route('/show_services', methods=['POST'])
def show_services():
    subscription_domain = get_config_value("subscription_domain")
    miniapp_domain = get_config_value("miniapp_subdomain")
    data = request.get_json()
    services = data.get('service')
    user_id = data.get('user_id')
    panel_address=services['panel']
    server_name=services['server_name']
    email=services['email']
    server_address = re.search(r'^(?:https?://)?([^/:]+)',panel_address)
    server_address = server_address.group(1) 
    subscription_link='https://'+subscription_domain+'/gx/'+services['subId']
    support_subscription_link_link='https://'+miniapp_domain+'/gx/'+services['subId']
    send_qrcode(subscription_link, user_id, title=f"{server_name+email} لینک ساب اصلی 👇")
    send_qrcode(support_subscription_link_link, user_id, title=f"{server_name+email} لینک ساب پشتیبان 👇")


    return jsonify({
    'status': 'success',
    'close_app': True
        })
 



     
@app.route('/delete_service', methods=['POST'])
def delete_service():
    data = request.get_json()
    services = data.get('service')
    panel_id=services['panel_id']
    panel=services['panel']
    limitip=services['limitip']
    user_id = data.get('user_id')
    expire=services['expiryTime']
    calculate_expire=calculate_expire_days(expire)
    balance = get_balance(user_id)
    uuid=services['uuid']
    email=services['unchanged_email']
    subId=services['subId']
    used_volume=services['up']+services['down']
    total_volume=services['total']
    net_byte_volume=total_volume-used_volume
    if net_byte_volume<0:
       net_byte_volume=0
    net_volume=bytes_to_gigabytes(net_byte_volume)
    InboundIDs = data['service']['InboundIDs']
    get_inbound = [int(x) for x in InboundIDs.split(",")]
    inbounds=get_inbound
    for inbound in inbounds:
     full_delete_url=services['panel']+f'panel/api/inbounds/{inbound}/delClientByEmail/{email}'
     alpha_status=single_with_retries('post',full_delete_url)
    if alpha_status.get('success'):                               
     delete_sql(user_id,subId)
     if user_exists(user_id):
      if expire == 0:
          base_price = get_specific_price('unlimited_volume_config_price', user_id)
      else: 
          base_price = get_specific_price('volume_config_price', user_id)
          
     else:
      if expire == 0:
          base_price = get_price_for_all('unlimited_volume_config_price')
      else:
          base_price = get_price_for_all('volume_config_price') 
     return_money = net_volume * base_price
     
     
     if int(services['is_unlimited'])==1 and bytes_to_gigabytes(total_volume)<100:
      return_money = net_volume * int(base_price)
     

     if int(services['is_unlimited'])==0:
       if user_exists(user_id):
         base_price=get_specific_price('meli_config_price', user_id)
       else:
         base_price = get_price_for_all('meli_config_price') 

       return_money = net_volume * int(base_price)




     
     if int(services['is_unlimited'])==1 and (total_volume==0 or bytes_to_gigabytes(total_volume>100)) :
      if user_exists(user_id):
       if limitip==1:
        base_price = get_specific_price('unlimited_config_one_price', user_id)
       else:
        base_price = get_specific_price('unlimited_config_two_price', user_id) 
      else:
       if limitip==1:  
        base_price = get_price_for_all('unlimited_config_one_price')
       else:
        base_price = get_price_for_all('unlimited_config_two_price')
      return_money=(base_price/30)*calculate_expire 
     if calculate_expire in (30, 60, 90) and bytes_to_gigabytes(used_volume) > 0:
       return_money -= bytes_to_gigabytes(used_volume) * 500
     update_balance(user_id, balance + return_money)
     balance = get_balance(user_id)
     return jsonify({
     'message': f'کانفیگ با موفقیت حذف شد و مبلغ {add_commas(abs(int(return_money)))} تومان به حساب شما اضافه شد ✅',
     'Status': 'success',
     'balance':  balance
     }), 200
           




@app.route('/toggle_status', methods=['POST'])
def toggle_service():
     data = request.get_json()
     status = data.get('status')
     panel=data['service']['panel']
     panel_id=data['service']['panel_id']
     username = data.get('user_id')
     uuid=data['service']['uuid']
     InboundIDs = data['service']['InboundIDs']
     get_inbound = [int(x) for x in InboundIDs.split(",")]
     flow=data['service']['flow']
     email=data['service']['unchanged_email']
     limitip=data['service']['limitip']
     totalGB=data['service']['totalGB']
     expiryTime=data['service']['expiryTime']
     config_status = True if status == 'on' else False
     tgld=data['service']['tgld']
     subId=data['service']['subId']
     comment=data['service']['comment']
     reset=data['service']['reset']
     password=data['service']['password']
     auth=data['service']['auth']
     full_status_url = panel+update_client + uuid

     clients = {
         "clients": [
             {
                 "id": uuid,
                 "flow": flow,
                 "email": email,
                 "limitip": limitip,
                 "totalGB": totalGB,
                 "expiryTime": expiryTime,
                 "enable": config_status,
                 "totalGB": totalGB,
                 "expiryTime": expiryTime,
                 "tgId": tgld,
                 "subId": subId,
                 "comment": comment,
                 "reset": reset,
             }
         ]
     }
     inbound_ids = get_inbound
     payload = [
         ("id", inbound_ids[0]),
     ]
     for inbound_id in inbound_ids:
         payload.append(("inboundIds", inbound_id))

     payload.append(("settings", json.dumps(clients)))
     print(payload)
     response=single_with_retries('post',full_status_url,data=payload)
     if response.get('success'):        
         config_status = 1 if status == 'on' else 0
           
         message = ('\u200F' + 'کانفیگ با موفقیت فعال شد' + ' ✅') if config_status else ('\u200F' + 'کانفیگ با موفقیت غیرفعال شد' + ' ⚠️')
         return jsonify({
         'message': message,
         'status':'success'
         }), 200
        

     




 
 
 
@app.route('/create_user', methods=['POST'])
def create_user():
    subscription_domain = get_config_value("subscription_domain") or "تنظیم نشده"
    miniapp_domain = get_config_value("miniapp_subdomain") or "تنظیم نشده"
    data = request.json
    expire = int(data.get('expire'))
    volume = int(data.get('volume'))
    user_id = data.get('user_id')
    username = data.get('username')
    telegram_id=data.get('telegram_id')
    if user_exists(user_id):
         base_price = get_specific_price('meli_config_price', user_id)
    else:
         base_price = get_price_for_all('meli_config_price') 
    
    price = int(volume * base_price)
    balance = get_balance(user_id)
    if balance < price or (balance == 0 and price == 0):
        return jsonify({'message': 'موجودی کافی نیست❌ '}), 403

    else:
          panel_id,panel_address,subscription_link,get_inbound,panel_name=choose_panel_meli()
          clients=single_with_retries('get',panel_address+api_clients_list)
          clients = clients.get("obj", [])
          rows = clients.get("rows", [])
          total_clients = clients.get("total", 0)
          if total_clients==0:
             config_name=str(total_clients+101)
          else:
           latest_email = rows[-1]['email']
           middle = latest_email.split("_")[1]
           config_name = str(int(middle.replace(panel_name,""))+1)

          client_uuid = str(uuid4())
          client_subid=random_string(20)
          email=user_id+"_"+panel_name+config_name
          clients = {
              "clients": [
                  {
                      "email": email,
                      "enable": True,
                      "limitIp": 0,
                      "comment": username,
                      "subId": client_subid,
                      "reset": 0,
                      "tgId": 0,
                      "totalGB": gb_to_bytes(volume),
                      "expiryTime": get_expiry_timestamp(expire),
                      "vpnUsername": random_string(10),
                      "auth": random_string(16),
                      "secret": random_string(8),
                      "naiveUsername": "",
                      "password": random_string(16),
                      "uuid": client_uuid,
                      "id": client_uuid
                  }
              ]
          }

          inbound_ids = get_inbound
          payload = [
              ("id", inbound_ids[0]),
          ]
          for inbound_id in inbound_ids:
              payload.append(("inboundIds", inbound_id))

          payload.append(("settings", json.dumps(clients)))
          response = single_with_retries(
              "post",
              panel_address+add_client,
              data=payload
          )
          print("Response:", response)

          if response:
              print("Success:", response.get("success"))
          else:
              print("Failed request")

          if response.get('success'):       
           insert_sql(user_id,telegram_id,panel_id,panel_address,subscription_link,int(time.time() * 1000),client_subid,panel_name+config_name,expire)
           subscription_link='https://'+subscription_domain+'/gx/'+client_subid
           support_subscription_link_link='https://'+miniapp_domain+'/gx/'+client_subid
           send_qrcode(subscription_link, user_id, title=f"{panel_name+config_name} لینک ساب اصلی 👇")
           send_qrcode(support_subscription_link_link, user_id, title=f"{panel_name+config_name} لینک ساب پشتیبان 👇")
           update_balance(user_id, balance - price)
           add_bonus(user_id,price)
           balance = get_balance(user_id)

           return jsonify({
            'message': f'کانفیگ با موفقیت ساخته شد و مبلغ {add_commas(price)} تومان از حساب شما کسر شد ✅',
             'balance':  balance,
             'close_app': True 
        }), 200 






@app.route('/create_user_direct', methods=['POST'])
def create_user_direct():
    subscription_domain = get_config_value("subscription_domain") or "تنظیم نشده"
    miniapp_domain = get_config_value("miniapp_subdomain") or "تنظیم نشده"
    data = request.json
    expire = int(data.get('expire'))
    volume = int(data.get('volume'))
    user_id = data.get('user_id')
    username = data.get('username')
    telegram_id=data.get('telegram_id')
    if user_exists(user_id):
     if expire == 0:
         base_price = get_specific_price('unlimited_volume_config_price', user_id)
     else:
         base_price = get_specific_price('volume_config_price', user_id)
    else:
     if expire == 0:
         base_price = get_price_for_all('unlimited_volume_config_price')
     else:
         base_price = get_price_for_all('volume_config_price')
    price = int(volume * base_price)
    balance = get_balance(user_id)
    if balance < price or (balance == 0 and price == 0):
        return jsonify({'message': 'موجودی کافی نیست❌ '}), 403
    else:

          panel_id,panel_address,subscription_link,get_inbound,panel_name=choose_panel_direct()
          clients=single_with_retries('get',panel_address+api_clients_list)
          clients = clients.get("obj", [])
          rows = clients.get("rows", [])
          total_clients = clients.get("total", 0)
          if total_clients==0:
             config_name=str(total_clients+101)
          else:
           latest_email = rows[-1]['email']
           middle = latest_email.split("_")[1]
           config_name = str(int(middle.replace(panel_name,""))+1)

          client_uuid = str(uuid4())
          client_subid=random_string(20)
          email=user_id+"_"+panel_name+config_name
          clients = {
              "clients": [
                  {
                      "email": email,
                      "enable": True,
                      "limitIp": 0,
                      "comment": username,
                      "subId": client_subid,
                      "reset": 0,
                      "tgId": 0,
                      "totalGB": gb_to_bytes(volume),
                      "expiryTime": get_expiry_timestamp(expire),
                      "vpnUsername": random_string(10),
                      "auth": random_string(16),
                      "secret": random_string(8),
                      "naiveUsername": "",
                      "password": random_string(16),
                      "uuid": client_uuid,
                      "id": client_uuid
                  }
              ]
          }

          inbound_ids = get_inbound
          payload = [
              ("id", inbound_ids[0]),
          ]
          for inbound_id in inbound_ids:
              payload.append(("inboundIds", inbound_id))

          payload.append(("settings", json.dumps(clients)))
          response = single_with_retries(
              "post",
              panel_address+add_client,
              data=payload
          )
          print("Response:", response)

          if response:
              print("Success:", response.get("success"))
          else:
              print("Failed request")

          if response.get('success'):       
           insert_sql(user_id,telegram_id,panel_id,panel_address,subscription_link,int(time.time() * 1000),client_subid,panel_name+config_name,expire)
           subscription_link='https://'+subscription_domain+'/gx/'+client_subid
           support_subscription_link_link='https://'+miniapp_domain+'/gx/'+client_subid
           send_qrcode(subscription_link, user_id, title=f"{panel_name+config_name} لینک ساب اصلی 👇")
           send_qrcode(support_subscription_link_link, user_id, title=f"{panel_name+config_name} لینک ساب پشتیبان 👇")
           update_balance(user_id, balance - price)
           add_bonus(user_id,price)
           balance = get_balance(user_id)

           return jsonify({
           'message': f'کانفیگ با موفقیت ساخته شد و مبلغ {add_commas(price)} تومان از حساب شما کسر شد ✅',
               'balance':  balance,
               'close_app': True 
       }), 200 

 





 
@app.route('/create_user_unlimited', methods=['POST'])
def create_user_unlimited():
    subscription_domain = get_config_value("subscription_domain") or "تنظیم نشده"
    miniapp_domain = get_config_value("miniapp_subdomain") or "تنظیم نشده"
    data = request.json
    username = data.get('username')
    expire = int(data.get('expire'))
    limitip = int(data.get('limitip'))
    user_id = data.get('user_id')
    telegram_id=data.get('telegram_id')
    if user_exists(user_id):
         if limitip==1:
          base_price = get_specific_price('unlimited_config_one_price', user_id)
         else:
          base_price = get_specific_price('unlimited_config_two_price', user_id)
    else:
        if limitip==1:
         base_price = get_price_for_all('unlimited_config_one_price')
        else: 
         base_price = get_price_for_all('unlimited_config_two_price')

    
    price = int(base_price*(expire/30))
    balance = get_balance(user_id)
    if balance < price or (balance == 0 and price == 0):
        return jsonify({'message': 'موجودی کافی نیست❌ '}), 403

    else:

          panel_id,panel_address,subscription_link,get_inbound,panel_name=choose_panel_unlimited()
          clients=single_with_retries('get',panel_address+api_clients_list)
          clients = clients.get("obj", [])
          rows = clients.get("rows", [])
          total_clients = clients.get("total", 0)
          if total_clients==0:
             config_name=str(total_clients+101)
          else:
           latest_email = rows[-1]['email']
           middle = latest_email.split("_")[1]
           config_name = str(int(middle.replace(panel_name,""))+1)

          client_uuid = str(uuid4())
          client_subid=random_string(20)
          email=user_id+"_"+panel_name+config_name
          
          clients = {
              "clients": [
                  {
                      "email": email,
                      "enable": True,
                      "limitIp": limitip,
                      "comment": username,
                      "subId": client_subid,
                      "reset": 0,
                      "tgId": 0,
                      "totalGB": 0,
                      "expiryTime": get_expiry_timestamp(expire),
                      "vpnUsername": random_string(10),
                      "auth": random_string(16),
                      "secret": random_string(8),
                      "naiveUsername": "",
                      "password": random_string(16),
                      "uuid": client_uuid,
                      "id": client_uuid
                  }
              ]
          }

          inbound_ids = get_inbound
          payload = [
              ("id", inbound_ids[0]),
          ]
          for inbound_id in inbound_ids:
              payload.append(("inboundIds", inbound_id))

          payload.append(("settings", json.dumps(clients)))
          response = single_with_retries(
              "post",
              panel_address+add_client,
              data=payload
          )
          print("Response:", response)

          if response:
              print("Success:", response.get("success"))
          else:
              print("Failed request")       

          if response.get('success'):       
           insert_sql(user_id,telegram_id,panel_id,panel_address,subscription_link,int(time.time() * 1000),client_subid,panel_name+config_name,expire)
           subscription_link='https://'+subscription_domain+'/gx/'+client_subid
           support_subscription_link_link='https://'+miniapp_domain+'/gx/'+client_subid
           send_qrcode(subscription_link, user_id, title=f"{panel_name+config_name} لینک ساب اصلی 👇")
           send_qrcode(support_subscription_link_link, user_id, title=f"{panel_name+config_name} لینک ساب پشتیبان 👇")
           update_balance(user_id, balance - price)
           add_bonus(user_id,price)
           balance = get_balance(user_id)

           return jsonify({
           'message': f'کانفیگ با موفقیت ساخته شد و مبلغ {add_commas(price)} تومان از حساب شما کسر شد ✅',
               'balance':  balance,
               'close_app': True 
       }), 200 


 
 
 
 
@app.route('/update_user', methods=['POST'])
def update_user():
 
    data = request.json
    username = data.get('username')
    user_id = data.get('user_id')
    panel_id=data['service']['panel_id']
    expire = int(data.get('expire'))
    volume = int(data.get('volume'))
    telegram_id=data.get('telegram_id')
    balance = get_balance(user_id)
    uuid=data['service']['uuid']
    panel_id=data['service']['panel_id']  
    flow=data['service']['flow']
    email=data['service']['unchanged_email']
    comment=data['service']['comment']
    updated_message="نام کانفیگ تغییر یافت " if comment!=username else ""
    limitip=data['service']['limitip']
    totalGB=data['service']['totalGB']
    expiryTime=data['service']['expiryTime']
    enable=data['service']['enable']
    tgld=data['service']['tgld']
    subId=data['service']['subId']
    reset=data['service']['reset']
    panel=data['service']['panel']
    password=data['service']['password']
    auth=data['service']['auth']    
    full_status_url = panel+update_client + email
    json_payload = {
        "email": email,
        "subId" : subId,
        "id" : uuid,
        "password": password,
        "auth": auth,
        "flow":flow,
        "totalGB":gb_to_bytes(volume),
        "expiryTime": (get_expiry_timestamp(expire)),
        "limitIp": limitip,
        "tgId": tgld,
        "comment": username,
        "enable": True,
        }
    alpha_status=single_with_retries('post',full_status_url,json_payload)
    used_volume=data['service']['up']+data['service']['down']
    total_volume=data['service']['total']
    remaining_volume_volume=max(0, bytes_to_gigabytes(total_volume - used_volume))
    # full_reset_traffic_url=panel+reset_traffic+str(id)+'/resetClientTraffic/'+email
    # single_with_retries('post',full_reset_traffic_url)
    # alpha_status= single_with_retries('post',full_status_url,json_payload)
    if alpha_status.get('success'):  
     if user_exists(user_id): 
         if expiryTime == 0:
             if expire==0:
                 unlimited_price = get_specific_price('unlimited_volume_config_price',user_id)##3000
                 full_price=int((remaining_volume_volume-volume)*unlimited_price)
                 abs_price=add_commas(abs(int(full_price)))
             else:    
                 unlimited_price = get_specific_price('unlimited_volume_config_price',user_id)##3000
                 config_price = get_specific_price('volume_config_price',user_id)#2000
                 full_price=int((remaining_volume_volume*unlimited_price)-(volume*config_price))
                 abs_price=add_commas(abs(int(full_price)))
         else: 
             
             if expire==0:  #### میخوای حجمی رو بدون تاریخ کنی
                 unlimited_price = get_specific_price('unlimited_volume_config_price',user_id)##3000
                 config_price = get_specific_price('volume_config_price',user_id)#2000
                 full_price=int((remaining_volume_volume*config_price)-(volume*unlimited_price)) 
                 abs_price=add_commas(abs(int(full_price)))
             else:
                 config_price = get_specific_price('meli_config_price',user_id)##3000
                 full_price=int((remaining_volume_volume-volume)*config_price) 
                 abs_price=add_commas(abs(int(full_price)))
     else:
         if expiryTime == 0:####بدون تاریخ رو همون بدون تاریخ نگه داری
             if expire==0:
                 unlimited_price = get_price_for_all('unlimited_volume_config_price')##3000
                 full_price=int((remaining_volume_volume-volume)*unlimited_price)
                 abs_price=add_commas(abs(int(full_price)))
             else:#########بدون تاریخ رو حجمی کنی 
                 unlimited_price = get_price_for_all('unlimited_volume_config_price')##3000
                 config_price = get_price_for_all('volume_config_price')#2000
                 full_price=int((remaining_volume_volume*unlimited_price)-(volume*config_price))
                 abs_price=add_commas(abs(int(full_price)))
         else:
             
             if expire==0:  #### میخوای حجمی رو بدون تاریخ کنی
                 unlimited_price = get_price_for_all('unlimited_volume_config_price')##3000
                 config_price = get_price_for_all('volume_config_price')#2000
                 full_price=int((remaining_volume_volume*config_price)-(volume*unlimited_price))
                 abs_price=add_commas(abs(int(full_price)))
             else:###############حجمی رو حجمی نگه داری
                 config_price = get_price_for_all('meli_config_price')##3000
                 full_price=int((remaining_volume_volume-volume)*config_price )
                 abs_price=add_commas(abs(int(full_price)))
                          
    if full_price < 0 and balance < abs(full_price):
     return jsonify({'message': 'موجودی کافی نیست❌'}), 403

    if full_price>0 and balance==0:
     if full_price>0:             
      message = (
          (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
          + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅'
      )
      update_sql(email,get_expiry_timestamp(expire),user_id,subId,expire) 
      update_balance(user_id, balance + full_price)
      balance = get_balance(user_id)                      
      return jsonify({
      'message': message,
      'balance':  balance,
      'close_app': True 
      }), 200              
                 
                 
             
    if full_price>0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅'
     )

              
    if full_price<0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان از حساب شما کسر شد ✅'
     ) 
    if full_price==0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'زمان کانفیگ شما بدون کسر هزینه با موفقیت تمدید شد ✅'
     )
     
    update_sql(email,get_expiry_timestamp(expire),user_id,subId,expire) 
    update_balance(user_id, balance + full_price)
    balance = get_balance(user_id)                      
    return jsonify({
    'message': message,
    'balance':  balance,
    'close_app': True 
    }), 200








@app.route('/update_user_direct', methods=['POST'])
def update_user_direct():
 
    data = request.json
    username = data.get('username')
    user_id = data.get('user_id')
    expire = int(data.get('expire'))
    volume = int(data.get('volume'))
    telegram_id=data.get('telegram_id')
    balance = get_balance(user_id)
    uuid=data['service']['uuid']
    panel_id=data['service']['panel_id']  
    flow=data['service']['flow']
    email=data['service']['unchanged_email']
    comment=data['service']['comment']
    updated_message="نام کانفیگ تغییر یافت " if comment!=username else ""
    limitip=data['service']['limitip']
    totalGB=data['service']['totalGB']
    expiryTime=data['service']['expiryTime']
    enable=data['service']['enable']
    tgld=data['service']['tgld']
    subId=data['service']['subId']
    reset=data['service']['reset']
    panel=data['service']['panel']
    password=data['service']['password']
    auth=data['service']['auth']   
    full_status_url = panel+update_client + email
    json_payload = {
        "email": email,
        "subId" : subId,
        "id" : uuid,
        "password": password,
        "auth": auth,
        "flow":flow,
        "totalGB":gb_to_bytes(volume),
        "expiryTime": (get_expiry_timestamp(expire)),
        "limitIp": limitip,
        "tgId": tgld,
        "comment": username,
        "enable": True,
        }
    alpha_status=single_with_retries('post',full_status_url,json_payload)
    used_volume=data['service']['up']+data['service']['down']
    total_volume=data['service']['total']
    remaining_volume_volume=max(0, bytes_to_gigabytes(total_volume - used_volume))
    # full_reset_traffic_url=panel+reset_traffic+str(id)+'/resetClientTraffic/'+email
    # single_with_retries('post',full_reset_traffic_url)
    if alpha_status.get('success'):
             
     if user_exists(user_id): 
         if expiryTime == 0:
             if expire==0:
                 unlimited_price = get_specific_price('unlimited_volume_config_price',user_id)
                 full_price=int((remaining_volume_volume-volume)*unlimited_price)
                 abs_price=add_commas(abs(int(full_price)))
             else:    
                 unlimited_price = get_specific_price('unlimited_volume_config_price',user_id)
                 config_price = get_specific_price('volume_config_price',user_id)
                 full_price=int((remaining_volume_volume*unlimited_price)-(volume*config_price))
                 abs_price=add_commas(abs(int(full_price)))
         else: 
             
             if expire==0:  #### میخوای حجمی رو بدون تاریخ کنی
                 unlimited_price = get_specific_price('unlimited_volume_config_price',user_id)
                 config_price = get_specific_price('volume_config_price',user_id)
                 full_price=int((remaining_volume_volume*config_price)-(volume*unlimited_price)) 
                 abs_price=add_commas(abs(int(full_price)))
             else:
                 config_price = get_specific_price('volume_config_price',user_id)
                 full_price=int((remaining_volume_volume-volume)*config_price) 
                 abs_price=add_commas(abs(int(full_price)))
     else:
         if expiryTime == 0:####بدون تاریخ رو همون بدون تاریخ نگه داری
             if expire==0:
                 unlimited_price = get_price_for_all('unlimited_volume_config_price')
                 full_price=int((remaining_volume_volume-volume)*unlimited_price)
                 abs_price=add_commas(abs(int(full_price)))
             else:#########بدون تاریخ رو حجمی کنی 
                 unlimited_price = get_price_for_all('unlimited_volume_config_price')
                 config_price = get_price_for_all('volume_config_price')#2000
                 full_price=int((remaining_volume_volume*unlimited_price)-(volume*config_price))
                 abs_price=add_commas(abs(int(full_price)))
         else:
             
             if expire==0:  #### میخوای حجمی رو بدون تاریخ کنی
                 unlimited_price = get_price_for_all('unlimited_volume_config_price')
                 config_price = get_price_for_all('volume_config_price')
                 full_price=int((remaining_volume_volume*config_price)-(volume*unlimited_price))
                 abs_price=add_commas(abs(int(full_price)))
             else:###############حجمی رو حجمی نگه داری
                 config_price = get_price_for_all('volume_config_price')
                 full_price=int((remaining_volume_volume-volume)*config_price )
                 abs_price=add_commas(abs(int(full_price)))
                          
    if full_price < 0 and balance < abs(full_price):
     return jsonify({'message': 'موجودی کافی نیست❌'}), 403

    if full_price>0 and balance==0:
     if full_price>0:             
      message = (
          (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
          + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅'
      )
      update_sql(email,get_expiry_timestamp(expire),user_id,subId,expire) 
      update_balance(user_id, balance + full_price)
      balance = get_balance(user_id)                      
      return jsonify({
      'message': message,
      'balance':  balance,
      'close_app': True 
      }), 200              
                 
                 
             
    if full_price>0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅'
     )

              
    if full_price<0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان از حساب شما کسر شد ✅'
     ) 
    if full_price==0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'زمان کانفیگ شما بدون کسر هزینه با موفقیت تمدید شد ✅'
     )
     
    update_sql(email,get_expiry_timestamp(expire),user_id,subId,expire) 
    update_balance(user_id, balance + full_price)
    balance = get_balance(user_id)                      
    return jsonify({
    'message': message,
    'balance':  balance,
    'close_app': True 
    }), 200






@app.route('/update_user_unlimited', methods=['POST'])
def update_user_unlimited():
 
    data = request.json
    username = data.get('username')
    user_id = data.get('user_id')

    expire = int(data.get('expire'))
    new_limitip = int(data.get('limitip'))
    telegram_id=data.get('telegram_id')
    balance = get_balance(user_id)
    uuid=data['service']['uuid']
    panel_id=data['service']['panel_id']  
    flow=data['service']['flow']
    email=data['service']['unchanged_email']
    comment=data['service']['comment']

    updated_message="نام کانفیگ تغییر یافت " if comment!=username else ""
    limitip=data['service']['limitip']
    totalGB=data['service']['totalGB']
    expiryTime=data['service']['expiryTime']
    calculate_expire=calculate_expire_days(expiryTime)
    enable=data['service']['enable']
    tgld=data['service']['tgld']
    subId=data['service']['subId']
    reset=data['service']['reset']
    panel=data['service']['panel']
    password=data['service']['password']
    auth=data['service']['auth']       
    full_status_url = panel+update_client + uuid   
    clients = {
        "clients": [
            {
                "id": uuid,
                "flow": flow,
                "email": email,
                "limitip": limitip,
                "totalGB": totalGB,
                "expiryTime": expiryTime,
                "enable": enable,
                "tgId": tgld,
                "subId":sub,
                "comment": comment,
                "reset": reset,
                "speedLimitDown": random_string(8),
                "speedLimitUp": "",
                "userLimitOverride": random_string(16),
                "vpnUsername": client_uuid,
                "auth": auth,
                "naiveUsername": client_uuid,
                "password": password,
                "uuid":uuid
            }
        ]
    }

    inbound_ids = get_inbound
    payload = [
        ("id", inbound_ids[0]),
    ]
    for inbound_id in inbound_ids:
        payload.append(("inboundIds", inbound_id))

    payload.append(("settings", json.dumps(clients)))
    response = single_with_retries(
        "post",
        panel+add_client,
        data=payload
    )
    print("Response:", response)

    if response:
        print("Success:", response.get("success"))
    else:
        print("Failed request")
  

    used_volume=data['service']['up']+data['service']['down']
    total_volume=data['service']['total']
    # full_reset_traffic_url=panel+reset_traffic+str(id)+'/resetClientTraffic/'+email
    # single_with_retries('post',full_reset_traffic_url)
    if response.get('success'):           
      if user_exists(user_id):
        unlimited_config_one_price = get_specific_price('unlimited_config_one_price', user_id)
        unlimited_config_two_price = get_specific_price('unlimited_config_two_price', user_id)     
        if limitip==1:
         if new_limitip==1:
          return_money=int(calculate_expire*(unlimited_config_one_price/30)-(expire*(unlimited_config_one_price/30)))
         else:
          return_money=int(calculate_expire*(unlimited_config_one_price/30)-(expire*(unlimited_config_two_price/30)))
        else:
         if new_limitip==1:
          return_money=int(calculate_expire*(unlimited_config_two_price/30)-(expire*(unlimited_config_one_price/30)))
         else:
          return_money=int(calculate_expire*(unlimited_config_two_price/30)-(expire*(unlimited_config_two_price/30)))

      else:
       unlimited_config_one_price=get_price_for_all('unlimited_config_one_price')
       unlimited_config_two_price=get_price_for_all('unlimited_config_two_price')
       if limitip==1:
        if new_limitip==1:
         return_money=int(calculate_expire*(unlimited_config_one_price/30)-(expire*(unlimited_config_one_price/30)))
        else:
         return_money=int(calculate_expire*(unlimited_config_one_price/30)-(expire*(unlimited_config_two_price/30)))
       else:
         if new_limitip==1:
          return_money=int(calculate_expire*(unlimited_config_two_price/30)-(expire*(unlimited_config_one_price/30)))
         else:
          return_money=int(calculate_expire*(unlimited_config_two_price/30)-(expire*(unlimited_config_two_price/30)))
     
         
    if calculate_expire in (30, 60, 90) and bytes_to_gigabytes(used_volume) > 0:
     return_money -= bytes_to_gigabytes(used_volume) * 500 
    abs_price=add_commas(abs(int(return_money)))
    
    if return_money < 0 and balance < abs(return_money):
        return jsonify({'message': 'موجودی کافی نیست❌'}), 403
 


    if return_money>0 and balance==0:
     if return_money>0:             
      message = (
          (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
          + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅'
      )
      update_sql(email,get_expiry_timestamp(expire),user_id,subId,expire) 
      update_balance(user_id, balance + return_money)
      balance = get_balance(user_id)                      
      return jsonify({
      'message': message,
      'balance':  balance,
      'close_app': True 
      }), 200
   
    
    
    
    if return_money>0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅'
     )

              
    if return_money<0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'کانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان از حساب شما کسر شد ✅'
     ) 
    if return_money==0:             
     message = (
         (f'نام کانفیگ تغییر یافت و ' if comment != username else '')
         + f'زمان کانفیگ شما بدون کسر هزینه با موفقیت تمدید شد ✅'
     )
     
    update_sql(email,get_expiry_timestamp(expire),user_id,subId,expire) 
    update_balance(user_id, balance + return_money)
    balance = get_balance(user_id)                      
    return jsonify({
    'message': message,
    'balance':  balance,
    'close_app': True 
    }), 200





# ---------- route ----------
@app.route('/manage_panel.html')
def manage_panel():
    panels = get_all_panels_with_capacity()
    return render_template("manage_panel.html", panels=panels)




@app.route("/master_edit/<int:id>")
def master_edit(id):
    master = get_specific_panel_with_capacity(id)
    return render_template("master_edit.html", master=master)









@app.route('/update_master/<int:id>', methods=['PUT'])
def update_master(id):
    data = request.get_json()
    print(data)

    panel_address = data.get("panel_address")
    name = data.get("name")
    panel_type = data.get("panel_type")
    token = data.get("token")
    capacity = data.get("capacity")
    subscription_link = data.get("sub_link")
    raw_inbounds = data.get("inbounds", [])

    raw_inbounds = ",".join(raw_inbounds)

    # -----------------------------
    # تنظیم نوع پنل
    # -----------------------------
    if panel_type == 'نامحدود':
        is_unlimited_val = 1
        panel_type_val = "نامحدود"

    elif panel_type == 'حجمی':
        is_unlimited_val = 1
        panel_type_val = "حجمی"

    elif panel_type == 'نت ملی':
        is_unlimited_val = 0
        panel_type_val = "نت ملی"

    else:
        return jsonify({
            "status": "error",
            "message": "نوع پنل نامعتبر است"
        }), 400

    # -----------------------------
    # چک اولیه
    # -----------------------------
    if not panel_address:
        return jsonify({
            "status": "error",
            "message": "آدرس پنل الزامی است"
        }), 400

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    try:

        # =========================
        # گرفتن inbound های قبلی
        # =========================
        c.execute(
            "SELECT get_inbound FROM panels WHERE id = ?",
            (id,)
        )
        old_row = c.fetchone()

        old_inbounds = []
        if old_row and old_row[0]:
            old_inbounds = old_row[0].split(",")

        new_inbounds = raw_inbounds.split(",")

        # =========================
        # آپدیت پنل
        # =========================
        c.execute("""
            UPDATE panels SET
                panel_address = ?,
                token = ?,
                name = ?,
                is_unlimited = ?,
                capacity = ?,
                subscription_link = ?,
                panel_type = ?,
                get_inbound = ?
            WHERE id = ?
        """, (
            panel_address,
            token,
            name,
            is_unlimited_val,
            capacity,
            subscription_link,
            panel_type_val,
            raw_inbounds,
            id
        ))

        c.execute("""
            UPDATE services SET
                panel = ?,
                subscription_link = ?
            WHERE panel_id = ?
        """, (
            panel_address,
            subscription_link,
            id
        ))

        conn.commit()

        sync_done = False

        # =========================
        # Sync فقط در صورت تغییر inbound
        # =========================
        if set(old_inbounds) != set(new_inbounds):

            sync_done = True

            full_address = panel_address + api_clients_list
            list_results = single_with_retries('get', full_address)

            clients = list_results.get("obj", [])

            payload = {
                "inboundIds": [
                    int(i)
                    for i in new_inbounds
                    if i.strip().isdigit()
                ]
            }

            for client in clients:

                email = client.get("email", "")

                if not email:
                    continue

                attach_url = (
                    f"{panel_address}panel/api/clients/"
                    f"{email}/attach"
                )

                response = single_with_retries(
                    'post',
                    attach_url,
                    payload
                )

                print(email, response)

        return jsonify({
            "status": "success",
            "message": "مستر با موفقیت آپدیت شد",
            "sync_done": sync_done,
            "id": id
        }), 200

    except sqlite3.Error as e:
        print("DB ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "خطا در دیتابیس"
        }), 500

    except Exception as e:
        print("ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        conn.close()






@app.route('/add_master', methods=['POST'])
def add_master():
    data = request.get_json(force=True)
    print(data)

    panel_address = data.get("panel_address")
    token=data.get("token")
    name = data.get("name")
    volume_type = data.get("volume_type")

    # تنظیم نوع پنل
    if volume_type == 'unlimited':
        is_unlimited_val = 1
        panel_type_val = "نامحدود"

    elif volume_type == 'volume_based':
        is_unlimited_val = 1
        panel_type_val = "حجمی"

    elif volume_type == 'national':
        is_unlimited_val = 0
        panel_type_val = "نت ملی"


    capacity = data.get("capacity")
    subscription_link = data.get("sub_link")
    raw_inbounds = data.get("inbounds")
    raw_inbounds = ",".join(raw_inbounds)
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    try:
        # بررسی تکراری بودن فقط برای پنل‌های مستر
        c.execute("""
            SELECT id
            FROM panels
            WHERE panel_address = ?
        """, (panel_address,))

        existing_panel = c.fetchone()

        if existing_panel:
            return jsonify({
                "status": "error",
                "message": "این پنل مستر قبلاً ثبت شده است"
            }), 409

        # ثبت پنل مستر جدید
        c.execute("""
            INSERT INTO panels (
                panel_address,
                token,
                name,
                is_unlimited,
                capacity,
                subscription_link,
                panel_type,
                get_inbound,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)
        """, (
            panel_address,
            token,
            name,
            is_unlimited_val,
            capacity,
            subscription_link,
            panel_type_val,
            raw_inbounds,
            1,
        ))

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "پنل مستر با موفقیت اضافه شد!"
        }), 200

    except sqlite3.Error as e:
        print(f"Database Error: {e}")

        return jsonify({
            "status": "error",
            "message": "خطایی در ذخیره‌سازی اطلاعات رخ داد"
        }), 500

    finally:
        conn.close()







@app.route("/delete_master/<int:id>", methods=["DELETE"])
def delete_master(id):
    print("DELETE MASTER:", id)

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    # اول چک می‌کنیم master وجود دارد
    c.execute("SELECT id FROM panels WHERE id=?", (id,))
    master = c.fetchone()

    if not master:
        return jsonify({
            "status": "not_found",
            "message": "مستر پیدا نشد"
        }), 404

    # حذف master و همه child ها
    c.execute("DELETE FROM panels WHERE id=? ", (id,))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "deleted",
        "message": "سرور مستر  با موفقیت حذف شد"
    })





@app.route("/toggle_status_panel/<int:id>", methods=["POST"])
def toggle_status(id):
    print("TOGGLE:", id)

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT status FROM panels WHERE id=?", (id,))
    row = c.fetchone()

    if not row:
        return jsonify({"status": "not_found"}), 404

    new_status = 0 if row[0] == 1 else 1

    c.execute("UPDATE panels SET status=? WHERE id=?", (new_status, id))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "toggled",
        "new_status": new_status,
        "message": "وضعیت پنل با موفقیت تغییر کرد"
    })



import base64
import os
import re
import sqlite3
import time
import requests
from flask import Flask, Response, render_template, request
import urllib.parse


# ------------------ config ------------------

def bytes_to_gigabytes(v):
    return round(v / (1024 ** 3), 2)

def get_config_value(key):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute(
            "SELECT config_value FROM bot_config WHERE config_key = ?",
            (key,)
        )
        row = c.fetchone()
        return row[0] if row else "0"
    finally:
        conn.close()

# ------------------ utils ------------------


def clean_after_hash(text, username=None):
    if not text:
        return ""

    lines = text.splitlines()
    result = []

    for line in lines:
        # اصلاح spx
        line = re.sub(r'&?spx=[^&#\s]*', '&spx=/', line)

        if "#" in line:
            before, after = line.split("#", 1)

            # حذف username فقط از tag
            if username:
                after = after.replace(username, "")

            # تمیز کردن tag
            after = after.replace("_", " ")
            after = after.replace("-", " ")

            # حذف فاصله‌های اضافی
            after = re.sub(r"\s+", " ", after).strip()

            line = before + "#" + after

        result.append(line)

    return "\n".join(result)




def extract_links(text):
    return re.findall(r"[a-zA-Z0-9+.-]+://[^\s]+", text or "")








# استخراج اسم + پرچم از هر کانفیگ
def extract_name_and_flag(text, username):
    text = text.replace(username, "")

    m = re.search(r"#([^\s]+)", text or "")
    if not m:
        return "User", "🏳️"

    # decode
    value = urllib.parse.unquote(m.group(1))

    # پیدا کردن پرچم یونیکد
    flag_match = re.search(r'[\U0001F1E6-\U0001F1FF]{2}', value)
    flag = flag_match.group(0) if flag_match else ""

    # حذف پرچم
    value = value.replace(flag, "")

    # حذف username
    value = re.sub(
        rf"[_\-\s]*{re.escape(username)}[_\-\s]*",
        " ",
        value,
        flags=re.IGNORECASE
    )

    # تمیز کردن جداکننده‌ها
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value or "User", flag


# ------------------ route ------------------

@app.route("/gx", defaults={"path": ""})
@app.route("/gx/<path:path>")
def sub(path):

    path = (path or "").strip("/")

    miniapp_subdomain = get_config_value("miniapp_subdomain")
    subscription_domain=get_config_value("subscription_domain")

    # ------------------ DB ------------------

    subscription_link = ""

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute(
            "SELECT subscription_link, username FROM services WHERE subid = ?",
            (path,)
        )
        row = c.fetchone()
        if row:
            subscription_link = row[0]
            username=row[1]
    finally:
        conn.close()

    # ------------------ FETCH ------------------

    content = ""
    upstream_userinfo = ""

    if subscription_link:
        final_url = f"{subscription_link}{path}"

        try:
            r = requests.get(final_url, timeout=8)

            if r.status_code == 200:
                content = r.text.strip()
                upstream_userinfo = r.headers.get("Subscription-Userinfo", "")

                try:
                    content = base64.b64decode(content).decode("utf-8")
                except:
                    pass

        except Exception as e:
            print("[REQUEST ERROR]", e)

    # ------------------ extra links ------------------

        extra_links = [
            "vless://1768c5dd-5bc4-4523-8fb9-9cdba36f45d5@none.parstrade.xyz:31509?security=&type=tcp&encryption=none#پشتیبان"
        ]

        # 1. فقط content تمیز شود
        clean_content = clean_after_hash(content, username) if content else ""

        # 2. لینک‌ها بدون تغییر اضافه شوند
        merged_full = clean_content + "\n" + "\n".join(extra_links) if extra_links else clean_content

        # 3. encode
        result = base64.b64encode(merged_full.encode()).decode()

    # ------------------ USERINFO ------------------

    upload = download = total = expire = 0

    userinfo = upstream_userinfo or request.headers.get("Subscription-Userinfo", "")

    if userinfo:
        data = {}
        for p in userinfo.split(";"):
            if "=" in p:
                k, v = p.split("=")
                try:
                    data[k.strip()] = int(v.strip())
                except:
                    pass

        upload = data.get("upload", 0)
        download = data.get("download", 0)
        total = data.get("total", 0)
        expire = data.get("expire", 0)

    # ------------------ calculations ------------------

    if expire == 0:
        remaining_days = "بدون انقضا"
    else:
        diff = expire - time.time()
        if diff < 0:
            remaining_days = "منقضی"
        else:
            days = int(diff // 86400)
            hours = int((diff % 86400) // 3600)
            remaining_days = f"{days} روز و {hours} ساعت"

    if total == 0:
        remaining_volume = "نامحدود"
    else:
        remaining = total - (upload + download)
        gb = bytes_to_gigabytes(remaining)
        remaining_volume = f"{gb}GB" if gb > 0 else "منقضی"

    status = "فعال" if (
        (expire == 0 or expire > time.time())
        and (total == 0 or total - (upload + download) > 0)
    ) else "غیر فعال"

    # ------------------ LINKS (FIX اصلی اینجاست) ------------------

    links = extract_links(content)

    additional_links = []


    for link in links:
        name, flag = extract_name_and_flag(link,username)
        additional_links.append({f"{flag}{name}": clean_after_hash(link,username)})



    # پشتیبان جدا
    for link in extra_links:
        additional_links.append({"پشتیبان": link})
    # ------------------ USER ------------------
    user = {
        "username": name,
        "subscription_url": f"https://{subscription_domain}/gx/{path}",
        "remaining_days": remaining_days,
        "status": status,
        "remaining_volume": remaining_volume,
        "additional_links": additional_links
    }

    # ------------------ browser detect ------------------

    ua = request.headers.get("User-Agent", "")

    if "Mozilla" in ua or "Chrome" in ua:
        return render_template("sub.html", user=user)

    return Response(
        result,
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Profile-Title": "base64:" + base64.b64encode(b"v2ray").decode(),
            "Profile-Update-Interval": "2",
            "Subscription-Userinfo": f"upload={upload}; download={download}; total={total}; expire={expire}",
            "profile-web-page-url": f"https://{subscription_domain}/gx/{path}",
            "support-url":f"https://{miniapp_subdomain}/gx/{path}"
        }
    )




# ---------- اجرای برنامه ----------z
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
 run_flask()


