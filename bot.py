#!/usr/bin/env python3
"""
Shopify Card Checker Bot - 100% Working
Fixed Output + User Management
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import *
from checker import ShopifyChecker
from database import Database

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize
db = Database()
checker = ShopifyChecker()

# Add initial admins
for admin_id in INITIAL_ADMINS:
    db.add_admin(admin_id)

class ShopifyCardBot:
    """Main Bot Class - 100% Working"""
    
    def __init__(self):
        self.user_settings: Dict[int, Dict] = {}
    
    def get_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                "language": "bn",
                "country": "US"
            }
        return self.user_settings[user_id]
    
    def safe_edit(self, msg, text):
        """Safely edit message"""
        try:
            return msg.edit_text(text[:4000])
        except:
            pass
    
    def safe_reply(self, update, text):
        """Safely reply to message"""
        try:
            return update.message.reply_text(text[:4000])
        except:
            try:
                return update.message.reply_text(text[:4000].replace('`', '').replace('*', '').replace('_', '').replace('[', '').replace(']', ''))
            except:
                return update.message.reply_text("✅ Done! Check results above.")
    
    # ==================== START ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        user = update.effective_user
        user_id = user.id
        
        # Check blocked
        if db.is_blocked(user_id):
            await update.message.reply_text(
                "⛔ Access Blocked!\n\n"
                f"Contact: {OWNER_USERNAME}"
            )
            return
        
        # Check pending
        if db.is_pending(user_id):
            await update.message.reply_text(
                "⏳ Approval Pending...\n\n"
                "Your request is being reviewed.\n"
                f"Contact: {OWNER_USERNAME}"
            )
            return
        
        # New user
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        # Show welcome
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        stats = checker.stats
        total = stats["total"]
        approved = stats["approved"]
        declined = stats["declined"]
        rate = (approved / total * 100) if total > 0 else 0
        
        welcome = f"""
🌟 Shopify Card Checker Bot 🌟

👋 Welcome {user.first_name}!

Features:
• 100% Real Shopify API Check
• Gateway Detection
• BIN, Card Type, Country
• 10,000+ Card Support

Settings:
• Language: {"Bangla" if lang == "bn" else "English"}
• Country: {country_name}

