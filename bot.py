import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from dotenv import load_dotenv
from database import init_database, get_shipment_info, add_shipment_info
import sqlite3

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
    
    # Define START command handler FIRST (before anything else)
    async def start_command(update: Update, context: CallbackContext):
        user_name = update.message.from_user.first_name if update.message.from_user else "User"
        await update.message.reply_text(
            f"👋 Welcome to Muslat Express Bot, {user_name}!\n\n"
            "Use these commands:\n"
            "/track <tracking_number> - Check package status\n"
            "/help - Show available commands\n\n"
            "Send tracking number or phone contact to begin!"
        )
    
    # Add start command handler
    app.add_handler(CommandHandler("start", start_command))
    
    # Add help command handler
    async def help_command(update: Update, context: CallbackContext):
        help_text = (
            "📦 **Muslat Express Tracking Bot Commands**\n\n"
            "💡 **For Users:**\n"
            "/track <number> - Track by shipment number\n"
            "/help - Show this message\n\n"
            "🔧 **For Admins:**\n"
            "/addshipment - Add new shipment manually\n"
            "/listshipments - View all shipments\n"
            "/updateshipment - Update existing shipment status\n\n"
            "**Note**: Only admin users can use the 🔧 commands above."
        )
        await update.message.reply_text(help_text)
    
    app.add_handler(CommandHandler("help", help_command))
    
    # Add contact message handler (for phone verification)
    async def receive_contact(update: Update, context: CallbackContext):
        contact = update.message.contact
        phone_number = contact.phone_number
        
        # Check if contact has name
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
    
    # Phone verification handler
    async def receive_tracking_number(update: Update, context: CallbackContext):
        tracking_number = update.message.text.strip()
        
        # Get stored contact info
        phone_number = context.user_data.get('client_phone', 'Unknown')
        client_name = context.user_data.get('client_name', 'Unknown')
        
        # Store in database
        status = "In Transit"  # Default status
        try:
            result = get_shipment_info(tracking_number, phone_number)
            if result:
                await update.message.reply_text(
                    f"📦 **Package Found!**\n\n"
                    f"Tracking Number: {result['tracking_number']}\n"
                    f"Client: {result['client_name']}\n"
                    f"Status: {result['status']}\n"
                    f"Last Update: {result['updated_at']}"
                )
            else:
                await update.message.reply_text(
                    f"🤔 No record found for tracking: `{tracking_number}`\n\n"
                    f"Would you like to add this shipment? Reply with `/addshipment` as admin."
                )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error checking tracking: {str(e)}")
        
        # Clean up conversation data
        if 'client_phone' in context.user_data:
            del context.user_data['client_phone']
        if 'client_name' in context.user_data:
            del context.user_data['client_name']
        
        return ConversationHandler.END
    
    # Add tracking handler for contact flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("track", track_command)],
        states={
            WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tracking_number)],
        },
        fallbacks=[],
    )
    
    # Add conversation handler
    app.add_handler(conv_handler)
    
    # Simple text handler for quick tracking
    async def quick_track(update: Update, context: CallbackContext):
        text = update.message.text.strip()
        
        # Check if text looks like tracking number (letters + numbers)
        if len(text) >= 6 and any(c.isalpha() for c in text):
            try:
                result = get_shipment_info(text, '')
                if result:
                    await update.message.reply_text(
                        f"📦 **Package Found!**\n\n"
                        f"Tracking: `{result['tracking_number']}`\n"
                        f"Client: {result['client_name']}\n"
                        f"Status: {result['status']}"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ No record found for `{text}`\n\n"
                        f"Try `/track {text}` for more details."
                    )
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error: {str(e)}")
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_track))
    
    # Start polling
    print("✅ Bot is running... Use Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()