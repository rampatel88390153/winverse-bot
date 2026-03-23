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

        if user is None:
            user = {
                "balance": 10,
                "referrals": 0,
                "ref_by": "",
                "last_bonus": "0"
            }
            ref.set(user)

        return user
    except Exception as e:
        print("Get user error:", e)
        return {"balance": 0, "referrals": 0, "ref_by": "", "last_bonus": "0"}

def update_user(user_id, data):
    try:
        db.reference(f'users/{user_id}').update(data)
    except Exception as e:
        print("Update error:", e)

# ================= MENU =================
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Balance", "🎁 Daily Bonus")
    markup.row("👥 Referral", "📋 Tasks")
    markup.row("🏆 Leaderboard", "💸 Withdraw")
    return markup

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = str(message.chat.id)
        args = message.text.split()

        user = get_user(user_id)

        # referral only once
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

        bot.send_message(user_id, "👋 Welcome to Winverse Bot!", reply_markup=main_menu())

    except Exception as e:
        print("Start Error:", e)

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    try:
        user_id = str(message.chat.id)
        user = db.reference(f'users/{user_id}').get()

        if user is None:
            user = get_user(user_id)

        bot.send_message(user_id, f"💰 Balance: ₹{user.get('balance',0)}")

    except Exception as e:
        print("Balance error:", e)

# ================= DAILY BONUS =================
@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    try:
        user_id = str(message.chat.id)

        ref = db.reference(f'users/{user_id}')
        user = ref.get()

        today = datetime.now().strftime("%Y-%m-%d")

        if user.get("last_bonus") == today:
            bot.send_message(user_id, "❌ Already claimed today")
            return

        new_balance = user.get("balance", 0) + 1

        ref.update({
            "balance": new_balance,
            "last_bonus": today
        })

        # referral commission
        if user.get("ref_by"):
            ref_user_id = user["ref_by"]
            ref_ref = db.reference(f'users/{ref_user_id}')
            ref_user = ref_ref.get()

            commission = int(1 * 0.25)

            ref_ref.update({
                "balance": ref_user.get("balance", 0) + commission
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

# ================= RUN =================
print("Bot Running 🚀")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Polling Error:", e)
        time.sleep(5)
