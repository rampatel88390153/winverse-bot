import telebot
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import time
import os

# ================= TOKEN SAFE =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 👉 fallback (agar Railway variable nahi mila)
if not BOT_TOKEN:
    BOT_TOKEN = "8239650192:AAEia0wuR4G6ai-iJQzpc64mBSwjTCkLMzA"

bot = telebot.TeleBot(BOT_TOKEN)

# ================= FIREBASE SAFE =================
firebase_config = {
  "type": "service_account",
  "project_id": "winverse-bot",
  "private_key_id": "dd0744d601e01a51f07271384626c4d1d9aa0945",
  "private_key": """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY
-----END PRIVATE KEY-----""",
  "client_email": "firebase-adminsdk-fbsvc@winverse-bot.iam.gserviceaccount.com"
}

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://winverse-bot-default-rtdb.firebaseio.com/"
        })
    print("Firebase Connected ✅")
except Exception as e:
    print("Firebase Error:", e)

# ================= AUTO TASK =================
def ensure_tasks():
    try:
        ref = db.reference("tasks")
        if not ref.get():
            ref.set({
                "task1": {"text": "Join Channel", "reward": 5}
            })
    except:
        pass

ensure_tasks()

# ================= USER =================
def get_user(uid):
    try:
        ref = db.reference(f'users/{uid}')
        user = ref.get()

        if not user:
            user = {
                "balance": 10,
                "referrals": 0,
                "ref_by": "",
                "last_bonus": "0"
            }
            ref.set(user)

        return user
    except:
        return {"balance": 0, "last_bonus": "0"}

def update_user(uid, data):
    try:
        db.reference(f'users/{uid}').update(data)
    except:
        pass

# ================= MENU =================
def menu():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("💰 Balance", "🎁 Daily Bonus")
    m.row("👥 Referral", "📋 Tasks")
    return m

# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.chat.id)
    get_user(uid)
    bot.send_message(uid, "👋 Welcome to Winverse Bot!", reply_markup=menu())

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def bal(msg):
    uid = str(msg.chat.id)
    user = get_user(uid)
    bot.send_message(uid, f"💰 Balance: ₹{user.get('balance',0)}")

# ================= BONUS =================
@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(msg):
    try:
        uid = str(msg.chat.id)
        ref = db.reference(f'users/{uid}')
        user = ref.get()

        today = datetime.now().strftime("%Y-%m-%d")

        if user.get("last_bonus") == today:
            bot.send_message(uid, "❌ Already claimed today")
            return

        new_balance = user.get("balance", 0) + 1

        ref.update({
            "balance": new_balance,
            "last_bonus": today
        })

        bot.send_message(uid, f"✅ ₹1 Added\n💰 Balance: ₹{new_balance}")

    except Exception as e:
        print("Bonus Error:", e)
        bot.send_message(msg.chat.id, "❌ Error, try again")

# ================= TASK =================
@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def task(msg):
    try:
        tasks = db.reference("tasks").get()

        if not tasks:
            bot.send_message(msg.chat.id, "❌ No tasks found")
            return

        text = "📋 Tasks:\n\n"

        for t in tasks:
            text += f"{t} - ₹{tasks[t]['reward']}\n"

        bot.send_message(msg.chat.id, text)

    except Exception as e:
        print("Task Error:", e)
        bot.send_message(msg.chat.id, "❌ Error loading tasks")

# ================= RUN =================
print("Bot Running 🚀")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Restarting Bot:", e)
        time.sleep(5)
