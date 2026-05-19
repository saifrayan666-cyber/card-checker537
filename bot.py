#!/usr/bin/env python3
"""
Shopify Card Checker Bot - Multi Gateway
Live Results + All Buttons Active
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

from config import *
from checker import ShopifyChecker
from database import Database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

db = Database()
checker = ShopifyChecker()

for admin_id in INITIAL_ADMINS:
    db.add_admin(admin_id)

class ShopifyCardBot:
    """Main Bot - All Features"""
    
    def __init__(self):
        self.user_settings: Dict[int, Dict] = {}
        self.live_results: Dict[int, list] = {}
    
    def get_settings(self, user_id: int) -> Dict:
        """Get user settings"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                "language": "bn",
                "country": "US",
                "gateway": "stripe"
            }
        return self.user_settings[user_id]
    
    # ==================== START ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start"""
        user = update.effective_user
        user_id = user.id
        
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Access Blocked!")
            return
        
        if db.is_pending(user_id):
            await update.message.reply_text("⏳ Approval Pending...")
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        gateway = settings["gateway"]
        gw_name = GATEWAYS[gateway]["name"]
        
        stats = checker.stats
        
        welcome = f"""
🌟 Shopify Card Checker Bot 🌟

👋 Welcome {user.first_name}!

⚡ Multi-Gateway Support
✅ Real-time Live Results
📊 Detailed Card Info

Settings:
• Country: {COUNTRIES[country]['name']}
• Gateway: {gw_name}

Stats:
• Total: {stats['total']}
• Approved: {stats['approved']}
• Declined: {stats['declined']}
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🌐 Country: " + country, callback_data="change_country"),
             InlineKeyboardButton("🚀 Gateway: " + gateway.upper(), callback_data="change_gateway")],
            [InlineKeyboardButton("🗣 Language", callback_data="change_lang"),
             InlineKeyboardButton("ℹ️ Help", callback_data="help")]
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
            "📩 Access Request Sent!\nPlease wait for approval."
        )
        
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
                    text=f"🔔 New Access Request\nUser: {user.first_name}\nID: {user_id}",
                    reply_markup=keyboard
                )
            except:
                pass
    
    # ==================== BUTTON HANDLER ====================
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Button handler - ALL BUTTONS ACTIVE"""
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
                        text="🎉 Approved! Send /start"
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
            await query.edit_message_text("⛔ Access Denied!")
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        gateway = settings["gateway"]
        
        # Check Card - ALWAYS ACTIVE
        if data == "check_card":
            msg = f"""
📝 Enter Card Details:

Format: 4111111111111111|12|2026|123

Gateway: {GATEWAYS[gateway]['name']}
Country: {COUNTRIES[country]['name']}

Send cards now ⬇️
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(msg, reply_markup=keyboard)
        
        # Upload File - ALWAYS ACTIVE
        elif data == "upload_file":
            msg = """
📤 Upload .txt File

• 1 card per line
• Max 10,000 cards
• Format: number|mm|yyyy|cvv

Upload now 📎
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(msg, reply_markup=keyboard)
        
        # Stats - ALWAYS ACTIVE
        elif data == "stats":
            s = checker.stats
            stats_msg = f"""
📊 Stats

Total: {s['total']}
Approved: {s['approved']}
Declined: {s['declined']}
Live: {s['live']}
Die: {s['die']}

Gateway: {GATEWAYS[gateway]['name']}
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(stats_msg, reply_markup=keyboard)
        
        # Change Country - ALWAYS ACTIVE
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
            
            await query.edit_message_text("🌐 Select Country:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("country_"):
            country = data.replace("country_", "")
            settings["country"] = country
            await query.answer(f"Country: {COUNTRIES[country]['name']}")
            await self.back_to_start(query)
        
        # Change Gateway - NEW
        elif data == "change_gateway":
            keyboard = []
            for gw_id, gw_info in GATEWAYS.items():
                keyboard.append([
                    InlineKeyboardButton(
                        f"{gw_info['emoji']} {gw_info['name']}",
                        callback_data=f"gateway_{gw_id}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
            
            await query.edit_message_text("🚀 Select Gateway:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("gateway_"):
            gateway = data.replace("gateway_", "")
            settings["gateway"] = gateway
            await query.answer(f"Gateway: {GATEWAYS[gateway]['name']}")
            await self.back_to_start(query)
        
        # Change Language - ALWAYS ACTIVE
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
        
        # Help - ALWAYS ACTIVE
        elif data == "help":
            help_msg = f"""
