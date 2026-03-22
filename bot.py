import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from dotenv import load_dotenv
from database import init_database, get_shipment_info, add_shipment_info, list_all_shipments
import re

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "0").split(",")

# Conversation states
WAITING_FOR_PHONE = 1

def main():
    """Run the bot"""
    # Initialize database first
    init_database()
    
    print(f"Bot starting with token: {TOKEN[:20]}...")
    
    # Create application with the token
    app = Application.builder().token(TOKEN).build()
    
    # Define START command handler FIRST
    async def start_command(update: Update, context: CallbackContext):
        user_name = update.message.from_user.first_name if update.message.from_user else "User"
        await update.message.reply_text(
            f"👋 Welcome to Muslat Express Bot, {user_name}!\n\n"
            "Use these commands:\n"
            "/track <number> - Check package status\n"
            "/help - Show available commands\n\n"
            "Send tracking number or contact to begin!"
        )
    
    app.add_handler(CommandHandler("start", start_command))
    
    # Add help command handler
    async def help_command(update: Update, context: CallbackContext):
        help_text = (
            "📦 **Muslat Express Tracking Bot Commands**\n\n"
            "💡 **For Users:**\n"
            "/track <number> - Track by shipment number\n"
            "/help - Show this message\n\n"
            "🔧 **For Admins Only:**\n"
            "/addshipment - Add new shipment manually\n"
            "/listshipments - View all shipments\n"
            "/updateshipment - Update shipment status\n"
        )
        await update.message.reply_text(help_text)
    
    app.add_handler(CommandHandler("help", help_command))
    
    # Start track conversation
    async def track_command(update: Update, context: CallbackContext):
        if update.message.from_user.id not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text("⚠️ Please enter tracking number:")
            return WAITING_FOR_TRACKING
        
        await update.message.reply_text("📋 Send tracking number, client name, and phone number:")
        return WAITING_FOR_DATA
    
    app.add_handler(CommandHandler("track", track_command))
    
    # Phone verification handler
    async def receive_contact(update: Update, context: CallbackContext):
        contact = update.message.contact
        phone_number = contact.phone_number
        
        client_name = contact.first_name
        last_name = contact.last_name
        if last_name:
            client_name = f"{client_name} {last_name}"
        
        await update.message.reply_text(
            f"✅ Contact received: {client_name}\nPhone: {phone_number}\n\n"
            "Enter your tracking number now..."
        )
        
        context.user_data['client_phone'] = phone_number
        context.user_data['client_name'] = client_name
        
        return WAITING_FOR_PHONE
    
    app.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    
    # Receive phone then tracking
    async def receive_tracking_number(update: Update, context: CallbackContext):
        tracking_number = update.message.text.strip()
        phone_number = context.user_data.get('client_phone', 'Unknown')
        client_name = context.user_data.get('client_name', 'Unknown')
        
        success = add_shipment_info(tracking_number, client_name, phone_number, "In Transit")
        
        if success:
            await update.message.reply_text(f"✅ Shipment added: `{tracking_number}`")
        else:
            await update.message.reply_text("❌ Failed to add shipment")
        
        # Cleanup
        if 'client_phone' in context.user_data:
            del context.user_data['client_phone']
        if 'client_name' in context.user_data:
            del context.user_data['client_name']
        
        return ConversationHandler.END
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tracking_number))
    
    # Quick text tracking handler
    async def quick_track(update: Update, context: CallbackContext):
        text = update.message.text.strip()
        
        # Check if text looks like tracking number (letters + numbers)
        if len(text) >= 6 and re.search(r'[A-Za-z]', text):
            result = get_shipment_info(text, '')
            
            if result:
                await update.message.reply_text(
                    f"📦 **Package Found!**\n\n"
                    f"Tracking Number: `{result['tracking_number']}`\n"
                    f"Client: {result['client_name']}\n"
                    f"Status: {result['status']}\n"
                    f"Last Update: {result['updated_at']}"
                )
            else:
                await update.message.reply_text(
                    f"❌ No record found for `{text}`\n\n"
                    f"Try `/track {text}` or send tracking number again."
                )
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_track))
    
    # Add admin shipment handlers
    async def add_shipment_cmd(update: Update, context: CallbackContext):
        if update.message.from_user.id not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text("❌ Only admin users can add shipments")
            return ConversationHandler.END
        
        await update.message.reply_text(
            "Please provide:\n"
            "1. Tracking number\n"
            "2. Client name\n"
            "3. Phone number"
        )
        return WAITING_FOR_ADMIN_DATA
    
    app.add_handler(CommandHandler("addshipment", add_shipment_cmd))
    
    async def process_admin_shiptext(update: Update, context: CallbackContext):
        data_parts = update.message.text.split(' ', 3)
        
        if len(data_parts) == 4:
            tracking, name, phone, status = data_parts
            
            success = add_shipment_info(tracking, name, phone, status)
            
            if success:
                await update.message.reply_text(f"✅ Shipment added: `{tracking}`")
            else:
                await update.message.reply_text("❌ Failed to add shipment")
            
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "Format: /addshipment <tracking> <name> <phone>\n"
                "Example: /addshipment YT123 John Doe +992123456789"
            )
            return ConversationHandler.END
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_admin_shiptext))
    
    # List shipments
    async def list_shipments(update: Update, context: CallbackContext):
        if update.message.from_user.id not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text("❌ Only admin users can view list")
            return ConversationHandler.END
        
        shipments = list_all_shipments()
        
        if not shipments:
            await update.message.reply_text("No shipments found in database.")
            return ConversationHandler.END
        
        msg = "📋 **All Shipments:**\n\n"
        for s in shipments[:20]:  # Limit to 20 for readability
            msg += f"`{s['tracking_number']}` | {s['client_name']} | {s['status']}\n"
        
        await update.message.reply_text(msg)
        return ConversationHandler.END
    
    app.add_handler(CommandHandler("listshipments", list_shipments))
    
    # Start polling
    print("✅ Bot is running... Use Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()