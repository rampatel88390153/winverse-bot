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
  "private_key_id": "YOUR_KEY_ID",
  "private_key": """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY
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
                "balance": 10,  # signup bonus
                "referrals": 0,
                "ref_by": "",
                "last_bonus": "",
                "created_at": str(datetime.now())
            }
            ref.set(user)

        return user
    except Exception as e:
        print("Get user error:", e)
        return {"balance": 0, "referrals": 0, "ref_by": "", "last_bonus": ""}

def update_user(user_id, data):
    try:
        db.reference(f'users/{user_id}').update(data)  # ✅ FIXED
    except Exception as e:
        print("Update error:", e)

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = str(message.chat.id)
        args = message.text.split()

        user = get_user(user_id)

        # referral (only once)
        if len(args) > 1 and user["ref_by"] == "":
            ref_id = args[1]

            if ref_id != user_id:
                ref_user = get_user(ref_id)

                update_user(user_id, {
                    "balance": user["balance"] + 10,
                    "ref_by": ref_id
                })

                update_user(ref_id, {
                    "balance": ref_user["balance"] + 10,
                    "referrals": ref_user["referrals"] + 1
                })

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
    try:
        user_id = str(message.chat.id)
        user = db.reference(f'users/{user_id}').get()

        if not user:
            user = get_user(user_id)

        bot.send_message(user_id, f"💰 Balance: ₹{user['balance']}")
    except Exception as e:
        print("Balance error:", e)

# ================= DAILY BONUS =================
@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    try:
        user_id = str(message.chat.id)
        user = get_user(user_id)

        today = str(datetime.now().date())

        if user.get("last_bonus") == today:
            bot.send_message(user_id, "❌ Already claimed today")
            return

        new_balance = user["balance"] + 1

        update_user(user_id, {
            "balance": new_balance,
            "last_bonus": today
        })

        # referral commission
        if user["ref_by"]:
            ref_user = get_user(user["ref_by"])
            commission = int(1 * 0.25)

            update_user(user["ref_by"], {
                "balance": ref_user["balance"] + commission
            })

        bot.send_message(user_id, f"✅ ₹1 Added\n💰 Balance: ₹{new_balance}")

    except Exception as e:
        print("Bonus error:", e)

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    try:
        user_id = str(message.chat.id)
        user = get_user(user_id)

        link = f"https://t.me/{bot.get_me().username}?start={user_id}"

        bot.send_message(user_id,
            f"🔗 Link:\n{link}\n👥 {user['referrals']}\n💰 25% lifetime earning"
        )
    except Exception as e:
        print("Referral error:", e)

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

            status = "✅ Done" if done else f"₹{t.get('reward',0)}"
            text += f"{tid[:5]} → {t.get('text','Task')} ({status})\n"

        bot.send_message(user_id, text)

    except Exception as e:
        print("Task error:", e)
        bot.send_message(message.chat.id, "❌ Error loading tasks")

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
        reward = task.get("reward", 0)

        new_balance = user["balance"] + reward

        update_user(user_id, {"balance": new_balance})

        db.reference(f"completed/{user_id}/{tid}").set(True)

        # referral commission
        if user["ref_by"]:
            ref_user = get_user(user["ref_by"])
            commission = int(reward * 0.25)

            update_user(user["ref_by"], {
                "balance": ref_user["balance"] + commission
            })

        bot.send_message(user_id, f"✅ ₹{reward} added\n💰 Balance: ₹{new_balance}")

    except Exception as e:
        print("Done error:", e)
        bot.send_message(message.chat.id, "Use: /done TASK_ID")

# ================= WITHDRAW =================
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    try:
        user_id = str(message.chat.id)
        user = get_user(user_id)

        if user["balance"] < 20:
            bot.send_message(user_id, "❌ Minimum ₹20 required")
            return

        msg = bot.send_message(user_id, "Enter amount:")
        bot.register_next_step_handler(msg, process_withdraw)

    except Exception as e:
        print("Withdraw error:", e)

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

        bot.send_message(user_id, "✅ Request sent")

        bot.send_message(ADMIN_ID, f"💸 Withdraw\nUser: {user_id}\nAmount: ₹{amount}")

    except Exception as e:
        print("Withdraw process error:", e)
        bot.send_message(message.chat.id, "❌ Invalid amount")

# ================= RUN =================
print("Bot Running 🚀")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Polling Error:", e)
        time.sleep(5)
