import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from dotenv import load_dotenv
from database import (init_database, register_user, get_user_info, 
                      check_user_registered, add_shipment_info, list_all_shipments)
import re

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "0").split(",")

REGISTERING = 1

def main():
    """Run the bot"""
    # Initialize database first
    init_database()
    
    print(f"Bot starting... Token prefix: {TOKEN[:20]}...")
    
    app = Application.builder().token(TOKEN).build()
    
    def create_menu_keyboard():
        keyboard = [
            [KeyboardButton("/start"), KeyboardButton("/help")],
            [KeyboardButton("/track"), KeyboardButton("/register")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # ===== START COMMAND =====
    async def start_command(update: Update, context: CallbackContext):
        await update.message.reply_text(
            f"👋 Welcome to Muslat Express Bot!\n\n"
            "💡 **How to Use This Bot**:\n"
            "1️⃣ Register with your phone number first\n"
            "2️⃣ Send tracking numbers to check status\n\n"
            "Use the buttons below to navigate!",
            reply_markup=create_menu_keyboard()
        )
    
    app.add_handler(CommandHandler("start", start_command))
    
    # ===== HELP COMMAND =====
    async def help_command(update: Update, context: CallbackContext):
        help_text = (
            "📦 **Muslat Express Tracking Bot Commands**\n\n"
            "**For All Users**:\n"
            "/start - Start the bot\n"
            "/help - Show these commands\n"
            "/track <number> - Track package status\n"
            "/register +992... - Register with phone number\n\n"
            "**Admin Only Commands**:\n"
            "/addshipment <tracking> <name> <phone> [status]\n"
            "/listshipments - View all shipments"
        )
        await update.message.reply_text(help_text, reply_markup=create_menu_keyboard())
    
    app.add_handler(CommandHandler("help", help_command))
    
    # ===== REGISTER USER =====
    async def register_command(update: Update, context: CallbackContext):
        if check_user_registered(update.message.from_user.id):
            user_info = get_user_info(update.message.from_user.id)
            await update.message.reply_text(
                f"✅ You're already registered!\n\n"
                f"Your phone: `{user_info['phone_number']}`\n\n"
                "If you changed phones, just register again.",
                reply_markup=create_menu_keyboard()
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "📱 **Please register with your phone number**\n\n"
            "Send your full phone number:\n"
            "Example: +992111004488\n\n"
            "Or click Contact button below:",
            reply_markup=create_menu_keyboard()
        )
        return REGISTERING
    
    app.add_handler(CommandHandler("register", register_command))
    
    # ===== CONTACT HANDLER FOR REGISTRATION =====
    async def receive_contact(update: Update, context: CallbackContext):
        contact = update.message.contact
        phone_number = contact.phone_number
        client_name = contact.first_name
        last_name = contact.last_name
        if last_name:
            client_name = f"{client_name} {last_name}"
        
        success = register_user(update.message.from_user.id, phone_number, client_name)
        
        if success:
            await update.message.reply_text(
                f"✅ **Registration Successful!**\n\n"
                f"Name: {client_name}\n"
                f"Phone: {phone_number}\n\n"
                "Now you can track packages! Send a tracking number.\n\n"
                "Use /help to see all commands.",
                reply_markup=create_menu_keyboard()
            )
        else:
            await update.message.reply_text("❌ Registration failed. Please try again.")
        
        return ConversationHandler.END
    
    app.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    
    # ===== REGISTRATION VIA TEXT PHONE NUMBER =====
    async def receive_phone_number(update: Update, context: CallbackContext):
        text = update.message.text.strip()
        
        if text.startswith('+') and len(text.replace('+', '')) >= 9:
            user_name = update.message.from_user.first_name
            last_name = update.message.from_user.last_name
            
            success = register_user(
                update.message.from_user.id,
                text,
                user_name + (' ' + last_name if last_name else '')
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ **Registration Successful!**\n\n"
                    f"Name: {user_name + (' ' + last_name if last_name else '')}\n"
                    f"Phone: {text}\n\n"
                    "Now you can track packages! Send a tracking number.\n\n"
                    "Use /help to see all commands.",
                    reply_markup=create_menu_keyboard()
                )
                # CRITICAL FIX: End conversation so it doesn't ask for phone again!
                return ConversationHandler.END
            else:
                await update.message.reply_text("❌ Phone number already registered. Try another one.")
                return ConversationHandler.END
        else:
            await update.message.reply_text(
                "⚠️ That doesn't look like a phone number.\n\n"
                "Please send:\n"
                "1. Click the Contact button, OR\n"
                "2. Type your full phone number starting with + (e.g., +992111004488)"
            )
            # Stay in conversation mode for retries
            return REGISTERING
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone_number))
    
    # ===== TRACK COMMAND =====
    async def track_command(update: Update, context: CallbackContext):
        if not check_user_registered(update.message.from_user.id):
            await update.message.reply_text(
                "⚠️ You need to register first!\n\n"
                "Use `/register +992...` or click the Contact button.",
                reply_markup=create_menu_keyboard()
            )
            return
        
        await update.message.reply_text(
            "Enter your tracking number:",
            reply_markup=create_menu_keyboard()
        )
    
    app.add_handler(CommandHandler("track", track_command))
    
    # ===== MAIN MESSAGE HANDLER (Tracking Lookup) =====
    async def handle_message(update: Update, context: CallbackContext):
        text = update.message.text.strip()
        
        # Skip short messages
        if len(text) < 6:
            return
        
        # Skip commands
        if text.startswith("/"):
            return
        
        # FIXED: Accept PURE NUMERIC tracking (like 9813247828669)
        if re.search(r'\d', text):
            if not check_user_registered(update.message.from_user.id):
                await update.message.reply_text(
                    "⚠️ You need to register first!\n\n"
                    "Use `/register +992...` to verify your phone number.",
                    reply_markup=create_menu_keyboard()
                )
                return
            
            user_info = get_user_info(update.message.from_user.id)
            result = get_shipment_info(text, user_info['phone_number'])
            
            if result:
                await update.message.reply_text(
                    f"📦 **Package Found!**\n\n"
                    f"**Tracking Number**: `{result['tracking_number']}`\n"
                    f"**Client Name**: {result['client_name']}\n"
                    f"**Phone**: {result['phone_number']}\n"
                    f"**Status**: {result['status']}\n"
                    f"**Last Updated**: {result['updated_at']}",
                    reply_markup=create_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ No record found for `{text}`\n\n"
                    "Please double-check the tracking number.\n"
                    "Or ask admin to add this shipment.",
                    reply_markup=create_menu_keyboard()
                )
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ===== ADMIN: ADD SHIPMENT =====
    async def add_shipment_cmd(update: Update, context: CallbackContext):
        if int(update.message.from_user.id) not in [int(aid) for aid in ADMIN_IDS]:
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
            
            success = add_shipment_info(tracking, name, phone, status)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Shipment Added Successfully!**\n\n"
                    f"`{tracking}` | {name} | {status}",
                    reply_markup=create_menu_keyboard()
                )
            else:
                await update.message.reply_text("❌ Failed to add shipment")
        else:
            await update.message.reply_text(
                "Usage: `/addshipment <tracking> <name> <phone> [status]`\n\n"
                "Example: `/addshipment YT123 John Doe +992123456789 In Transit`"
            )
    
    app.add_handler(CommandHandler("addshipment", add_shipment_cmd))
    
    # ===== ADMIN: LIST SHIPMENTS =====
    async def list_shipments_cmd(update: Update, context: CallbackContext):
        if int(update.message.from_user.id) not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text(
                "❌ **Only admin users can view shipments!**",
                reply_markup=create_menu_keyboard()
            )
            return
        
        shipments = list_all_shipments()
        
        if not shipments:
            await update.message.reply_text(
                "🗄️ Database is empty. Use `/addshipment` to add records.",
                reply_markup=create_menu_keyboard()
            )
            return
        
        msg = "📋 **All Shipments** (First 20):\n\n"
        for s in shipments[:20]:
            msg += f"`{s['tracking_number']}` | {s['client_name']} | {s['status']}\n"
        
        await update.message.reply_text(msg, reply_markup=create_menu_keyboard())
    
    app.add_handler(CommandHandler("listshipments", list_shipments_cmd))
    
    # ===== ERROR HANDLER =====
    async def error_handler(update, context):
        print(f"Error: {context.error}")
    
    app.add_error_handler(error_handler)
    
    print("✅ Bot is running! Send tracking numbers or use /help")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()