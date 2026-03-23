import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from dotenv import load_dotenv
from database import init_database, get_shipment_info, add_shipment_info, list_all_shipments
import re

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "0").split(",")

def main():
    """Run the bot"""
    # Initialize database first
    init_database()
    
    print(f"Bot starting with token: {TOKEN[:20]}...")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # START command handler
    async def start_command(update: Update, context: CallbackContext):
        user_name = update.message.from_user.first_name if update.message.from_user else "User"
        await update.message.reply_text(
            f"👋 Welcome to Muslat Express Bot, {user_name}!\n\n"
            "💡 **How to Track Packages**:\n\n"
            "Method 1: Just send your tracking number directly\n"
            "Example: YT88311855941829\n\n"
            "Method 2: Use /help to see all commands"
        )
    
    app.add_handler(CommandHandler("start", start_command))
    
    # HELP command handler
    async def help_command(update: Update, context: CallbackContext):
        help_text = (
            "📦 **Muslat Express Tracking Bot**\n\n"
            "**For All Users**:\n"
            "/start - Start the bot\n"
            "/help - Show these commands\n"
            "Send any text → Automatically checks if it's tracking number ✅\n\n"
            "**Admin Only Commands**:\n"
            "/addshipment <tracking> <name> <phone>\n"
            "/listshipments - View all shipments\n"
            "/updateshipment <tracking> <new_status>\n\n"
            "**Current User**: Admin access level"
        )
        await update.message.reply_text(help_text)
    
    app.add_handler(CommandHandler("help", help_command))
    
    # Main message handler for tracking
    async def handle_message(update: Update, context: CallbackContext):
        text = update.message.text.strip()
        
        # Skip short texts or messages that are just commands
        if len(text) < 6 or text.startswith("/"):
            return
        
        # Check if text looks like tracking number (has letters + numbers)
        if re.search(r'[A-Za-z]', text) and re.search(r'\d', text):
            result = get_shipment_info(text, '')
            
            if result:
                await update.message.reply_text(
                    f"📦 **Package Found!**\n\n"
                    f"**Tracking Number**: `{result['tracking_number']}`\n"
                    f"**Client Name**: {result['client_name']}\n"
                    f"**Phone**: {result['phone_number']}\n"
                    f"**Status**: {result['status']}\n"
                    f"**Last Updated**: {result['updated_at']}"
                )
            else:
                await update.message.reply_text(
                    f"❌ No record found for `{text}`\n\n"
                    "You can:\n"
                    "1. Double-check the tracking number\n"
                    "2. Ask admin to add this shipment"
                )
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ADMIN COMMANDS below this line
    
    # Add shipment command (Admin only)
    async def add_shipment_cmd(update: Update, context: CallbackContext):
        if int(update.message.from_user.id) not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text("❌ Only admin users can add shipments!")
            return
        
        args = update.message.text.split(' ', 3)
        
        if len(args) >= 4:
            tracking, name, phone, status = args[1], args[2], args[3], 'In Transit'
            
            if len(args) == 5:
                status = args[4]
            
            success = add_shipment_info(tracking, name, phone, status)
            
            if success:
                await update.message.reply_text(f"✅ Shipment added successfully!\n\n`{tracking}` | {name} | {status}")
            else:
                await update.message.reply_text("❌ Failed to add shipment")
        else:
            await update.message.reply_text(
                "Usage: /addshipment <tracking> <name> <phone> [status]\n\n"
                "Example: /addshipment YT123 John Doe +992123456789 In Transit"
            )
    
    app.add_handler(CommandHandler("addshipment", add_shipment_cmd))
    
    # List shipments command (Admin only)
    async def list_shipments_cmd(update: Update, context: CallbackContext):
        if int(update.message.from_user.id) not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text("❌ Only admin users can view all shipments!")
            return
        
        shipments = list_all_shipments()
        
        if not shipments:
            await update.message.reply_text("🗄️ Database is empty. Use `/addshipment` to add records.")
            return
        
        msg = "📋 **All Shipments** (showing first 20):\n\n"
        for s in shipments[:20]:
            msg += f"`{s['tracking_number']}` | {s['client_name']} | {s['status']}\n"
        
        await update.message.reply_text(msg)
    
    app.add_handler(CommandHandler("listshipments", list_shipments_cmd))
    
    # Update shipment command (Admin only)
    async def update_shipment_cmd(update: Update, context: CallbackContext):
        if int(update.message.from_user.id) not in [int(aid) for aid in ADMIN_IDS]:
            await update.message.reply_text("❌ Only admin users can update shipments!")
            return
        
        args = update.message.text.split(' ', 2)
        
        if len(args) >= 3:
            tracking, new_status = args[1], args[2]
            
            conn = sqlite3.connect('muslat.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE shipments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tracking_number = ?
            ''', (new_status, tracking))
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected > 0:
                await update.message.reply_text(f"✅ Status updated!\n\n`{tracking}` → {new_status}")
            else:
                await update.message.reply_text(f"❌ No shipment found with tracking: `{tracking}`")
        else:
            await update.message.reply_text(
                "Usage: /updateshipment <tracking> <new_status>\n\n"
                "Example: /updateshipment YT123 Delivered"
            )
    
    app.add_handler(CommandHandler("updateshipment", update_shipment_cmd))
    
    # Add error handler to prevent crashes
    async def error_handler(update, context):
        print(f"Update {update} caused error: {context.error}")
    
    app.add_error_handler(error_handler)
    
    # Start polling
    print("✅ Bot is running... Send commands or tracking numbers!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()