import telebot
import os
import json
import firebase_admin
from firebase_admin import credentials, db
import time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Firebase setup
firebase_data = json.loads(os.getenv("FIREBASE_JSON"))
cred = credentials.Certificate(firebase_data)
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_data["databaseURL"]
})

# USER GET
def get_user(uid):
    ref = db.reference(f"users/{uid}")
    user = ref.get()
    if not user:
        user = {
            "balance": 0,
            "referral": 0,
            "bonus": 0
        }
        ref.set(user)
    return user

# START
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    get_user(uid)
    
    bot.reply_to(message,
    "👋 Welcome\n\n"
    "Use commands:\n"
    "/balance\n"
    "/withdraw\n"
    "/refer\n"
    "/bonus\n"
    "/leaderboard")

# BALANCE
@bot.message_handler(commands=['balance'])
def balance(message):
    uid = str(message.from_user.id)
    user = get_user(uid)
    
    bot.reply_to(message, f"💰 Balance: ₹{user['balance']}")

# BONUS (daily)
@bot.message_handler(commands=['bonus'])
def bonus(message):
    uid = str(message.from_user.id)
    ref = db.reference(f"users/{uid}")
    user = get_user(uid)
    
    now = int(time.time())
    
    if now - user["bonus"] > 86400:
        user["balance"] += 5
        user["bonus"] = now
        ref.set(user)
        bot.reply_to(message, "🎁 ₹5 bonus added!")
    else:
        bot.reply_to(message, "❌ Already claimed today")

# REFERRAL
@bot.message_handler(commands=['refer'])
def refer(message):
    uid = str(message.from_user.id)
    bot.reply_to(message, f"👥 Your referral link:\nhttps://t.me/{bot.get_me().username}?start={uid}")

# WITHDRAW
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    uid = str(message.from_user.id)
    user = get_user(uid)
    
    if user["balance"] < 20:
        bot.reply_to(message, "❌ Minimum withdraw ₹20")
        return
    
    req = db.reference("withdraw_requests").push({
        "user": uid,
        "amount": user["balance"],
        "status": "pending"
    })
    
    user["balance"] = 0
    db.reference(f"users/{uid}").set(user)
    
    bot.reply_to(message, "✅ Withdraw request sent")

# LEADERBOARD
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    users = db.reference("users").get()
    
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:5]
    
    text = "🏆 Top Users:\n\n"
    for i, (uid, data) in enumerate(sorted_users):
        text += f"{i+1}. ₹{data['balance']}\n"
    
    bot.reply_to(message, text)

print("Bot running...")
bot.infinity_polling()
