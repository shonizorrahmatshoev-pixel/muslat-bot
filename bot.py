import os
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from database import (init_database, register_user, check_user_registered, get_user_info, 
                      add_shipment, get_shipment_info, list_all_shipments, get_shipments_by_phone)

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "0").split(",")]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///muslat.db")

def create_menu_keyboard():
    """Clean menu buttons"""
    keyboard = [
        [KeyboardButton('/Start'), KeyboardButton('/Help')],
        [KeyboardButton('/Track'), KeyboardButton('/Register')]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context: CallbackContext):
    """Welcome message with menu buttons"""
    msg = "**👋 Welcome to Muslat Express!**\n\n" \
          "**💡 How to track:**\n" \
          "1️⃣ Click **Contact button** to register automatically\n" \
          "2️⃣ Send your tracking number directly\n\n" \
          "Send a contact or use `/register` to start."
    await update.message.reply_text(msg, reply_markup=create_menu_keyboard())

app.add_handler(CommandHandler('start', start_command))

async def help_command(update: Update, context: CallbackContext):
    """Command guide"""
    msg = "**📦 Commands:**\n\n" \
          "**For All Users:**\n" \
          "/start - Start the bot\n" \
          "/help - Show this help\n" \
          "/track <number> - Track package\n" \
          "/register - Register with phone\n\n" \
          "**Admin Only:**\n" \
          "/addshipment <tracking> <name> <phone> [status] - Add order\n" \
          "/byphone <phone> - Filter orders by client\n" \
          "/listshipments - View all shipments"
    await update.message.reply_text(msg, reply_markup=create_menu_keyboard())

app.add_handler(CommandHandler('help', help_command))

async def receive_contact(update: Update, context: CallbackContext):
    """AUTO-REGISTRATION via Contact button"""
    contact = update.message.contact
    name = f"{contact.first_name} {contact.last_name}" if contact.last_name else contact.first_name
    phone = contact.phone_number
    
    success = register_user(update.message.from_user.id, phone, name)
    
    if success:
        msg = f"**✅ Registration Successful!**\n\n" \
              f"**Name**: {name}\n" \
              f"**Phone**: {phone}\n\n" \
              "Now you can track packages!\n\n" \
              "Just send your tracking number directly.",
              reply_markup=create_menu_keyboard()
        await update.message.reply_text(msg)
    
    else:
        await update.message.reply_text(
            "❌ Registration failed. Please try again or contact admin.",
            reply_markup=create_menu_keyboard()
        )

app.add_handler(MessageHandler(filters.CONTACT, receive_contact))

async def handle_message(update: Update, context: CallbackContext):
    """TRACKING LOOKUP - accepts ALL formats"""
    text = update.message.text.strip()
    
    # Skip short messages, commands, and empty lines
    if len(text) < 6 or text.startswith('/') or not any(c.isdigit() for c in text):
        return
    
    # Check if registered
    if not check_user_registered(update.message.from_user.id):
        await update.message.reply_text(
            "⚠️ **Please register first!**\n\n" \
            "Click **Contact button** below OR type `/register`.",
            reply_markup=create_menu_keyboard()
        )
        return
    
    # Get shipment info (works with letters, numbers, or mixed)
    result = get_shipment_info(text)
    
    if result:
        msg = (f"**📦 Package Found!**\n\n"
               f"**Tracking**: `{result['tracking_number']}`\n"
               f"**Client**: {result['client_name']}\n"
               f"**Status**: {result['status']}\n"
               f"**Last Updated**: {result['updated_at']}")
        await update.message.reply_text(msg, reply_markup=create_menu_keyboard())
    else:
        await update.message.reply_text(
            f"❌ **No record found for**: `{text}`\n\n" \
            "Please double-check the tracking number.\n" \
            "Or ask admin to add this shipment.",
            reply_markup=create_menu_keyboard()
        )

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def add_shipment_cmd(update: Update, context: CallbackContext):
    """Admin-only command to add shipments manually"""
    if int(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ **Only admin users can add shipments!**",
            reply_markup=create_menu_keyboard()
        )
        return
    
    args = update.message.text.split(' ', 4)
    
    if len(args) >= 4:
        tracking = args[1]
        name = args[2]
        phone = args[3]
        status = args[4] if len(args) > 4 else "In Transit"
        
        success = add_shipment(tracking, name, phone, status)
        
        if success:
            await update.message.reply_text(
                f"✅ **Shipment Added Successfully!**\n\n" \
                f"`{tracking}` | {name} | {status}",
                reply_markup=create_menu_keyboard()
            )
        else:
            await update.message.reply_text("❌ Failed to add shipment. Try again.")
    else:
        await update.message.reply_text(
            "Usage: `/addshipment <tracking> <name> <phone> [status]`\n\n" \
            "Example: `/addshipment YT883118 Shakhnoz +992111004488 Done`",
            reply_markup=create_menu_keyboard()
        )

app.add_handler(CommandHandler('addshipment', add_shipment_cmd))

async def list_shipments_cmd(update: Update, context: CallbackContext):
    """Admin command to list all shipments"""
    if int(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ **Only admin users can view shipments!**",
            reply_markup=create_menu_keyboard()
        )
        return
    
    shipments = list_all_shipments(limit=20)
    
    if not shipments:
        await update.message.reply_text(
            "🗄️ Database is empty. Use `/addshipment` to add records.",
            reply_markup=create_menu_keyboard()
        )
        return
    
    msg = "**📋 All Shipments (Top 20):**\n\n"
    for s in shipments:
        msg += f"`{s['tracking_number']}` | {s['client_name']} | {s['status']}\n"
    
    await update.message.reply_text(msg, reply_markup=create_menu_keyboard())

app.add_handler(CommandHandler('listshipments', list_shipments_cmd))

async def byphone_cmd(update: Update, context: CallbackContext):
    """Admin filter shipments by phone number"""
    if int(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ **Only admin users can filter orders!**",
            reply_markup=create_menu_keyboard()
        )
        return
    
    phone = ' '.join(context.args)
    if not phone:
        await update.message.reply_text(
            "Usage: `/byphone +992...`\n\n" \
            "Example: `/byphone +992111004488`",
            reply_markup=create_menu_keyboard()
        )
        return
    
    matches = get_shipments_by_phone(phone)
    
    if not matches:
        await update.message.reply_text(f"❌ No shipments found for: `{phone}`", reply_markup=create_menu_keyboard())
        return
    
    msg = f"**📦 Shipments for** `{phone}`:\n\n"
    for m in matches[:20]:
        msg += f"`{m['tracking_number']}` | {m['status']}\n"
    
    await update.message.reply_text(msg, reply_markup=create_menu_keyboard())

app.add_handler(CommandHandler('byphone', byphone_cmd))

async def error_handler(update, context):
    """Catch all errors gracefully"""
    print(f"Error: {context.error}")

app.add_error_handler(error_handler)

if __name__ == "__main__":
    init_database()
    app.run_polling(allowed_updates=Update.ALL_TYPES)