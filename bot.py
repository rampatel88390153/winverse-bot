import telebot
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Firebase connect
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': https://YOUR-DATABASE.firebaseio.com/
})

# Helper functions
def get_user(user_id):
    ref = db.reference(f'users/{user_id}')
    user = ref.get()
    if not user:
        user = {
            "balance": 0,
            "referrals": 0,
            "last_bonus": "",
        }
        ref.set(user)
    return user

def update_user(user_id, data):
    db.reference(f'users/{user_id}').update(data)

# START
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    get_user(user_id)

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Balance", "🎁 Daily Bonus")
    markup.row("👥 Referral", "📋 Tasks")
    markup.row("🏆 Leaderboard", "💸 Withdraw")

    bot.send_message(user_id, "👋 Welcome to Winverse Bot!", reply_markup=markup)

# BALANCE
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    user = get_user(str(message.chat.id))
    bot.send_message(message.chat.id, f"💰 Your Balance: ₹{user['balance']}")

# DAILY BONUS
@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    today = str(datetime.now().date())

    if user["last_bonus"] == today:
        bot.send_message(user_id, "❌ Already claimed today")
    else:
        user["balance"] += 5
        user["last_bonus"] = today
        update_user(user_id, user)
        bot.send_message(user_id, "✅ ₹5 Daily Bonus Added")

# REFERRAL
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    user_id = str(message.chat.id)
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id, f"🔗 Your Referral Link:\n{link}")

# TASKS
@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(message):
    bot.send_message(message.chat.id, "📋 Complete tasks and earn soon (Coming update)")

# LEADERBOARD
@bot.message_handler(func=lambda m: m.text == "🏆 Leaderboard")
def leaderboard(message):
    users = db.reference('users').get()
    sorted_users = sorted(users.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]

    text = "🏆 Top Users:\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. ₹{data['balance']}\n"

    bot.send_message(message.chat.id, text)

# WITHDRAW
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(message):
    user_id = str(message.chat.id)
    user = get_user(user_id)

    if user["balance"] < 20:
        bot.send_message(user_id, "❌ Minimum ₹20 required")
    else:
        bot.send_message(user_id, "💸 Enter amount to withdraw:")

        bot.register_next_step_handler(message, process_withdraw)

def process_withdraw(message):
    user_id = str(message.chat.id)
    amount = int(message.text)

    ref = db.reference(f'withdraw/{user_id}')
    ref.push({
        "amount": amount,
        "status": "pending"
    })

    bot.send_message(user_id, "✅ Withdraw request sent (Admin approval pending)")

bot.infinity_polling()
