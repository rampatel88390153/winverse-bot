import telebot
import os
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = "7144593342"

bot = telebot.TeleBot(BOT_TOKEN)

# ================= FIREBASE =================
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://winverse-bot-default-rtdb.firebaseio.com/"
        })
    print("Firebase Connected ✅")
except Exception as e:
    print("Firebase Error:", e)

# ================= USER =================
def get_user(user_id):
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

def update_user(user_id, data):
    db.reference(f'users/{user_id}').update(data)

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    args = message.text.split()

    user = get_user(user_id)

    # ✅ Referral system FIXED
    if len(args) > 1 and user.get("ref_by") == "":
        ref_id = args[1]

        if ref_id != user_id:
            ref_user = get_user(ref_id)

            # new user bonus
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

# ================= BALANCE =================
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    user = get_user(str(message.chat.id))
    bot.send_message(message.chat.id, f"💰 Balance: ₹{user['balance']}")

# ================= DAILY BONUS =================
@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    today = str(datetime.now().date())

    if user["last_bonus"] == today:
        bot.send_message(user_id, "❌ Already claimed")
    else:
        user["balance"] += 5
        user["last_bonus"] = today
        update_user(user_id, user)

        # referral 25% earning
        if user.get("ref_by"):
            ref_user = get_user(user["ref_by"])
            ref_user["balance"] += int(5 * 0.25)
            update_user(user["ref_by"], ref_user)

        bot.send_message(user_id, "✅ ₹5 Added")

# ================= REFERRAL =================
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    bot.send_message(user_id,
        f"🔗 Link:\n{link}\n\n👥 Total: {user['referrals']}\n💰 25% lifetime earning"
    )

# ================= TASKS =================
@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(message):
    user_id = str(message.chat.id)
    tasks = db.reference("tasks").get()

    if not tasks:
        bot.send_message(user_id, "❌ No tasks")
        return

    text = "📋 Tasks:\n\n"

    for tid, t in tasks.items():
        done = db.reference(f"completed/{user_id}/{tid}").get()

        if done:
            status = "✅ Done"
        else:
            status = f"💰 ₹{t['reward']}"

        text += f"{tid[:4]} → {t['text']} ({status})\n"

    bot.send_message(user_id, text)

# ================= COMPLETE TASK =================
@bot.message_handler(commands=['done'])
def done_task(message):
    user_id = str(message.chat.id)

    try:
        tid = message.text.split()[1]
        task = db.reference(f"tasks/{tid}").get()

        if not task:
            bot.send_message(user_id, "Invalid Task ID")
            return

        # already done
        if db.reference(f"completed/{user_id}/{tid}").get():
            bot.send_message(user_id, "❌ Already completed")
            return

        user = get_user(user_id)
        user["balance"] += task["reward"]
        update_user(user_id, user)

        db.reference(f"completed/{user_id}/{tid}").set(True)

        # referral earning
        if user.get("ref_by"):
            ref_user = get_user(user["ref_by"])
            ref_user["balance"] += int(task["reward"] * 0.25)
            update_user(user["ref_by"], ref_user)

        bot.send_message(user_id, f"✅ ₹{task['reward']} added")

    except:
        bot.send_message(user_id, "Usage: /done TASK_ID")

# ================= LEADERBOARD =================
@bot.message_handler(func=lambda m: m.text == "🏆 Leaderboard")
def leaderboard(message):
    users = db.reference("users").get()

    if not users:
        bot.send_message(message.chat.id, "No users")
        return

    sorted_users = sorted(users.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]

    text = "🏆 Top Users:\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. ₹{data['balance']}\n"

    bot.send_message(message.chat.id, text)

# ================= WITHDRAW =================
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    if user["balance"] < 20:
        bot.send_message(user_id, "❌ Minimum ₹20 required")
    else:
        msg = bot.send_message(user_id, "Enter amount:")
        bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = str(message.chat.id)

    try:
        amount = int(message.text)
    except:
        bot.send_message(user_id, "Invalid")
        return

    user = get_user(user_id)

    if amount > user["balance"]:
        bot.send_message(user_id, "Not enough balance")
        return

    db.reference("withdraw").push({
        "user": user_id,
        "amount": amount,
        "status": "pending"
    })

    bot.send_message(user_id, "✅ Request sent to admin")

    # notify admin
    bot.send_message(ADMIN_ID, f"💸 Withdraw Request\nUser: {user_id}\nAmount: ₹{amount}")

# ================= ADMIN =================
@bot.message_handler(commands=['addtask'])
def add_task(message):
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
