#!/usr/bin/env python3
"""
Shopify Card Checker Bot - Professional
Admin Panel + Multi Gateway + Broadcast + User Management
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
    """Professional Bot"""
    
    def __init__(self):
        self.user_settings: Dict[int, Dict] = {}
    
    def get_settings(self, user_id: int) -> Dict:
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                "language": "en",
                "country": "US",
                "gateway": "stripe"
            }
        return self.user_settings[user_id]
    
    # ==================== START ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ You are blocked!\nContact: " + OWNER_USERNAME)
            return
        
        if db.is_pending(user_id):
            await update.message.reply_text("⏳ Approval Pending...\nPlease wait for admin approval.")
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        settings = self.get_settings(user_id)
        gateway = settings["gateway"]
        gw_name = GATEWAYS[gateway]["name"]
        
        stats = checker.stats
        
        welcome = f"""
🌟 **Shopify Card Checker Pro** 🌟

👋 Welcome **{user.first_name}**!

⚡ **5 Payment Gateways**
✅ Live Card Detection
📊 Full Card Details
🌍 14 Countries

**Your Settings:**
• Country: {COUNTRIES[settings['country']]['name']}
• Gateway: {gw_name}

**Global Stats:**
• Total: {stats['total']}
• Approved: {stats['approved']}
• Declined: {stats['declined']}

Select option below 👇
        """
        
        keyboard_buttons = [
            [InlineKeyboardButton("🔍 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🌐 Country: " + settings["country"], callback_data="change_country")],
            [InlineKeyboardButton("🚀 Gateway: " + gateway.upper(), callback_data="change_gateway")],
            [InlineKeyboardButton("🗣 Language", callback_data="change_lang"),
             InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        
        if db.is_admin(user_id):
            keyboard_buttons.append([
                InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")
            ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await update.message.reply_text(welcome, reply_markup=keyboard, parse_mode='Markdown')
    
    # ==================== ACCESS REQUEST ====================
    async def send_access_request(self, update: Update):
        user = update.effective_user
        user_id = user.id
        
        db.add_pending(user_id, {
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or ""
        })
        
        await update.message.reply_text(
            "📩 **Access Request Sent!**\n\n"
            "Your request has been sent to admin.\n"
            "Please wait for approval.\n\n"
            f"Contact: {OWNER_USERNAME}",
            parse_mode='Markdown'
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
                    text=f"🔔 **New Access Request**\n\n"
                         f"👤 {user.first_name} (@{user.username or 'N/A'})\n"
                         f"🆔 `{user_id}`",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            except:
                pass
    
    # ==================== BUTTON HANDLER ====================
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # Admin actions
        if data.startswith("approve_"):
            if db.is_admin(user_id):
                target = int(data.replace("approve_", ""))
                db.approve_user(target, user_id)
                await query.edit_message_text(f"✅ User `{target}` Approved!")
                try:
                    await context.bot.send_message(target, "🎉 Approved! Send /start")
                except:
                    pass
            return
        
        if data.startswith("reject_"):
            if db.is_admin(user_id):
                target = int(data.replace("reject_", ""))
                db.reject_user(target)
                await query.edit_message_text(f"❌ User `{target}` Rejected!")
            return
        
        if data.startswith("block_"):
            if db.is_admin(user_id):
                target = int(data.replace("block_", ""))
                db.block_user(target)
                await query.edit_message_text(f"🚫 User `{target}` Blocked!")
            return
        
        if data.startswith("unblock_"):
            if db.is_admin(user_id):
                target = int(data.replace("unblock_", ""))
                db.unblock_user(target)
                await query.edit_message_text(f"✅ User `{target}` Unblocked!")
            return
        
        if data.startswith("remove_"):
            if db.is_admin(user_id):
                target = int(data.replace("remove_", ""))
                db.remove_user(target)
                await query.edit_message_text(f"🗑 User `{target}` Removed!")
            return
        
        # Check access
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await query.edit_message_text("⛔ Access Denied!")
            return
        
        settings = self.get_settings(user_id)
        
        # ===== ADMIN PANEL =====
        if data == "admin_panel":
            if not db.is_admin(user_id):
                return
            
            db_stats = db.get_stats()
            panel = f"""
