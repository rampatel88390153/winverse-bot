import telebot
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("BOT_TOKEN missing!")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# =========================
# FIREBASE SAFE INIT
# =========================
try:
    firebase_json = os.getenv("FIREBASE_JSON")
    firebase_url = os.getenv("FIREBASE_URL")

    if not firebase_json or not firebase_url:
        raise Exception("Firebase ENV missing")

    cred_dict = json.loads(firebase_json)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            credentials.Certificate(cred_dict),
            {"databaseURL": firebase_url}
        )

    print("Firebase Connected ✅")

except Exception as e:
    print("Firebase Error:", e)


# =========================
# USER FUNCTIONS
# =========================

def get_user(user_id):
    try:
        ref = db.reference(f'users/{user_id}')
        user = ref.get()

        if not user:
            user = {
                "balance": 0,
                "referrals": 0,
                "last_bonus": ""
            }
            ref.set(user)

        return user
    except Exception as e:
        print("get_user error:", e)
        return {"balance": 0, "referrals": 0, "last_bonus": ""}


def update_user(user_id, data):
    try:
        db.reference(f'users/{user_id}').update(data)
    except Exception as e:
        print("update_user error:", e)


# =========================
# START + REFERRAL
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = str(message.chat.id)
        args = message.text.split()

        user = get_user(user_id)

        # Referral
        if len(args) > 1:
            ref_id = args[1]

            if ref_id != user_id:
                ref_user = get_user(ref_id)
                ref_user["balance"] += 2
                ref_user["referrals"] += 1
                update_user(ref_id, ref_user)

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("💰 Balance", "🎁 Daily Bonus")
        markup.row("👥 Referral", "📋 Tasks")
        markup.row("🏆 Leaderboard", "💸 Withdraw")

        bot.send_message(user_id, "👋 Welcome to Winverse Bot!", reply_markup=markup)

    except Exception as e:
        print("start error:", e)


# =========================
# BALANCE
# =========================

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    try:
        user = get_user(str(message.chat.id))
        bot.send_message(message.chat.id, f"💰 Balance: ₹{user['balance']}")
    except Exception as e:
        print("balance error:", e)


# =========================
# DAILY BONUS
# =========================

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def daily_bonus(message):
    try:
        user_id = str(message.chat.id)
        user = get_user(user_id)

        today = str(datetime.now().date())

        if user["last_bonus"] == today:
            bot.send_message(user_id, "❌ Already claimed today")
        else:
            user["balance"] += 5
            user["last_bonus"] = today
            update_user(user_id, user)

            bot.send_message(user_id, "✅ ₹5 Bonus Added")

    except Exception as e:
        print("bonus error:", e)


# =========================
# REFERRAL
# =========================

@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    try:
        user_id = str(message.chat.id)
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"

        bot.send_message(user_id, f"🔗 Your Link:\n{link}")
    except Exception as e:
        print("referral error:", e)


# =========================
# TASKS
# =========================

@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(message):
    bot.send_message(message.chat.id, "📋 Tasks coming soon...")


# =========================
# LEADERBOARD
# =========================

@bot.message_handler(func=lambda m: m.text == "🏆 Leaderboard")
def leaderboard(message):
    try:
        users = db.reference('users').get()

        if not users:
            bot.send_message(message.chat.id, "No users yet")
            return

        sorted_users = sorted(users.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]

        text = "🏆 Top Users:\n"
        for i, (uid, data) in enumerate(sorted_users, 1):
            text += f"{i}. ₹{data['balance']}\n"

        bot.send_message(message.chat.id, text)

    except Exception as e:
        print("leaderboard error:", e)


# =========================
# WITHDRAW
# =========================

@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    try:
        user_id = str(message.chat.id)
        user = get_user(user_id)

        if user["balance"] < 20:
            bot.send_message(user_id, "❌ Minimum ₹20 required")
        else:
            msg = bot.send_message(user_id, "💸 Enter amount:")
            bot.register_next_step_handler(msg, process_withdraw)

    except Exception as e:
        print("withdraw error:", e)


def process_withdraw(message):
    try:
        user_id = str(message.chat.id)
        amount = int(message.text)

        ref = db.reference(f'withdraw/{user_id}')
        ref.push({
            "amount": amount,
            "status": "pending",
            "time": str(datetime.now())
        })

        bot.send_message(user_id, "✅ Request sent (Admin approval pending)")

    except:
        bot.send_message(message.chat.id, "❌ Invalid amount")


# =========================
# RUN BOT
# =========================

print("Bot running 🚀")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Polling Error:", e)
