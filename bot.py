# bot.py - Muslat Express Bot
import logging
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import database as db
import sqlite3

# --- CONFIGURATION ---
TOKEN = '8308776708:AAFdYLUCBnlbbxnh9t7gyASpSnJLB5E_AUY'  
ADMIN_IDS = [1273176859]   

# --- DATABASE INITIALIZATION ---
def init_database():
    """Create database tables if they don't exist"""
    print("🔧 Creating database tables...")
    
    conn = sqlite3.connect('muslat.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (telegram_id INTEGER PRIMARY KEY, 
                  phone_number TEXT UNIQUE, 
                  name TEXT)''')
    
    # Create shipments table
    c.execute('''CREATE TABLE IF NOT EXISTS shipments
                 (tracking_number TEXT PRIMARY KEY, 
                  phone_number TEXT, 
                  client_name TEXT, 
                  status TEXT DEFAULT 'In Transit',
                  telegram_id INTEGER)''')
    
    conn.commit()
    conn.close()
    
    print("✅ Database tables created successfully!")

# --- STATES FOR CONVERSATION ---
WAITING_FOR_TRACKING = 1
WAITING_FOR_PHONE_VERIFY = 2

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 0: Client Registration"""
    user = update.effective_user
    # Check if already registered
    # Note: We rely on phone number for logic, but we need to ask for it if not provided
    
    keyboard = [[KeyboardButton("# Share Phone Number", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Welcome to Muslat Express, {user.first_name}! 📦\n\n"
        "To track packages and receive notifications, please register your phone number.",
        reply_markup=reply_markup
    )

async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the phone number contact"""
    contact = update.message.contact
    phone = contact.phone_number
    user_id = contact.user_id
    name = contact.first_name
    
    # Save to database
    db.add_user(user_id, phone, name)
    
    await update.message.reply_text(
        f"✅ Registration successful!\n\n"
        f"Your phone number {phone} has been registered.\n"
        f"You can now use /track to check your shipments."
    )

# Add your existing functions here (receive_tracking, receive_verify_phone, etc.)
# ...

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    from telegram.ext import ConversationHandler
    
    # Step 1: Initialize Database Tables FIRST
    init_database()
    
    application = Application.builder().token(TOKEN).build()
    
    # Registration Handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    
    # Add your other handlers here
    # application.add_handler(...)
    
    print("Bot is running...")
    application.run_polling()