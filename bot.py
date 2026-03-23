import telebot
import os
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = str(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

# =====================
# FIREBASE
# =====================
cred = credentials.Certificate("firebase.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': "https://winverse-bot-default-rtdb.firebaseio.com/"
})

# =====================
# USER FUNCTIONS
# =====================

def get_user(user_id):
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

def update_user(user_id, data):
    db.reference(f'users/{user_id}').update(data)

# =====================
# START
# =====================

@bot.message_handler(commands=['start'])
def start(message):
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

# =====================
# BALANCE
# =====================

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    user = get_user(str(message.chat.id))
    bot.send_message(message.chat.id, f"💰 Balance: ₹{user['balance']}")

# =====================
# DAILY BONUS
# =====================

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def daily_bonus(message):
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

# =====================
# REFERRAL
# =====================

@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    bot.send_message(user_id,
        f"🔗 Your Link:\n{link}\n\n👥 Total Referrals: {user['referrals']}\n💰 Earn ₹2 per referral"
    )

# =====================
# TASKS
# =====================

@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(message):
    tasks = db.reference("tasks").get()

    if not tasks:
        bot.send_message(message.chat.id, "❌ No tasks available")
        return

    text = "📋 Available Tasks:\n\n"
    for t in tasks.values():
        text += f"👉 {t['text']} - ₹{t['reward']}\n"

    bot.send_message(message.chat.id, text)

# =====================
# LEADERBOARD
# =====================

@bot.message_handler(func=lambda m: m.text == "🏆 Leaderboard")
def leaderboard(message):
    users = db.reference('users').get()

    if not users:
        bot.send_message(message.chat.id, "No users yet")
        return

    sorted_users = sorted(users.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]

    text = "🏆 Top Users:\n\n"

    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. ₹{data['balance']}\n"

    bot.send_message(message.chat.id, text)

# =====================
# WITHDRAW
# =====================

@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    if user["balance"] < 20:
        bot.send_message(user_id, "❌ Minimum ₹20 required")
    else:
        bot.send_message(user_id, "💸 Enter amount:")

        bot.register_next_step_handler(message, process_withdraw)

def process_withdraw(message):
    user_id = str(message.chat.id)

    try:
        amount = int(message.text)
    except:
        bot.send_message(user_id, "❌ Invalid amount")
        return

    user = get_user(user_id)

    if amount > user["balance"]:
        bot.send_message(user_id, "❌ Insufficient balance")
        return

    user["balance"] -= amount
    update_user(user_id, user)

    db.reference("withdraw").push({
        "user": user_id,
        "amount": amount,
        "status": "pending",
        "time": str(datetime.now())
    })

    bot.send_message(user_id, "✅ Withdraw request sent")

# =====================
# ADMIN COMMANDS
# =====================

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if str(message.chat.id) != ADMIN_ID:
        return

    try:
        _, uid, amount = message.text.split()
        amount = int(amount)

        user = get_user(uid)
        user["balance"] += amount
        update_user(uid, user)

        bot.send_message(message.chat.id, "✅ Balance added")
    except:
        bot.send_message(message.chat.id, "❌ Error")

@bot.message_handler(commands=['addtask'])
def add_task(message):
    if str(message.chat.id) != ADMIN_ID:
        return

    try:
        text = message.text.replace("/addtask ", "")
        db.reference("tasks").push({
            "text": text,
            "reward": 2
        })
        bot.send_message(message.chat.id, "✅ Task added")
    except:
        bot.send_message(message.chat.id, "❌ Error")

# =====================
# RUN
# =====================

print("Bot running...")
bot.infinity_polling()