Stats:
• Total: {total}
• Approved: {approved}
• Declined: {declined}
• Success Rate: {rate:.1f}%
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🌐 Country: " + country, callback_data="change_country"),
             InlineKeyboardButton("🗣 Language", callback_data="change_lang")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])
        
        await update.message.reply_text(welcome, reply_markup=keyboard)
    
    # ==================== ACCESS REQUEST ====================
    async def send_access_request(self, update: Update):
        """Send access request"""
        user = update.effective_user
        user_id = user.id
        
        db.add_pending(user_id, {
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or ""
        })
        
        await update.message.reply_text(
            "📩 Access Request Sent!\n\n"
            "Your request has been sent to admin.\n"
            "Please wait for approval.\n\n"
            f"Contact: {OWNER_USERNAME}"
        )
        
        # Notify admins
        for admin_id_str in db.users["admins"]:
            try:
                admin_id = int(admin_id_str)
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")],
                    [InlineKeyboardButton("🚫 Block", callback_data=f"block_{user_id}")]
                ])
                
                await update.get_bot().send_message(
                    chat_id=admin_id,
                    text=f"🔔 New Access Request\n\n"
                         f"User: {user.first_name}\n"
                         f"Username: @{user.username or 'N/A'}\n"
                         f"ID: {user_id}",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Admin notify error: {e}")
    
    # ==================== BUTTON HANDLER ====================
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Button handler"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # Admin actions
        if data.startswith("approve_"):
            target_id = int(data.replace("approve_", ""))
            if db.is_admin(user_id):
                db.approve_user(target_id, user_id)
                await query.edit_message_text(f"✅ User {target_id} Approved!")
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text="🎉 Your access has been approved!\nSend /start to use the bot."
                    )
                except:
                    pass
            return
        
        if data.startswith("reject_"):
            target_id = int(data.replace("reject_", ""))
            if db.is_admin(user_id):
                db.reject_user(target_id)
                await query.edit_message_text(f"❌ User {target_id} Rejected!")
            return
        
        if data.startswith("block_"):
            target_id = int(data.replace("block_", ""))
            if db.is_admin(user_id):
                db.block_user(target_id)
                await query.edit_message_text(f"🚫 User {target_id} Blocked!")
            return
        
        # Check access
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await query.edit_message_text("⛔ Access Denied! Send /start first.")
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        # Check Card
        if data == "check_card":
            msg = f"""
📝 Enter Card Details:

Format: 4111111111111111|12|2026|123
Separators: | : , ; space

• Single or multiple cards
• Use file for 100+ cards

Country: {country_name}
Time per card: {CHECK_DELAY}s

Send cards now ⬇️
            """
            
            await query.edit_message_text(
                msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
        
        # Upload File
        elif data == "upload_file":
            msg = """
📤 File Upload Guide:

• .txt files only
• 1 card per line
• Max 10,000 cards
• Format: number|mm|yyyy|cvv

Upload .txt file now 📎
            """
            
            await query.edit_message_text(
                msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
        
        # Stats
        elif data == "stats":
            s = checker.stats
            total = s["total"]
            approved = s["approved"]
            declined = s["declined"]
            rate = (approved / total * 100) if total > 0 else 0
            
            stats_msg = f"""
📊 Checking Stats

Total: {total}
Approved: {approved}
Declined: {declined}
Success: {rate:.1f}%

Live: {s['live']}
Die: {s['die']}
Gateway: Shopify API
Delay: {CHECK_DELAY}s/card
            """
            
            await query.edit_message_text(
                stats_msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh", callback_data="stats")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
        
        # Change Country
        elif data == "change_country":
            keyboard = []
            row = []
            for code, info in COUNTRIES.items():
                row.append(InlineKeyboardButton(info["name"], callback_data=f"country_{code}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
            
            await query.edit_message_text(
                "🌐 Select Country:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data.startswith("country_"):
            country = data.replace("country_", "")
            settings["country"] = country
            await query.answer(f"Country: {COUNTRIES.get(country, {}).get('name', country)}")
            await self.back_to_start(query)
        
        # Change Language
        elif data == "change_lang":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🇧🇩 Bangla", callback_data="lang_bn"),
                 InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text("🗣 Select Language:", reply_markup=keyboard)
        
        elif data.startswith("lang_"):
            lang = data.replace("lang_", "")
            settings["language"] = lang
            await query.answer(f"Language: {'Bangla' if lang == 'bn' else 'English'}")
            await self.back_to_start(query)
        
        # Help
        elif data == "help":
            help_msg = f"""
ℹ️ Help & Info

Card Format:
4111111111111111|12|2026|123

Results:
✅ APPROVED = Card works (Live)
❌ DECLINED = Card rejected (Die)
⚠️ UNKNOWN = Try again

File: .txt, 10000 cards
Gateway: Shopify, Stripe
Speed: {CHECK_DELAY}s/card

Support: {OWNER_USERNAME}
Bot: {BOT_USERNAME}
            """
            
            await query.edit_message_text(
                help_msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
        
        # Back
        elif data == "back_to_start":
            await self.back_to_start(query)
    
    # ==================== BACK TO START ====================
    async def back_to_start(self, query):
        """Back to main menu"""
        user_id = query.from_user.id
        settings = self.get_settings(user_id)
        country = settings["country"]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🌐 Country: " + country, callback_data="change_country"),
             InlineKeyboardButton("🗣 Language", callback_data="change_lang")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])
        
        await query.edit_message_text(
            "🔄 Main Menu\nSelect option below:",
            reply_markup=keyboard
        )
    
    # ==================== HANDLE CARD INPUT (FIXED) ====================
    async def handle_card_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle card input - 100% WORKING OUTPUT"""
        user_id = update.effective_user.id
        
        # Check access
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Access Blocked!")
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            if db.is_pending(user_id):
                await update.message.reply_text("⏳ Approval Pending...")
            else:
                await self.send_access_request(update)
            return
        
        text = update.message.text.strip()
        cards = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not cards:
            await update.message.reply_text("❌ No cards found!")
            return
        
        if len(cards) > 100:
            await update.message.reply_text("⚠️ Use .txt file for 100+ cards!")
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        # Processing message
        processing_msg = await update.message.reply_text(
            f"⏳ Checking {len(cards)} cards...\n"
            f"Country: {country_name}\n"
            f"Time: ~{len(cards) * CHECK_DELAY}s\n\n"
            "Please wait..."
        )
        
        try:
            # Process cards
            results = await checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.progress_update(
                    processing_msg, c, t, card
                )
            )
            
            # Delete processing message
            try:
                await processing_msg.delete()
            except:
                pass
            
            # Build output text
            output = self.build_output(results, lang)
            
            # Send results
            if len(output) > 4000:
                # Save to file
                filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(output)
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"✅ Check Complete!\n"
                               f"Total: {len(results)}\n"
                               f"Live: {checker.stats['live']} | Die: {checker.stats['die']}"
                    )
                os.remove(filename)
            else:
                # Send as message
                await update.message.reply_text(output)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            try:
                await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
            except:
                await update.message.reply_text("❌ Error occurred. Try again.")
    
    # ==================== PROGRESS UPDATE ====================
    async def progress_update(self, msg, current: int, total: int, card: str):
        """Update progress"""
        if current % 3 == 0 or current == total:
            percent = int(current / total * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            
            text = (
                f"⏳ Checking: {current}/{total}\n"
                f"[{bar}] {percent}%\n"
                f"Card: {card}\n"
                f"Shopify API real check..."
            )
            
            try:
                await msg.edit_text(text)
            except:
                pass
    
    # ==================== BUILD OUTPUT (FIXED) ====================
    def build_output(self, results: list, lang: str) -> str:
        """Build output text - 100% working"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = len(results)
        
        approved = [r for r in results if r["status"] == "APPROVED"]
        declined = [r for r in results if r["status"] == "DECLINED"]
        unknown = [r for r in results if r["status"] == "UNKNOWN"]
        invalid = [r for r in results if r["status"] == "INVALID"]
        errors = [r for r in results if r["status"] == "ERROR"]
        
        output = "═══════════════════════════════════\n"
        output += "  SHOPIFY CARD CHECK RESULTS\n"
        output += "═══════════════════════════════════\n\n"
        output += f"Date: {now}\n"
        output += f"Total Cards: {total}\n"
        output += f"Approved: {len(approved)}\n"
        output += f"Declined: {len(declined)}\n"
        if unknown:
            output += f"Unknown: {len(unknown)}\n"
        if invalid:
            output += f"Invalid: {len(invalid)}\n"
        if errors:
            output += f"Errors: {len(errors)}\n"
        
        output += "\n" + "=" * 50 + "\n"
        
        # Show each card result
        for i, r in enumerate(results, 1):
            status_emoji = "✅" if r["status"] == "APPROVED" else "❌" if r["status"] == "DECLINED" else "⚠️"
            output += f"\n{i}. {status_emoji} {r['card']}\n"
            output += f"   BIN: {r.get('bin', 'N/A')}\n"
            output += f"   Type: {r.get('card_type', 'Unknown')}\n"
            output += f"   Gateway: {r.get('gateway', 'N/A')}\n"
            output += f"   Country: {r.get('country', 'US')}\n"
            output += f"   Time: {r.get('response_time', 'N/A')}\n"
            output += f"   Result: {r.get('message', 'N/A')}\n"
        
        output += f"""
{'=' * 50}
Summary: {len(approved)} Live | {len(declined)} Die | {total} Total
Bot: {BOT_USERNAME}
Owner: {OWNER_USERNAME}
Time: {now}
"""
        
        return output
    
    # ==================== HANDLE FILE ====================
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file upload"""
        user_id = update.effective_user.id
        
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Access Blocked!")
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            if db.is_pending(user_id):
                await update.message.reply_text("⏳ Approval Pending...")
            else:
                await self.send_access_request(update)
            return
        
        document = update.message.document
        
        if not document.file_name.endswith('.txt'):
            await update.message.reply_text("❌ Only .txt files allowed!")
            return
        
        if document.file_size > 5 * 1024 * 1024:
            await update.message.reply_text("❌ File too large (max 5MB)!")
            return
        
        settings = self.get_settings(user_id)
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        progress_msg = await update.message.reply_text("📥 Downloading file...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            content = file_bytes.decode('utf-8')
            
            cards = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not cards:
                await progress_msg.edit_text("❌ No cards found in file!")
                return
            
            if len(cards) > MAX_FILE_CARDS:
                cards = cards[:MAX_FILE_CARDS]
            
            await progress_msg.edit_text(
                f"⏳ Checking {len(cards)} cards...\n"
                f"Country: {country_name}\n"
                f"Time: ~{len(cards) * CHECK_DELAY // 60} min\n\n"
                "Please wait..."
            )
            
            results = await checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.progress_update(
                    progress_msg, c, t, card
                )
            )
            
            output = self.build_output(results, settings["language"])
            
            filename = f"shopify_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(output)
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"✅ Complete! {len(results)} cards\n"
                           f"Live: {checker.stats['live']} | Die: {checker.stats['die']}"
                )
            
            os.remove(filename)
            await progress_msg.delete()
        
        except Exception as e:
            logger.error(f"File error: {e}")
            try:
                await progress_msg.edit_text(f"❌ Error: {str(e)[:200]}")
            except:
                await update.message.reply_text("❌ Error processing file.")
    
    # ==================== ADMIN COMMANDS ====================
    async def admin_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin commands"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            return
        
        text = update.message.text.strip()
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        
        if cmd == "/users":
            pending = db.get_pending_users()
            approved = db.get_approved_users()
            
            msg = "📊 User Management\n\n"
            msg += f"Pending ({len(pending)}):\n"
            for u in pending:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - {u['id']}\n"
            
            msg += f"\nApproved ({len(approved)}):\n"
            for u in approved[:20]:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - {u['id']}\n"
            
            if len(approved) > 20:
                msg += f"... and {len(approved) - 20} more\n"
            
            await update.message.reply_text(msg)
        
        elif cmd == "/approve" and len(parts) > 1:
            try:
                target = int(parts[1])
                db.approve_user(target, user_id)
                await update.message.reply_text(f"✅ User {target} Approved!")
                try:
                    await context.bot.send_message(
                        chat_id=target,
                        text="🎉 Your access has been approved!\nSend /start to use the bot."
                    )
                except:
                    pass
            except:
                await update.message.reply_text("❌ Invalid ID!")
        
        elif cmd == "/block" and len(parts) > 1:
            try:
                target = int(parts[1])
                db.block_user(target)
                await update.message.reply_text(f"🚫 User {target} Blocked!")
            except:
                await update.message.reply_text("❌ Invalid ID!")
        
        elif cmd == "/unblock" and len(parts) > 1:
            try:
                target = int(parts[1])
                db.unblock_user(target)
                await update.message.reply_text(f"✅ User {target} Unblocked!")
            except:
                await update.message.reply_text("❌ Invalid ID!")
    
    # ==================== RUN ====================
    def run(self):
        """Run bot"""
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ BOT_TOKEN not configured!")
            sys.exit(1)
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("users", self.admin_commands))
        app.add_handler(CommandHandler("approve", self.admin_commands))
        app.add_handler(CommandHandler("block", self.admin_commands))
        app.add_handler(CommandHandler("unblock", self.admin_commands))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_card_input))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        
        print("""
═══════════════════════════════════
  Shopify Card Checker Bot
  100% Working Version
  User Management Active
  Railway Ready
═══════════════════════════════════
        """)
        
        print("✅ Bot is running...")
        
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

# ==================== MAIN ====================
if __name__ == "__main__":
    bot = ShopifyCardBot()
    bot.run()
