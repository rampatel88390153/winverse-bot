import telebot
import firebase_admin
from firebase_admin import credentials, db
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://YOUR-PROJECT-ID-default-rtdb.firebaseio.com/'
})

def get_user(uid):
    ref = db.reference(f"users/{uid}")
    user = ref.get()
    if not user:
        user = {"balance": 0}
        ref.set(user)
    return user

def save_user(uid, data):
    db.reference(f"users/{uid}").update(data)

@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.chat.id)
    bot.send_message(msg.chat.id, "Welcome to WINVERSE 💸")

@bot.message_handler(commands=['task'])
def task(msg):
    user = get_user(msg.chat.id)
    user["balance"] += 1
    save_user(msg.chat.id, user)
    bot.send_message(msg.chat.id, "Task done ₹1 added")

@bot.message_handler(commands=['wallet'])
def wallet(msg):
    user = get_user(msg.chat.id)
    bot.send_message(msg.chat.id, f"Balance: ₹{user['balance']}")

bot.infinity_polling()
