import telebot
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import time

BOT_TOKEN = "8239650192:AAEia0wuR4G6ai-iJQzpc64mBSwjTCkLMzA"
ADMIN_ID = "7144593342"

bot = telebot.TeleBot(BOT_TOKEN)

# ================= FIREBASE =================
firebase_config = {
  "type": "service_account",
  "project_id": "winverse-bot",
  "private_key_id": "dd0744d601e01a51f07271384626c4d1d9aa0945",
  "private_key": """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"""
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

# ================= USER =================
def get_user(user_id):
    try:
        ref = db.reference(f'users/{user_id}')
        user = ref.get()

        if not user:
            user = {
                "balance": 0,
                "referrals": 0,
                "ref_by": "",
                "last_bonus": ""
            }
            ref.set(user)

        return user
    except:
        return {"balance": 0, "referrals": 0, "ref_by": "", "last_bonus": ""}

# ✅ FIXED (update → set)
def update_user(user_id, data):
    try:
        db.reference(f'users/{user_id}').set(data)
    except Exception as e:
        print("Update error:", e)

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = str(message.chat.id)
        args = message.text.split()
        user = get_user(user_id)

        # Referral
        if len(args) > 1 and user["ref_by"] == "":
            ref_id = args[1]

            if ref_id != user_id:
                ref_user = get_user(ref_id)

                user["balance"] += 10
                user["ref_by"] = ref_id

                ref_user["referrals"] += 1

                update_user(ref_id, ref_user)
                update_user(user_id, user)

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("💰 Balance", "🎁 Daily Bonus")
        markup.row("👥 Referral", "📋 Tasks")
        markup.row("🏆 Leaderboard", "💸 Withdraw")

        bot.send_message(user_id, "👋 Welcome to Winverse Bot!", reply_markup=markup)

    except Exception as e:
        print("Start Error:", e)

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    user = get_user(str(message.chat.id))
    bot.send_message(message.chat.id, f"💰 Balance: ₹{user['balance']}")

# ================= BONUS =================
@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    today = str(datetime.now().date())

    # ✅ FIX repeat bonus
    if user.get("last_bonus") == today:
        bot.send_message(user_id, "❌ Already claimed today")
        return

    user["balance"] += 5
    user["last_bonus"] = today
    update_user(user_id, user)

    # referral earning
    if user["ref_by"]:
        ref_user = get_user(user["ref_by"])
        ref_user["balance"] += 1
        update_user(user["ref_by"], ref_user)

    # ✅ show updated balance
    bot.send_message(user_id, f"✅ ₹5 Added\n💰 New Balance: ₹{user['balance']}")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    bot.send_message(user_id,
        f"🔗 Link:\n{link}\n👥 {user['referrals']}\n💰 25% lifetime earning"
    )

# ================= TASKS =================
@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(message):
    try:
        user_id = str(message.chat.id)
        tasks = db.reference("tasks").get()

        if not tasks:
            bot.send_message(user_id, "❌ No tasks available")
            return

        text = "📋 Tasks:\n\n"
        for tid, t in tasks.items():
            done = db.reference(f"completed/{user_id}/{tid}").get()

            status = "✅ Done" if done else f"₹{t['reward']}"
            text += f"{tid[:5]} → {t['text']} ({status})\n"

        bot.send_message(user_id, text)

    except Exception as e:
        print("Task error:", e)
        bot.send_message(message.chat.id, "Error loading tasks")

# ================= COMPLETE TASK =================
@bot.message_handler(commands=['done'])
def done(message):
    try:
        user_id = str(message.chat.id)
        tid = message.text.split()[1]

        if db.reference(f"completed/{user_id}/{tid}").get():
            bot.send_message(user_id, "❌ Already completed")
            return

        task = db.reference(f"tasks/{tid}").get()

        if not task:
            bot.send_message(user_id, "❌ Invalid Task ID")
            return

        user = get_user(user_id)
        user["balance"] += task["reward"]
        update_user(user_id, user)

        db.reference(f"completed/{user_id}/{tid}").set(True)

        if user["ref_by"]:
            ref_user = get_user(user["ref_by"])
            ref_user["balance"] += int(task["reward"] * 0.25)
            update_user(user["ref_by"], ref_user)

        bot.send_message(user_id, f"✅ ₹{task['reward']} added\n💰 Balance: ₹{user['balance']}")

    except:
        bot.send_message(message.chat.id, "Use: /done TASK_ID")

# ================= WITHDRAW =================
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    if user["balance"] < 20:
        bot.send_message(user_id, "❌ Minimum ₹20 required")
        return

    msg = bot.send_message(user_id, "Enter amount:")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    try:
        user_id = str(message.chat.id)
        amount = int(message.text)

        user = get_user(user_id)

        if amount > user["balance"]:
            bot.send_message(user_id, "❌ Not enough balance")
            return

        db.reference("withdraw").push({
            "user": user_id,
            "amount": amount,
            "status": "pending"
        })

        bot.send_message(user_id, "✅ Request sent to admin")

        bot.send_message(ADMIN_ID, f"💸 Withdraw Request\nUser: {user_id}\nAmount: ₹{amount}")

    except:
        bot.send_message(message.chat.id, "❌ Invalid amount")

# ================= ADMIN =================
@bot.message_handler(commands=['addtask'])
def addtask(message):
    if str(message.chat.id) != ADMIN_ID:
        return

    text = message.text.replace("/addtask ", "")

    db.reference("tasks").push({
        "text": text,
        "reward": 5
    })

    bot.send_message(message.chat.id, "✅ Task added")

# ================= RUN =================
print("Bot Running 🚀")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
