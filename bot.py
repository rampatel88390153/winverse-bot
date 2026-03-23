import telebot
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import time
import os

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8239650192:AAEia0wuR4G6ai-iJQzpc64mBSwjTCkLMzA"
ADMIN_ID = "7144593342"

bot = telebot.TeleBot(BOT_TOKEN)

# ================= FIREBASE =================
firebase_config = {
  "type": "service_account",
  "project_id": "winverse-bot",
  "private_key_id": "YOUR_KEY_ID",
  "private_key": """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY
-----END PRIVATE KEY-----""",
  "client_email": "firebase-adminsdk-fbsvc@winverse-bot.iam.gserviceaccount.com"
}

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://winverse-bot-default-rtdb.firebaseio.com/"
    })

# ================= USER =================
def get_user(uid):
    ref = db.reference(f'users/{uid}')
    user = ref.get()

    if not user:
        user = {
            "balance": 10,   # signup bonus
            "ref_by": "",
            "referrals": 0
        }
        ref.set(user)

    return user

def update_user(uid, data):
    db.reference(f'users/{uid}').update(data)

# ================= MENU =================
def menu():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("💰 Balance", "📋 Tasks")
    m.row("👥 Referral", "💸 Withdraw")
    return m

# ================= START =================
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.chat.id)
    get_user(uid)
    bot.send_message(uid, "👋 Welcome!", reply_markup=menu())

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(msg):
    user = get_user(str(msg.chat.id))
    bot.send_message(msg.chat.id, f"💰 Balance: ₹{user['balance']}")

# ================= TASK SHOW =================
@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(msg):
    try:
        tasks = db.reference("tasks").get()

        if not tasks:
            bot.send_message(msg.chat.id, "❌ No tasks available")
            return

        text = "📋 Tasks:\n\n"
        for tid, t in tasks.items():
            text += f"{tid} → {t['text']} (₹{t['reward']})\n"

        text += "\nUse: /done task1"

        bot.send_message(msg.chat.id, text)
    except:
        bot.send_message(msg.chat.id, "❌ Error loading tasks")

# ================= COMPLETE TASK =================
@bot.message_handler(commands=['done'])
def done(msg):
    try:
        uid = str(msg.chat.id)
        tid = msg.text.split()[1]

        if db.reference(f"done/{uid}/{tid}").get():
            bot.send_message(uid, "❌ Already done")
            return

        task = db.reference(f"tasks/{tid}").get()

        if not task:
            bot.send_message(uid, "❌ Invalid task")
            return

        user = get_user(uid)
        reward = task["reward"]

        new_balance = user["balance"] + reward
        update_user(uid, {"balance": new_balance})

        db.reference(f"done/{uid}/{tid}").set(True)

        bot.send_message(uid, f"✅ ₹{reward} added\n💰 Balance: ₹{new_balance}")

    except:
        bot.send_message(msg.chat.id, "Use: /done task1")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(msg):
    uid = str(msg.chat.id)
    user = get_user(uid)

    link = f"https://t.me/{bot.get_me().username}?start={uid}"

    bot.send_message(uid, f"🔗 Link:\n{link}\n👥 {user['referrals']}")

# ================= WITHDRAW =================
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(msg):
    uid = str(msg.chat.id)
    user = get_user(uid)

    if user["balance"] < 20:
        bot.send_message(uid, "❌ Minimum ₹20 required")
        return

    msg1 = bot.send_message(uid, "Enter amount:")
    bot.register_next_step_handler(msg1, process_withdraw)

def process_withdraw(msg):
    try:
        uid = str(msg.chat.id)
        amount = int(msg.text)

        user = get_user(uid)

        if amount > user["balance"]:
            bot.send_message(uid, "❌ Not enough balance")
            return

        final = amount - 2  # withdraw fee

        update_user(uid, {"balance": user["balance"] - amount})

        db.reference("withdraw").push({
            "user": uid,
            "amount": amount,
            "final": final
        })

        bot.send_message(uid, f"✅ Withdraw request sent\n💸 You get ₹{final}")

        # ADMIN MESSAGE
        bot.send_message(ADMIN_ID, f"💸 Withdraw Request\nUser: {uid}\nAmount: ₹{amount}")

    except:
        bot.send_message(msg.chat.id, "❌ Invalid amount")

# ================= ADMIN ADD TASK =================
@bot.message_handler(commands=['addtask'])
def addtask(msg):
    if str(msg.chat.id) != ADMIN_ID:
        return

    try:
        text = msg.text.replace("/addtask ", "")

        db.reference("tasks").child(f"task{int(time.time())}").set({
            "text": text,
            "reward": 5
        })

        bot.send_message(msg.chat.id, "✅ Task added")

    except:
        bot.send_message(msg.chat.id, "❌ Error")

# ================= RUN =================
print("Bot Running 🚀")

while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        print("Restart:", e)
        time.sleep(5)