ℹ️ Help

Gateways:
• Stripe - Shopify payment
• Braintree - PayPal payment
• BIN Lookup - Card info

Format: 4111111111111111|12|2026|123

Support: {OWNER_USERNAME}
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(help_msg, reply_markup=keyboard)
        
        # Back - ALWAYS ACTIVE
        elif data == "back_to_start":
            await self.back_to_start(query)
    
    # ==================== BACK TO START ====================
    async def back_to_start(self, query):
        """Back to main menu"""
        user_id = query.from_user.id
        settings = self.get_settings(user_id)
        country = settings["country"]
        gateway = settings["gateway"]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🌐 Country: " + country, callback_data="change_country"),
             InlineKeyboardButton("🚀 Gateway: " + gateway.upper(), callback_data="change_gateway")],
            [InlineKeyboardButton("🗣 Language", callback_data="change_lang"),
             InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])
        
        await query.edit_message_text("🔄 Main Menu", reply_markup=keyboard)
    
    # ==================== HANDLE CARD INPUT ====================
    async def handle_card_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle card input - Live results"""
        user_id = update.effective_user.id
        
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Access Blocked!")
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        text = update.message.text.strip()
        cards = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not cards:
            await update.message.reply_text("❌ No cards found!")
            return
        
        settings = self.get_settings(user_id)
        gateway = settings["gateway"]
        gw_name = GATEWAYS[gateway]["name"]
        
        processing_msg = await update.message.reply_text(
            f"⏳ Checking {len(cards)} cards...\nGateway: {gw_name}"
        )
        
        # Live results list
        live_results = []
        
        async def on_live_result(result, current, total):
            """Callback for approved cards"""
            live_results.append(result)
            live_msg = (
                f"✅ LIVE CARD FOUND! ({current}/{total})\n\n"
                f"Card: {result['card']}\n"
                f"BIN: {result['bin']}\n"
                f"Type: {result['card_type']}\n"
                f"Gateway: {result['gateway']}\n"
                f"Time: {result['response_time']}\n"
            )
            if result.get('bin_info'):
                bi = result['bin_info']
                live_msg += (
                    f"Bank: {bi.get('bank', 'N/A')}\n"
                    f"Country: {bi.get('country', 'N/A')}\n"
                    f"Brand: {bi.get('brand', 'N/A')}\n"
                    f"Type: {bi.get('type', 'N/A')}"
                )
            await update.message.reply_text(live_msg)
        
        try:
            results = await checker.check_batch(
                cards,
                gateway=gateway,
                country=settings["country"],
                progress_callback=lambda c, t, card: self.progress_update(processing_msg, c, t, card),
                live_result_callback=on_live_result
            )
            
            await processing_msg.delete()
            
            # Final summary
            approved = [r for r in results if r["status"] == "APPROVED"]
            declined = [r for r in results if r["status"] == "DECLINED"]
            
            summary = (
                f"═══════════════════════════════\n"
                f"  CHECK COMPLETE\n"
                f"═══════════════════════════════\n\n"
                f"Total: {len(results)}\n"
                f"Approved: {len(approved)}\n"
                f"Declined: {len(declined)}\n"
                f"Gateway: {gw_name}\n\n"
            )
            
            if approved:
                summary += "✅ APPROVED CARDS:\n"
                for r in approved:
                    summary += f"• {r['card']} - {r['gateway']}\n"
                    if r.get('bin_info'):
                        summary += f"  Bank: {r['bin_info'].get('bank', 'N/A')}\n"
            
            await update.message.reply_text(summary)
            
            # Full results as file
            if len(results) > 5:
                filename = f"full_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    for r in results:
                        f.write(f"{r['card']} | {r['status']} | {r['gateway']} | {r['message']}\n")
                        if r.get('bin_info'):
                            f.write(f"  BIN: {r['bin']} | Bank: {r['bin_info'].get('bank')} | Country: {r['bin_info'].get('country')}\n")
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"Full Results: {len(results)} cards"
                    )
                os.remove(filename)
        
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
    
    # ==================== PROGRESS UPDATE ====================
    async def progress_update(self, msg, current: int, total: int, card: str):
        """Update progress"""
        if current % 3 == 0 or current == total:
            percent = int(current / total * 100)
            text = f"⏳ {current}/{total} ({percent}%)\n🔍 {card}"
            try:
                await msg.edit_text(text)
            except:
                pass
    
    # ==================== HANDLE FILE ====================
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file - Live results for approved"""
        user_id = update.effective_user.id
        
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Blocked!")
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        document = update.message.document
        
        if not document.file_name.endswith('.txt'):
            await update.message.reply_text("❌ Only .txt files!")
            return
        
        settings = self.get_settings(user_id)
        gateway = settings["gateway"]
        gw_name = GATEWAYS[gateway]["name"]
        
        progress_msg = await update.message.reply_text("📥 Downloading...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            content = (await file.download_as_bytearray()).decode('utf-8')
            cards = [line.strip() for line in content.split('\n') if line.strip()][:MAX_FILE_CARDS]
            
            await progress_msg.edit_text(f"⏳ Checking {len(cards)} cards...\nGateway: {gw_name}")
            
            # Live results
            async def on_live(result, current, total):
                live_msg = (
                    f"✅ LIVE! ({current}/{total})\n"
                    f"Card: {result['card']}\n"
                    f"BIN: {result['bin']}\n"
                    f"Gateway: {result['gateway']}\n"
                )
                if result.get('bin_info'):
                    bi = result['bin_info']
                    live_msg += f"Bank: {bi.get('bank', 'N/A')} | Country: {bi.get('country', 'N/A')}"
                await update.message.reply_text(live_msg)
            
            results = await checker.check_batch(
                cards,
                gateway=gateway,
                progress_callback=lambda c, t, card: self.progress_update(progress_msg, c, t, card),
                live_result_callback=on_live
            )
            
            # Save file
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for r in results:
                    f.write(f"{r['card']} | {r['status']} | {r['gateway']} | {r['message']}\n")
                    if r.get('bin_info'):
                        bi = r['bin_info']
                        f.write(f"  BIN: {r['bin']} | Bank: {bi.get('bank')} | Country: {bi.get('country')} | Brand: {bi.get('brand')}\n")
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"✅ Complete! {len(results)} cards | Live: {checker.stats['live']} | Die: {checker.stats['die']}"
                )
            
            os.remove(filename)
            await progress_msg.delete()
        
        except Exception as e:
            logger.error(f"File error: {e}")
            await progress_msg.edit_text(f"❌ Error: {str(e)[:200]}")
    
    # ==================== ADMIN COMMANDS ====================
    async def admin_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin commands"""
        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            return
        
        parts = update.message.text.strip().split()
        cmd = parts[0].lower() if parts else ""
        
        if cmd == "/users":
            pending = db.get_pending_users()
            approved = db.get_approved_users()
            msg = f"📊 Users\n\nPending: {len(pending)}\nApproved: {len(approved)}"
            await update.message.reply_text(msg)
        
        elif cmd == "/approve" and len(parts) > 1:
            target = int(parts[1])
            db.approve_user(target, user_id)
            await update.message.reply_text(f"✅ Approved {target}")
        
        elif cmd == "/block" and len(parts) > 1:
            target = int(parts[1])
            db.block_user(target)
            await update.message.reply_text(f"🚫 Blocked {target}")
    
    # ==================== RUN ====================
    def run(self):
        """Run bot"""
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ BOT_TOKEN not configured!")
            sys.exit(1)
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("users", self.admin_commands))
        app.add_handler(CommandHandler("approve", self.admin_commands))
        app.add_handler(CommandHandler("block", self.admin_commands))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_card_input))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        
        print("""
═══════════════════════════════════
  Shopify Card Checker Bot
  Multi-Gateway Support
  Live Results Active
  All Buttons Working
═══════════════════════════════════
        """)
        
        print("✅ Bot is running...")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    bot = ShopifyCardBot()
    bot.run()
