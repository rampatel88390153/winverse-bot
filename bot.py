import logging
import sqlite3
from datetime import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Bot token (provided)
BOT_TOKEN = "8239650192:AAEia0wu"

# Admin ID (change to your Telegram user ID)
ADMIN_ID = 123456789  # Replace with your actual Telegram ID

# Database setup
def init_db():
    conn = sqlite3.connect('earn_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0,
        tasks_done INTEGER DEFAULT 0,
        referrals INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        withdraw_requests INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdraws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        upi TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Get user data
def get_user(user_id):
    conn = sqlite3.connect('earn_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

# Update or create user
def update_user(user_id, username='', **kwargs):
    conn = sqlite3.connect('earn_bot.db', check_same_thread=False)
    c = conn.cursor()
    user = get_user(user_id)
    if not user:
        c.execute('INSERT INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    for key, value in kwargs.items():
        c.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()
    conn.close()

# Add referral
def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect('earn_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', (referrer_id, referred_id))
    conn.commit()
    conn.close()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user(user.id, user.username)
    
    # Check referral
    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id and get_user(ref_id):
                user_data = get_user(user.id)
                if not user_data[5]:  # referred_by is NULL
                    add_referral(ref_id, user.id)
                    update_user(ref_id, referrals=get_user(ref_id)[4] + 1)
                    update_user(user.id, referred_by=ref_id)
                    await context.bot.send_message(ref_id, 
                        "🎉 New referral! You earned ₹10\nBalance updated!")
        except:
            pass
    
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📋 Tasks (₹2)", callback_data="tasks")],
        [InlineKeyboardButton("👥 Refer & Earn (₹10)", callback_data="refer")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🌟 Welcome to *Winverse Earn Bot*!\n\n"
        f"👋 Hi {user.first_name}!\n"
        f"Earn real money by completing tasks and referring friends!\n\n"
        f"💎 Features:\n"
        f"• Tasks: ₹2 each (one-time)\n"
        f"• Referrals: ₹10 unlimited\n"
        f"• Min withdraw: ₹20\n\n"
        f"🚀 Start earning now!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_data = get_user(query.from_user.id)
    balance = user_data[2] if user_data else 0
    tasks_done = user_data[3] if user_data else 0
    
    if query.data == "balance":
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main")]]
        await query.edit_message_text(
            f"💰 *Your Balance*\n\n"
            f"💵 Current Balance: *₹{balance:.2f}*\n"
            f"📊 Tasks Completed: {tasks_done}\n"
            f"👥 Your Referrals: {user_data[4] if user_data else 0}\n\n"
            f"💸 *Minimum withdrawal: ₹20*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "tasks":
        if tasks_done >= 1:
            await query.edit_message_text(
                "✅ *Task already completed!*\n\n"
                "You can only complete this task once.\n"
                f"💰 Earn more by referring friends (₹10 each)!",
                parse_mode='Markdown'
            )
        else:
            update_user(query.from_user.id, tasks_done=1, balance=balance + 2)
            await query.edit_message_text(
                "🎉 *Task Completed!*\n\n"
                f"✅ You earned *₹2*\n"
                f"💰 New Balance: *₹{balance + 2:.2f}*\n\n"
                f"👥 Share with friends to earn ₹10 per referral!",
                parse_mode='Markdown'
            )
    
    elif query.data == "refer":
        ref_link = f"https://t.me/winverse_earn_bot?start={query.from_user.id}"
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main")]]
        await query.edit_message_text(
            f"👥 *Referral Program*\n\n"
            f"💰 Earn *₹10* for each friend you refer!\n"
            f"📈 *Unlimited referrals*\n\n"
            f"🔗 *Your Referral Link:*\n"
            f"`{ref_link}`\n\n"
            f"📋 Share this link with friends!\n"
            f"💎 They get started, you get ₹10 instantly!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "withdraw":
        if balance < 20:
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main")]]
            await query.edit_message_text(
                f"❌ *Insufficient Balance*\n\n"
                f"💰 Current Balance: *₹{balance:.2f}*\n"
                f"📏 Minimum withdrawal: *₹20*\n\n"
                f"💎 Complete tasks & referrals to reach withdrawal limit!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            keyboard = [[InlineKeyboardButton("✅ Request Withdraw", callback_data="confirm_withdraw")]]
            await query.edit_message_text(
                f"💸 *Withdrawal Request*\n\n"
                f"💰 Available Balance: *₹{balance:.2f}*\n"
                f"💳 Withdrawal Charge: ₹2\n"
                f"📥 *Send your UPI ID* in next message\n\n"
                f"⚠️ Admin will approve within 24hrs",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            context.user_data['awaiting_withdraw'] = True
    
    elif query.data == "confirm_withdraw":
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main")]]
        await query.edit_message_text(
            "💳 *Send your UPI ID*\n\n"
            "Example: `yourname@paytm` or `9123456789@upi`\n\n"
            "⚠️ Make sure UPI is correct!\n"
            "Admin will send payment within 24hrs after approval.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        context.user_data['awaiting_upi'] = True
    
    elif query.data == "main":
        keyboard = [
            [InlineKeyboardButton("💰 Balance", callback_data="balance")],
            [InlineKeyboardButton("📋 Tasks (₹2)", callback_data="tasks")],
            [InlineKeyboardButton("👥 Refer & Earn (₹10)", callback_data="refer")],
            [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
        ]
        await query.edit_message_text(
            f"🌟 *Winverse Earn Bot*\n\n"
            f"👋 Hi {query.from_user.first_name}!\n"
            f"💰 Balance: *₹{balance:.2f}*\n\n"
            f"🚀 Choose an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# Handle UPI messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_upi'):
        user_data = get_user(update.effective_user.id)
        balance = user_data[2]
        upi = update.message.text.strip()
        
        # Deduct balance (₹2 charge)
        final_amount = balance - 2
        update_user(update.effective_user.id, balance=final_amount, withdraw_requests=user_data[6] + 1)
        
        # Save withdraw request
        conn = sqlite3.connect('earn_bot.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT INTO withdraws (user_id, amount, upi) VALUES (?, ?, ?)', 
                 (update.effective_user.id, final_amount, upi))
        conn.commit()
        conn.close()
        
        # Notify admin
        admin_msg = (
            f"💸 *New Withdrawal Request*\n\n"
            f"👤 User: {update.effective_user.first_name} (@{update.effective_user.username})\n"
            f"🆔 ID: `{update.effective_user.id}`\n"
            f"💰 Amount: *₹{final_amount:.2f}*\n"
            f"💳 UPI: `{upi}`\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        try:
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
        except:
            pass
        
        await update.message.reply_text(
            f"✅ *Withdrawal Requested!*\n\n"
            f"💰 Amount: *₹{final_amount:.2f}*\n"
            f"💳 UPI: `{upi}`\n"
            f"📋 Status: *Pending Approval*\n\n"
            f"⏳ Admin will process within 24hrs\n"
            f"💎 Check back later!",
            parse_mode='Markdown'
        )
        context.user_data.clear()

# Admin panel
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect('earn_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT SUM(balance) FROM users')
    total_balance = c.fetchone()[0] or 0
    c.execute('SELECT * FROM withdraws WHERE status = "pending" ORDER BY created_at DESC LIMIT 5')
    pending_withdraws = c.fetchall()
    conn.close()
    
    withdraw_text = ""
    for withdraw in pending_withdraws:
        withdraw_text += f"🆔 {withdraw[1]} | ₹{withdraw[2]:.2f} | {withdraw[3]}\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("💸 Pending Withdraws", callback_data="admin_withdraws")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")]
    ]
    
    await update.message.reply_text(
        f"👨‍💼 *Admin Panel*\n\n"
        f"📊 *Stats:*\n"
        f"👥 Total Users: *{total_users}*\n"
        f"💰 Total Balance: *₹{total_balance:.2f}*\n\n"
        f"⏳ *Pending Withdrawals (Top 5):*\n{withdraw_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Winverse Earn Bot started!")
    app.run_polling()

if __name__ == '__main__':
    main()