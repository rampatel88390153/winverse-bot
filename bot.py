import telebot
import os
import json
import firebase_admin
from firebase_admin import credentials, db
import time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

firebase_data = json.loads(os.getenv("FIREBASE_JSON"))
cred = credentials.Certificate(firebase_data)

firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_data["databaseURL"]
})

def get_user(uid):
    ref = db.reference(f"users/{uid}")
    user = ref.get()
    if not user:
        user = {"balance": 0, "bonus": 0}
        ref.set(user)
    return user

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    get_user(uid)
    bot.reply_to(message, "👋 Welcome!")

@bot.message_handler(commands=['balance'])
def balance(message):
    uid = str(message.from_user.id)
    user = get_user(uid)
    bot.reply_to(message, f"💰 Balance: ₹{user['balance']}")

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
        bot.reply_to(message, "❌ Already claimed")

print("Bot running...")
bot.infinity_polling()
