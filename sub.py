import base64
import os
import re
import sqlite3
import time
import requests
from flask import Flask, Response, render_template, request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)

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

def clean_after_hash(text, username):
    if not text or not username:
        return ""

    # حذف username و @
    text = text.replace(username, "")
    text = re.sub(r'&?spx=[^&#\s]*', '&spx=/', text)

    if "#" in text:
        before, after = text.split("#", 1)

        # فقط بعد از #
        after = after.replace("_", " ")
        after = after.replace("-", " ")

        text = before + "#" + after  # خود # حفظ می‌شود

    # تمیز کردن فاصله‌های اضافی
    return text




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
        "subscription_url": f"https://{miniapp_subdomain}/gx/{path}",
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
            "profile-web-page-url": f"https://{miniapp_subdomain}/gx/{path}"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)