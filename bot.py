import asyncio
import logging
import sqlite3
import hashlib
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8239650192:AAEia0wuR4G6ai-iJQzpc64mBSwjTCkLMzA"
ADMIN_ID = 7144593342

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect('winverse_earn.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
        referral_code TEXT UNIQUE, referred_by INTEGER, balance REAL DEFAULT 0,
        total_earned REAL DEFAULT 0, signup_bonus INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_text TEXT, reward REAL DEFAULT 2,
        completed_by INTEGER, completed_at TIMESTAMP, is_active INTEGER DEFAULT 1)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
        charge REAL DEFAULT 2, final_amount REAL, upi_id TEXT,
        status TEXT DEFAULT 'pending', requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS task_completions (
        user_id INTEGER, task_id INTEGER, PRIMARY KEY(user_id, task_id))''')
    
    # Default Task ₹2
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_active=1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO tasks (task_text, reward, is_active) VALUES (?, 2, 1)", 
                      ("🎯 Task 1: Winverse join confirmation - Complete karo!",))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('winverse_earn.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id, username, first_name, referred_by=None):
    conn = sqlite3.connect('winverse_earn.db')
    cursor = conn.cursor()
    ref_code = hashlib.md5(f"{user_id}".encode()).hexdigest()[:8].upper()
    
    cursor.execute('''INSERT OR IGNORE INTO users 
                     (user_id,username,first_name,referral_code,referred_by) 
                     VALUES(?,?,?,?,?)''', (user_id,username,first_name,ref_code,referred_by))
    conn.commit()
    conn.close()
    
    # Signup bonus ₹10 (once)
    user = get_user(user_id)
    if user and user[7] == 0:
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET signup_bonus=1, balance=balance+10, total_earned=total_earned+10 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
    
    # Referral bonus ₹10
    if referred_by:
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance=balance+10, total_earned=total_earned+10 WHERE user_id=?", (referred_by,))
        conn.commit()
        conn.close()

def get_active_task():
    conn = sqlite3.connect('winverse_earn.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE is_active=1 LIMIT 1")
    task = cursor.fetchone()
    conn.close()
    return task

def complete_task(user_id, task_id):
    conn = sqlite3.connect('winverse_earn.db')
    cursor = conn.cursor()
    
    # Check already completed
    cursor.execute("SELECT 1 FROM task_completions WHERE user_id=? AND task_id=?", (user_id, task_id))
    if cursor.fetchone(): 
        conn.close()
        return False
    
    cursor.execute("SELECT reward FROM tasks WHERE id=?", (task_id,))
    reward = cursor.fetchone()[0]  # ₹2 default
    
    # Add reward
    cursor.execute("UPDATE users SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?", (reward, reward, user_id))
    cursor.execute("INSERT INTO task_completions(user_id,task_id) VALUES(?,?)", (user_id, task_id))
    cursor.execute("UPDATE tasks SET is_active=0, completed_by=?, completed_at=CURRENT_TIMESTAMP WHERE id=?", (user_id, task_id))
    
    conn.commit()
    conn.close()
    return True

# APP LIKE MAIN MENU
def main_menu():
    keyboard = [
        [InlineKeyboardButton("📋 TASKS", callback_data="tasks")],
        [InlineKeyboardButton("💰 BALANCE", callback_data="balance")],
        [InlineKeyboardButton("🔗 REFERRAL", callback_data="referral")],
        [InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Referral handling
    referred_by = None
    if args:
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE referral_code=?", (args[0].upper(),))
        ref = cursor.fetchone()
        if ref: referred_by = ref[0]
        conn.close()
    
    create_user(user.user_id, user.username, user.first_name, referred_by)
    
    user_data = get_user(user.user_id)
    ref_link = f"t.me/winverse_earn_bot?start={user_data[3]}" if user_data else ""
    
    text = f"""{'='*40}
🚀 **WINVERSE EARN APP** 🚀
{'='*40}

👋 **Welcome {user.first_name}!**

💎 **JOIN BONUS**: +₹10 ✅
🔗 **Ref Code**: `{user_data[3] if user_data else 'N/A'}`
📱 **Share**: {ref_link}

{'='*40}
🎮 **MAIN MENU** 🎮
{'='*40}"""
    
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode='Markdown')

# Button Handler - APP LIKE UI
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if query.data == "tasks":
        task = get_active_task()
        if task:
            kb = [[InlineKeyboardButton("✅ COMPLETE TASK (+₹2)", callback_data=f"complete_{task[0]}")],
                  [InlineKeyboardButton("🏠 HOME", callback_data="home")]]
            text = f"""📱 **TASK PANEL**

🎯 **Task #{task[0]}**
{task[1]}

💰 **Reward**: ₹{task[2]}
⏰ **Status**: Available

👆 **Tap Complete Button!**"""
        else:
            kb = [[InlineKeyboardButton("🔄 REFRESH", callback_data="tasks")],
                  [InlineKeyboardButton("➕ REQUEST NEW", callback_data="home")]]
            text = "📭 **No Active Tasks**\n\n⏳ Admin new task add kar raha hai!"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    
    elif query.data == "balance":
        user = get_user(uid)
        text = f"""💳 **BALANCE DASHBOARD**

{'='*25}
💰 **Available**: ₹{user[5]:.2f}
⭐ **Total Earned**: ₹{user[6]:.2f}
🎁 **Signup Bonus**: ₹10 ✅

{'='*25}
⚡ **Quick Actions:**
"""
        kb = [[InlineKeyboardButton("📋 TASKS", callback_data="tasks")],
              [InlineKeyboardButton("🔗 REFERRAL", callback_data="referral")],
              [InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw")],
              [InlineKeyboardButton("🏠 HOME", callback_data="home")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    
    elif query.data == "referral":
        user = get_user(uid)
        text = f"""🔗 **REFERRAL CENTER**

💰 **Per Referral**: ₹10
∞ **Unlimited Referrals**

{'='*25}
📱 **Your Link:**
`t.me/winverse_earn_bot?start={user[3]}`

🎯 **Ref Code**: `{user[3]}`

👥 **Share anywhere & Earn!**
"""
        kb = [[InlineKeyboardButton("📋 TASKS", callback_data="tasks")],
              [InlineKeyboardButton("💰 BALANCE", callback_data="balance")],
              [InlineKeyboardButton("🏠 HOME", callback_data="home")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    
    elif query.data == "withdraw":
        user = get_user(uid)
        if user[5] >= 20:
            text = f"""💸 **WITHDRAWAL PANEL**

💰 **Current Balance**: ₹{user[5]:.2f}
💳 **Min Amount**: ₹20
⚡ **Processing Fee**: ₹2

{'='*25}
📱 **Enter UPI ID & Amount:**

*Format:* `UPI | Amount`
*Example:* `9123456789@paytm | 25`
"""
            await query.edit_message_text(text, parse_mode='Markdown')
            context.user_data['await_withdraw'] = uid
        else:
            await query.answer("❌ Minimum ₹20 balance required!", show_alert=True)
    
    elif query.data == "home":
        await query.edit_message_text("🏠 **Winverse Earn App**\n\nChoose from main menu:", reply_markup=main_menu(), parse_mode='Markdown')
    
    elif query.data.startswith("complete_"):
        task_id = int(query.data.split("_")[1])
        task = get_active_task()
        
        if task and task[0] == task_id:
            if complete_task(uid, task_id):
                user = get_user(uid)
                text = f"""🎉 **TASK COMPLETED!**

✅ **Task #{task_id}** - Done!
💰 **Reward Earned**: +₹{task[2]}
💳 **New Balance**: ₹{user[5]:.2f}

⭐ **Perfect! Keep Earning!**
"""
                kb = [[InlineKeyboardButton("📋 NEW TASK", callback_data="tasks")],
                      [InlineKeyboardButton("💰 BALANCE", callback_data="balance")],
                      [InlineKeyboardButton("🏠 HOME", callback_data="home")]]
            else:
                text = "❌ This task already completed by you!"
                kb = [[InlineKeyboardButton("🔄 NEW TASKS", callback_data="tasks")]]
        else:
            text = "❌ Task expired! Check new tasks."
            kb = [[InlineKeyboardButton("📋 TASKS", callback_data="tasks")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# Withdraw Request Handler
async def withdraw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('await_withdraw'):
        return
    
    uid = context.user_data['await_withdraw']
    if update.effective_user.id != uid:
        return
    
    try:
        parts = update.message.text.split('|')
        upi = parts[0].strip()
        withdraw_amount = float(parts[1].strip())
        
        user = get_user(uid)
        if withdraw_amount > user[5] or withdraw_amount < 20:
            await update.message.reply_text("❌ Invalid amount! Min ₹20 & balance check karo.")
            return
        
        charge = 2
        final_amount = withdraw_amount - charge
        
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO withdrawals 
                         (user_id, amount, charge, final_amount, upi_id) 
                         VALUES(?,?,?,?,?)""", (uid, withdraw_amount, charge, final_amount, upi))
        
        # Deduct balance
        cursor.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (withdraw_amount, uid))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"""✅ **Withdraw Request Created!**

💰 **Amount**: ₹{withdraw_amount}
💸 **Charge**: ₹2
💵 **Final**: ₹{final_amount}
📱 **UPI**: `{upi}`

⏳ **Status**: Pending
🔔 Admin ko notification chala gaya!

*Payment 24hr me milega*""", parse_mode='Markdown')
        
        # ADMIN NOTIFICATION
        await context.bot.send_message(ADMIN_ID, f"""🚨 **NEW WITHDRAW REQUEST #{cursor.lastrowid}**

👤 **User**: {user[2]} (ID: {uid})
💰 **Amount**: ₹{withdraw_amount}
💵 **Pay**: ₹{final_amount}
📱 **UPI**: `{upi}`

**Approve Command:**
`/approve {cursor.lastrowid}`""", parse_mode='Markdown')
        
        context.user_data['await_withdraw'] = None
        
    except:
        await update.message.reply_text("❌ Wrong format!\n`UPI | Amount`\nExample: `9123456789@paytm | 25`")

# ADMIN PANEL
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    kb = [[InlineKeyboardButton("➕ ADD TASK", callback_data="admin_add")],
          [InlineKeyboardButton("💰 WITHDRAWALS", callback_data="admin_wd")],
          [InlineKeyboardButton("📊 STATS", callback_data="admin_stats")],
          [InlineKeyboardButton("👥 USERS", callback_data="admin_users")]]
    
    await update.message.reply_text("🔧 **WINVERSE ADMIN DASHBOARD**", reply_markup=InlineKeyboardMarkup(kb))

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID: return
    await query.answer()
    
    if query.data == "admin_add":
        await query.edit_message_text("📝 **ADD NEW TASK** (₹2 default)\n\n`Task Text | Reward`\n*Ex:* `Daily Check-in | 2`", parse_mode='Markdown')
        context.user_data['admin_add_task'] = True
    
    elif query.data == "admin_wd":
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id,user_id,final_amount,upi_id FROM withdrawals WHERE status='pending'")
        wds = cursor.fetchall()
        conn.close()
        
        if wds:
            text = "💸 **PENDING WITHDRAWS**:\n\n"
            for wd in wds:
                text += f"🆔 `{wd[0]}` | ₹{wd[2]} | {wd[3]}\n"
            text += "\nApprove: `/approve ID`"
        else:
            text = "✅ No pending withdrawals!"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == "admin_stats":
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*),SUM(balance),SUM(total_earned) FROM users")
        stats = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_active=1")
        tasks = cursor.fetchone()[0]
        conn.close()
        
        text = f"""📊 **ADMIN STATS**
👥 Users: {stats[0]}
💰 Total Balance: ₹{stats[1]:.2f}
⭐ Total Earned: ₹{stats[2]:.2f}
📋 Active Tasks: {tasks}"""
        await query.edit_message_text(text, parse_mode='Markdown')

async def admin_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not context.user_data.get('admin_add_task'):
        return
    
    try:
        parts = update.message.text.split('|')
        task_text = parts[0].strip()
        reward = float(parts[1].strip()) if len(parts) > 1 else 2.0
        
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks(task_text,reward,is_active) VALUES(?,?,1)", (task_text, reward))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ **TASK ADDED #{cursor.lastrowid}**\n\n📝 {task_text}\n💰 ₹{reward}\n\nUsers ko dikhne lagega!")
        context.user_data['admin_add_task'] = False
    except:
        await update.message.reply_text("❌ Format: `Task | Reward`\nDefault reward ₹2")

async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    try:
        wid = int(context.args[0])
        conn = sqlite3.connect('winverse_earn.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM withdrawals WHERE id=? AND status='pending'", (wid,))
        result = cursor.fetchone()
        
        if result:
            cursor.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (wid,))
            conn.commit()
            await context.bot.send_message(result[0], "✅ **PAYMENT APPROVED!**\n💰 Money sent to your UPI!\n\nThank you! 🎉")
            await update.message.reply_text(f"✅ **Withdraw #{wid} APPROVED**\nUser notified!")
        else:
            await update.message.reply_text("❌ Invalid withdraw ID!")
        conn.close()
    except:
        await update.message.reply_text("❌ `/approve ID` - Example: `/approve 1`")

def main():
    init_db()
    print("🚀 WINVERSE EARN BOT v2.0 - Starting...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("approve", approve_cmd))
    
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern="^admin_"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_request))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_task))
    
    print("✅ BOT LIVE! t.me/winverse_earn_bot")
    print("🔧 Admin: /admin")
    app.run_polling()

if __name__ == '__main__':
    main()