👑 **Admin Panel**

📊 **Database Stats:**
• Total Users: {db_stats['total_users']}
• Approved: {db_stats['approved_users']}
• Pending: {db_stats['pending_users']}
• Blocked: {db_stats['blocked_users']}
• Total Checks: {db_stats['total_checks']}
• Broadcasts: {db_stats['broadcasts']}

Select action:
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 User List", callback_data="user_list")],
                [InlineKeyboardButton("⏳ Pending Users", callback_data="pending_users")],
                [InlineKeyboardButton("🚫 Blocked Users", callback_data="blocked_users")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
                [InlineKeyboardButton("📋 Check History", callback_data="check_history")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(panel, reply_markup=keyboard, parse_mode='Markdown')
        
        # User List
        elif data == "user_list":
            if not db.is_admin(user_id):
                return
            
            approved = db.get_approved_users()
            msg = "👥 **Approved Users:**\n\n"
            for u in approved[:30]:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - `{u['id']}`\n"
                msg += f"  Checks: {u.get('total_checks', 0)} | Approved: {u.get('total_approved', 0)}\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
        
        # Pending Users
        elif data == "pending_users":
            if not db.is_admin(user_id):
                return
            
            pending = db.get_pending_users()
            if not pending:
                await query.edit_message_text("✅ No pending users!")
                return
            
            msg = "⏳ **Pending Users:**\n\n"
            for u in pending:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - `{u['id']}`\n"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"✅ Approve {u['first_name']}", callback_data=f"approve_{u['id']}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"reject_{u['id']}")],
                    [InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]
                ])
                await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
                return
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
        
        # Blocked Users
        elif data == "blocked_users":
            if not db.is_admin(user_id):
                return
            
            blocked = db.get_blocked_users()
            if not blocked:
                await query.edit_message_text("✅ No blocked users!")
                return
            
            msg = "🚫 **Blocked Users:**\n\n"
            for u in blocked:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - `{u['id']}`\n"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"✅ Unblock {u['first_name']}", callback_data=f"unblock_{u['id']}"),
                     InlineKeyboardButton("🗑 Remove", callback_data=f"remove_{u['id']}")],
                    [InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]
                ])
                await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
                return
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
        
        # Broadcast
        elif data == "broadcast":
            if not db.is_admin(user_id):
                return
            
            self.user_settings[user_id]["awaiting_broadcast"] = True
            await query.edit_message_text(
                "📢 **Broadcast Mode**\n\n"
                "Send the message you want to broadcast to all approved users.\n"
                "Send /cancel to cancel."
            )
        
        # Check History
        elif data == "check_history":
            if not db.is_admin(user_id):
                return
            
            history = db.users.get("check_history", [])[-20:]
            msg = "📋 **Recent Checks:**\n\n"
            for h in reversed(history):
                msg += f"• {h['card']} - {h['status']} ({h['gateway']})\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_panel")]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
        
        # ===== REGULAR BUTTONS =====
        elif data == "check_card":
            msg = f"""
📝 **Enter Card Details:**

Format: `4111111111111111|12|2026|123`
Separators: | : , ; space

Gateway: {GATEWAYS[settings['gateway']]['name']}
Country: {COUNTRIES[settings['country']]['name']}

Send cards now ⬇️
            """
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "upload_file":
            msg = """
📤 **Upload .txt File**

• 1 card per line
• Max 10,000 cards
• Format: number|mm|yyyy|cvv

Upload now 📎
            """
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "stats":
            s = checker.stats
            rate = (s['approved'] / s['total'] * 100) if s['total'] > 0 else 0
            stats_msg = f"""
📊 **Checking Stats**

Total: {s['total']}
✅ Approved: {s['approved']}
❌ Declined: {s['declined']}
📈 Rate: {rate:.1f}%
💚 Live: {s['live']}
💀 Die: {s['die']}

Gateway: {GATEWAYS[settings['gateway']]['name']}
            """
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            await query.edit_message_text(stats_msg, reply_markup=keyboard, parse_mode='Markdown')
        
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
            await query.edit_message_text("🌐 **Select Country:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data.startswith("country_"):
            settings["country"] = data.replace("country_", "")
            await query.answer(f"Country: {COUNTRIES[settings['country']]['name']}")
            await self.back_to_start(query)
        
        elif data == "change_gateway":
            keyboard = []
            for gw_id, gw_info in GATEWAYS.items():
                keyboard.append([InlineKeyboardButton(gw_info["name"], callback_data=f"gateway_{gw_id}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
            await query.edit_message_text("🚀 **Select Gateway:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data.startswith("gateway_"):
            settings["gateway"] = data.replace("gateway_", "")
            await query.answer(f"Gateway: {GATEWAYS[settings['gateway']]['name']}")
            await self.back_to_start(query)
        
        elif data == "change_lang":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🇧🇩 Bangla", callback_data="lang_bn"),
                 InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            await query.edit_message_text("🗣 **Select Language:**", reply_markup=keyboard, parse_mode='Markdown')
        
        elif data.startswith("lang_"):
            settings["language"] = data.replace("lang_", "")
            await query.answer(f"Language: {'Bangla' if settings['language'] == 'bn' else 'English'}")
            await self.back_to_start(query)
        
        elif data == "help":
            help_msg = f"""
ℹ️ **Help**

**5 Gateways:**
• Stripe - Shopify payment
• Braintree - PayPal
• Adyen - Global processor
• Checkout.com - Enterprise
• BIN Lookup - Card info

**Format:** `4111111111111111|12|2026|123`

**Support:** {OWNER_USERNAME}
            """
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            await query.edit_message_text(help_msg, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "back_to_start":
            await self.back_to_start(query)
    
    # ==================== BACK TO START ====================
    async def back_to_start(self, query):
        user_id = query.from_user.id
        settings = self.get_settings(user_id)
        gateway = settings["gateway"]
        
        keyboard_buttons = [
            [InlineKeyboardButton("🔍 Check Card", callback_data="check_card")],
            [InlineKeyboardButton("📤 Upload File", callback_data="upload_file"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🌐 Country: " + settings["country"], callback_data="change_country")],
            [InlineKeyboardButton("🚀 Gateway: " + gateway.upper(), callback_data="change_gateway")],
            [InlineKeyboardButton("🗣 Language", callback_data="change_lang"),
             InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        
        if db.is_admin(user_id):
            keyboard_buttons.append([
                InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")
            ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text("🔄 **Main Menu**", reply_markup=keyboard, parse_mode='Markdown')
    
    # ==================== HANDLE CARD INPUT ====================
    async def handle_card_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        settings = self.get_settings(user_id)
        if settings.get("awaiting_broadcast") and db.is_admin(user_id):
            await self.handle_broadcast(update, context)
            return
        
        if db.is_blocked(user_id):
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        text = update.message.text.strip()
        if text == "/cancel":
            settings.pop("awaiting_broadcast", None)
            await update.message.reply_text("✅ Cancelled!")
            return
        
        cards = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not cards:
            return
        
        gateway = settings["gateway"]
        gw_name = GATEWAYS[gateway]["name"]
        country = settings["country"]
        
        processing_msg = await update.message.reply_text(
            f"⏳ Checking {len(cards)} cards...\n"
            f"Gateway: {gw_name}\n"
            f"Country: {COUNTRIES[country]['name']}"
        )
        
        async def on_live_result(result, current, total):
            live_msg = (
                f"✅ **LIVE CARD FOUND!** ({current}/{total})\n\n"
                f"💳 **Card:** `{result['card']}`\n"
                f"🔢 **BIN:** `{result['bin']}`\n"
                f"🔹 **Last 4:** `{result.get('last4', 'N/A')}`\n"
                f"📅 **Expiry:** `{result.get('expiry', 'N/A')}`\n"
                f"🏦 **Type:** {result['card_type']}\n"
                f"🌐 **Gateway:** {result['gateway']}\n"
                f"⏱️ **Time:** {result['response_time']}\n"
            )
            if result.get('bin_info'):
                bi = result['bin_info']
                live_msg += (
                    f"🏛 **Bank:** {bi.get('bank', 'N/A')}\n"
                    f"🌍 **Country:** {bi.get('country', 'N/A')}\n"
                    f"🏷 **Brand:** {bi.get('brand', 'N/A')}\n"
                    f"💼 **Card Type:** {bi.get('type', 'N/A')}\n"
                )
            
            await update.message.reply_text(live_msg, parse_mode='Markdown')
        
        try:
            results = await checker.check_batch(
                cards,
                gateway=gateway,
                country=country,
                progress_callback=lambda c, t, card: self.progress_update(processing_msg, c, t, card),
                live_result_callback=on_live_result
            )
            
            await processing_msg.delete()
            
            approved = [r for r in results if r["status"] == "APPROVED"]
            declined = [r for r in results if r["status"] == "DECLINED"]
            
            summary = (
                "═══════════════════════════════\n"
                "  ✅ CHECK COMPLETE\n"
                "═══════════════════════════════\n\n"
                f"📊 Total: {len(results)}\n"
                f"✅ Approved: {len(approved)}\n"
                f"❌ Declined: {len(declined)}\n"
                f"🌐 Gateway: {gw_name}\n\n"
            )
            
            if approved:
                summary += "**APPROVED CARDS:**\n"
                for r in approved:
                    summary += f"• `{r['card']}` - {r['gateway']}\n"
            
            await update.message.reply_text(summary, parse_mode='Markdown')
            
            if len(results) > 3:
                filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    for r in results:
                        f.write(f"{r['card']} | {r['status']} | {r['gateway']} | {r['message']}\n")
                        if r.get('bin_info'):
                            bi = r['bin_info']
                            f.write(f"  BIN:{r['bin']} | Bank:{bi.get('bank')} | Country:{bi.get('country')} | Type:{bi.get('type')}\n")
                        f.write("\n")
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"Full Results: {len(results)} cards | Live: {len(approved)} | Die: {len(declined)}"
                    )
                os.remove(filename)
            
            db.update_user_stats(user_id, len(approved))
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)[:200]}")
    
    # ==================== BROADCAST ====================
    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            return
        
        message = update.message.text.strip()
        settings = self.get_settings(user_id)
        settings.pop("awaiting_broadcast", None)
        
        approved = db.get_approved_users()
        sent = 0
        
        await update.message.reply_text(f"📢 Broadcasting to {len(approved)} users...")
        
        for user in approved:
            try:
                await context.bot.send_message(
                    chat_id=user['id'],
                    text=f"📢 **Broadcast from Admin:**\n\n{message}",
                    parse_mode='Markdown'
                )
                sent += 1
                await asyncio.sleep(0.5)
            except:
                pass
        
        db.add_broadcast(message, sent)
        await update.message.reply_text(f"✅ Broadcast sent to {sent}/{len(approved)} users!")
    
    # ==================== PROGRESS ====================
    async def progress_update(self, msg, current: int, total: int, card: str):
        if current % 3 == 0 or current == total:
            percent = int(current / total * 100)
            text = f"⏳ {current}/{total} ({percent}%)\n🔍 `{card}`"
            try:
                await msg.edit_text(text, parse_mode='Markdown')
            except:
                pass
    
    # ==================== HANDLE FILE ====================
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if db.is_blocked(user_id):
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
            
            async def on_live(result, current, total):
                live_msg = (
                    f"✅ **LIVE!** ({current}/{total})\n"
                    f"💳 `{result['card']}`\n"
                    f"🔢 BIN: `{result['bin']}`\n"
                    f"🌐 {result['gateway']}\n"
                )
                if result.get('bin_info'):
                    bi = result['bin_info']
                    live_msg += f"🏛 {bi.get('bank', 'N/A')} | 🌍 {bi.get('country', 'N/A')}"
                await update.message.reply_text(live_msg, parse_mode='Markdown')
            
            results = await checker.check_batch(
                cards,
                gateway=gateway,
                progress_callback=lambda c, t, card: self.progress_update(progress_msg, c, t, card),
                live_result_callback=on_live
            )
            
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for r in results:
                    f.write(f"{r['card']} | {r['status']} | {r['gateway']} | {r['message']}\n")
                    if r.get('bin_info'):
                        bi = r['bin_info']
                        f.write(f"  BIN:{r['bin']} | Bank:{bi.get('bank')} | Country:{bi.get('country')} | Brand:{bi.get('brand')} | Type:{bi.get('type')}\n")
                    f.write("\n")
            
            with open(filename, 'rb') as f:
                approved = len([r for r in results if r['status'] == 'APPROVED'])
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"✅ Complete! {len(results)} cards | Live: {approved}"
                )
            
            os.remove(filename)
            await progress_msg.delete()
            
            db.update_user_stats(user_id, approved)
            
        except Exception as e:
            logger.error(f"File error: {e}")
            await progress_msg.edit_text(f"❌ Error: {str(e)[:200]}")
    
    # ==================== ADMIN COMMANDS ====================
    async def admin_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            return
        
        parts = update.message.text.strip().split()
        cmd = parts[0].lower() if parts else ""
        
        if cmd == "/users":
            approved = db.get_approved_users()
            pending = db.get_pending_users()
            blocked = db.get_blocked_users()
            msg = f"📊 Users\n\n✅ Approved: {len(approved)}\n⏳ Pending: {len(pending)}\n🚫 Blocked: {len(blocked)}"
            await update.message.reply_text(msg)
        
        elif cmd == "/approve" and len(parts) > 1:
            target = int(parts[1])
            if db.approve_user(target, user_id):
                await update.message.reply_text(f"✅ User {target} Approved!")
                try:
                    await context.bot.send_message(target, "🎉 Approved! Send /start")
                except:
                    pass
        
        elif cmd == "/block" and len(parts) > 1:
            target = int(parts[1])
            db.block_user(target)
            await update.message.reply_text(f"🚫 User {target} Blocked!")
        
        elif cmd == "/broadcast":
            self.user_settings[user_id]["awaiting_broadcast"] = True
            await update.message.reply_text("📢 Send the broadcast message now:")
    
    # ==================== RUN ====================
    def run(self):
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ BOT_TOKEN not configured!")
            sys.exit(1)
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("users", self.admin_commands))
        app.add_handler(CommandHandler("approve", self.admin_commands))
        app.add_handler(CommandHandler("block", self.admin_commands))
        app.add_handler(CommandHandler("broadcast", self.admin_commands))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_card_input))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        
        async def error_handler(update, context):
            logger.error(f"Error: {context.error}")
        
        app.add_error_handler(error_handler)
        
        print("""
══════════════════════════════════════════
  🚀 Shopify Card Checker Pro
  👑 Admin Panel Active
  🌐 5 Gateways
  📢 Broadcast System
  👥 20-25 Concurrent Users
══════════════════════════════════════════
        """)
        
        print("✅ Bot is running...")
        
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

if __name__ == "__main__":
    bot = ShopifyCardBot()
    bot.run()
