# bot.py
import logging
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import database as db

# --- CONFIGURATION ---
TOKEN = '8308776708:AAFdYLUCBnlbbxnh9t7gyASpSnJLB5E_AUY'
ADMIN_IDS = [1273176859] 
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- STATES FOR CONVERSATION ---
WAITING_FOR_TRACKING = 1
WAITING_FOR_PHONE_VERIFY = 2

# --- COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 0: Client Registration"""
    user = update.effective_user
    # Check if already registered
    # Note: We rely on phone number for logic, but we need to ask for it if not provided
    
    keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Welcome to Muslat Express, {user.first_name}!\n"
        "To track packages and receive notifications, please register your phone number.",
        reply_markup=reply_markup
    )

async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the phone number contact"""
    contact = update.message.contact
    phone = contact.phone_number
    user_id = contact.user_id
    name = contact.first_name
    
    if db.add_user(user_id, phone, name):
        # Check if they have existing shipments
        shipments = db.get_all_shipments_by_phone(phone)
        await update.message.reply_text("✅ Registration successful!")
        
        if shipments:
            msg = "📦 You have existing shipments:\n"
            for track, status in shipments:
                msg += f"ID: <code>{track}</code> - {status}\n"
            await update.message.reply_text(msg, parse_mode='HTML')
    else:
        await update.message.reply_text("ℹ️ This phone number is already registered.")
    
    # Remove keyboard
    await update.message.reply_text("Use /track to track a package.", reply_markup=ReplyKeyboardMarkup([['/track']], resize_keyboard=True))

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Initiate Tracking"""
    await update.message.reply_text("Please send me the **Tracking Number**:", parse_mode='HTML')
    return WAITING_FOR_TRACKING

async def receive_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive Tracking Number and ask for Phone Verification"""
    tracking = update.message.text.strip()
    context.user_data['tracking'] = tracking
    await update.message.reply_text("Now, please send the **Phone Number** associated with this package:")
    return WAITING_FOR_PHONE_VERIFY

async def receive_verify_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify Phone and Show Status"""
    phone = update.message.text.strip()
    tracking = context.user_data.get('tracking')
    
    result = db.get_shipment(tracking, phone)
    
    if result:
        status, client_name = result
        await update.message.reply_text(
            f"✅ **Found Package**\n"
            f"👤 Name: {client_name}\n"
            f"🔢 Tracking: <code>{tracking}</code>\n"
            f"🚚 Status: <b>{status}</b>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ No package found with these details. Please check the numbers.")
    
    return ConversationHandler.END

async def upload_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1 & 2: Admin Uploads Excel and Bot Notifies"""
    user_id = update.effective_user.id
    
    # Security Check
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not update.message.document:
        await update.message.reply_text("Please send an Excel file (.xlsx).")
        return
    
    # Download File
    file = await update.message.document.get_file()
    file_path = 'uploads.xlsx'
    await file.download_to_drive(file_path) # Note: In v20+ use download_to_drive or custom logic
    
    # Actually, in v20+ we download to a local path
    await file.download_to_custom_file(file_path)

    try:
        df = pd.read_excel(file_path)
        # Expected Columns: 'Tracking', 'Phone', 'Name', 'Status'
        required_cols = ['Tracking', 'Phone', 'Name']
        if not all(col in df.columns for col in required_cols):
            await update.message.reply_text(f"❌ Excel must contain columns: {required_cols}")
            return

        count = 0
        notified = 0
        
        for index, row in df.iterrows():
            tracking = str(row['Tracking'])
            phone = str(row['Phone'])
            name = str(row['Name'])
            status = str(row.get('Status', 'In Transit'))
            
            # Save to DB
            db.add_shipment(tracking, phone, name, status)
            count += 1
            
            # Step 2: Check if user is registered to send Notification
            telegram_id = db.get_user_by_phone(phone)
            if telegram_id:
                try:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=f"🔔 **New Shipment Update**\n"
                             f"Tracking: <code>{tracking}</code>\n"
                             f"Status: <b>{status}</b>",
                        parse_mode='HTML'
                    )
                    notified += 1
                except Exception as e:
                    logging.error(f"Failed to notify {telegram_id}: {e}")

        await update.message.reply_text(f"✅ Processed {count} shipments.\n🔔 Notified {notified} registered clients.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing file: {str(e)}")
    finally:
        import os
        if os.path.exists(file_path):
            os.remove(file_path)

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    from telegram.ext import ConversationHandler
    
    application = Application.builder().token(TOKEN).build()
    
    # Registration Handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    
    # Tracking Conversation Handler
    track_conv = ConversationHandler(
        entry_points=[CommandHandler('track', track_command)],
        states={
            WAITING_FOR_TRACKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tracking)],
            WAITING_FOR_PHONE_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_verify_phone)],
        },
        fallbacks=[],
    )
    application.add_handler(track_conv)
    
    # Admin Upload Handler
    application.add_handler(MessageHandler(filters.Document.ALL, upload_excel))
    
    print("Bot is running...")
    application.run_polling()