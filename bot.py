#!/usr/bin/env python3
"""
Shopify Card Checker Bot
100% Real Check + User Management + Fixed Output
"""

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
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
    """Main Bot Class"""
    
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
    
    def txt(self, user_id: int, bn: str, en: str) -> str:
        """Get text based on language"""
        lang = self.get_settings(user_id)["language"]
        return bn if lang == "bn" else en
    
    # ==================== START COMMAND ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        user = update.effective_user
        user_id = user.id
        
        # Check if blocked
        if db.is_blocked(user_id):
            await update.message.reply_text(
                "⛔ **Access Blocked**\n\n"
                "আপনার অ্যাকসেস ব্লক করা হয়েছে।\n"
                "Your access has been blocked.\n\n"
                f"📞 Contact: {OWNER_USERNAME}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check if pending
        if db.is_pending(user_id):
            await update.message.reply_text(
                "⏳ **Approval Pending**\n\n"
                "আপনার রিকোয়েস্ট পেন্ডিং আছে।\n"
                "Your request is pending approval.\n"
                "অনুগ্রহ করে অপেক্ষা করুন। Please wait.\n\n"
                f"📞 Contact: {OWNER_USERNAME}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # New user - send access request
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        # User has access - show welcome
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        stats = checker.stats
        total = stats["total"]
        approved = stats["approved"]
        declined = stats["declined"]
        rate = (approved / total * 100) if total > 0 else 0
        
        welcome_bn = f"""
🌟 **Shopify Card Checker Bot** 🌟

👋 **স্বাগতম** {user.first_name}!

**🔍 এই বট যা করে:**
• ১০০% রিয়েল Shopify API চেক
• Shopify, Stripe গেটওয়ে ডিটেকশন
• BIN, কার্ড টাইপ, কান্ট্রি ইনফো
• ১০,০০০+ কার্ড সাপোর্ট

**📊 বর্তমান সেটিংস:**
• 🗣 ভাষা: বাংলা
• 🌐 কান্ট্রি: {country_name}

**📈 টোটাল স্ট্যাটাস:**
🔄 টোটাল চেক: `{total}`
✅ অ্যাপ্রুভ: `{approved}`
❌ ডিক্লাইন: `{declined}`
📊 সাফল্য: `{rate:.1f}%`

**নিচের বাটন থেকে অপশন সিলেক্ট করুন 👇**
        """
        
        welcome_en = f"""
🌟 **Shopify Card Checker Bot** 🌟

👋 **Welcome** {user.first_name}!

**🔍 What this bot does:**
• 100% Real Shopify API Check
• Shopify, Stripe Gateway Detection
• BIN, Card Type, Country Info
• 10,000+ Card Support

**📊 Current Settings:**
• 🗣 Language: English
• 🌐 Country: {country_name}

**📈 Total Stats:**
🔄 Total Checked: `{total}`
✅ Approved: `{approved}`
❌ Declined: `{declined}`
📊 Success Rate: `{rate:.1f}%`

**Select option from buttons below 👇**
        """
        
        welcome = welcome_bn if lang == "bn" else welcome_en
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔍 কার্ড চেক / Check Card",
                    callback_data="check_card"
                )
            ],
            [
                InlineKeyboardButton(
                    "📤 ফাইল আপলোড / Upload File",
                    callback_data="upload_file"
                ),
                InlineKeyboardButton(
                    "📊 স্ট্যাটাস / Status",
                    callback_data="stats"
                )
            ],
            [
                InlineKeyboardButton(
                    "🌐 কান্ট্রি: " + country,
                    callback_data="change_country"
                ),
                InlineKeyboardButton(
                    "🗣 ভাষা / Language",
                    callback_data="change_lang"
                )
            ],
            [
                InlineKeyboardButton(
                    "ℹ️ হেল্প / Help",
                    callback_data="help"
                )
            ]
        ])
        
        await update.message.reply_text(
            welcome,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== ACCESS REQUEST ====================
    async def send_access_request(self, update: Update):
        """Send access request to admins"""
        user = update.effective_user
        user_id = user.id
        
        # Add to pending
        db.add_pending(user_id, {
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or ""
        })
        
        # Notify user
        await update.message.reply_text(
            "📩 **Access Request Sent!**\n\n"
            "আপনার অ্যাকসেস রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।\n"
            "Your access request has been sent to admin.\n\n"
            "⏳ অনুগ্রহ করে অপেক্ষা করুন... Please wait...\n\n"
            f"📞 Contact: {OWNER_USERNAME}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Notify all admins
        for admin_id_str in db.users["admins"]:
            try:
                admin_id = int(admin_id_str)
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ Approve",
                            callback_data=f"approve_{user_id}"
                        ),
                        InlineKeyboardButton(
                            "❌ Reject",
                            callback_data=f"reject_{user_id}"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "🚫 Block",
                            callback_data=f"block_{user_id}"
                        )
                    ]
                ])
                
                await update.get_bot().send_message(
                    chat_id=admin_id,
                    text=(
                        "🔔 **New Access Request**\n\n"
                        f"👤 User: {user.first_name} {user.last_name or ''}\n"
                        f"📛 Username: @{user.username or 'N/A'}\n"
                        f"🆔 ID: `{user_id}`\n\n"
                        "Approve or Reject?"
                    ),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id_str}: {e}")
    
    # ==================== BUTTON HANDLER ====================
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Button callback handler"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # ===== ADMIN ACTIONS =====
        if data.startswith("approve_"):
            target_id = int(data.replace("approve_", ""))
            if db.is_admin(user_id):
                db.approve_user(target_id, user_id)
                await query.edit_message_text(
                    f"✅ User `{target_id}` Approved!\n\n"
                    "তারা এখন বট ব্যবহার করতে পারবে।",
                    parse_mode=ParseMode.MARKDOWN
                )
                # Notify approved user
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text="🎉 **Congratulations!**\n\n"
                             "আপনার অ্যাকসেস অ্যাপ্রুভ হয়েছে!\n"
                             "Your access has been approved!\n\n"
                             "এখন /start দিন এবং বট ব্যবহার করুন।\n"
                             "Send /start to use the bot.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return
        
        if data.startswith("reject_"):
            target_id = int(data.replace("reject_", ""))
            if db.is_admin(user_id):
                db.reject_user(target_id)
                await query.edit_message_text(
                    f"❌ User `{target_id}` Rejected!",
                    parse_mode=ParseMode.MARKDOWN
                )
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text="❌ আপনার অ্যাকসেস রিকোয়েস্ট রিজেক্ট হয়েছে।\n"
                             "Your access request has been rejected.\n\n"
                             f"Contact: {OWNER_USERNAME}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return
        
        if data.startswith("block_"):
            target_id = int(data.replace("block_", ""))
            if db.is_admin(user_id):
                db.block_user(target_id)
                await query.edit_message_text(
                    f"🚫 User `{target_id}` Blocked!",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # ===== CHECK USER ACCESS =====
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            if db.is_pending(user_id):
                await query.edit_message_text(
                    "⏳ Approval Pending... Please wait!",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    "⛔ Access Denied! Send /start first.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        # ===== CHECK CARD =====
        if data == "check_card":
            msg_bn = f"""
📝 **কার্ড ইনপুট দিন:**

**ফরম্যাট:** `4111111111111111|12|2026|123`
**সাপোর্টেড সেপারেটর:** | : , ; space

• সিঙ্গেল কার্ড পাঠান
• একাধিক কার্ড লাইন বাই লাইন দিন
• ১০০+ কার্ডের জন্য ফাইল ব্যবহার করুন

🌐 কান্ট্রি: **{country_name}**
⏱️ প্রতি কার্ডে সময়: **{CHECK_DELAY} সেকেন্ড**

**এখন কার্ড পাঠান ⬇️**
            """
            
            msg_en = f"""
📝 **Enter Card Details:**

**Format:** `4111111111111111|12|2026|123`
**Supported separators:** | : , ; space

• Send single card
• Multiple cards line by line
• Use file for 100+ cards

🌐 Country: **{country_name}**
⏱️ Time per card: **{CHECK_DELAY} seconds**

**Send cards now ⬇️**
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                msg_bn if lang == "bn" else msg_en,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # ===== UPLOAD FILE =====
        elif data == "upload_file":
            msg_bn = """
📤 **ফাইল আপলোড নির্দেশিকা:**

• .txt ফাইল মাত্র
• প্রতি লাইনে ১টি কার্ড
• সর্বোচ্চ ১০,০০০ কার্ড
• ফরম্যাট: `number|mm|yyyy|cvv`

**এখন .txt ফাইল আপলোড করুন 📎**
            """
            
            msg_en = """
📤 **File Upload Guide:**

• .txt files only
• 1 card per line
• Maximum 10,000 cards
• Format: `number|mm|yyyy|cvv`

**Upload .txt file now 📎**
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                msg_bn if lang == "bn" else msg_en,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # ===== STATS =====
        elif data == "stats":
            stats = checker.stats
            total = stats["total"]
            approved = stats["approved"]
            declined = stats["declined"]
            errors = stats["errors"]
            live = stats["live"]
            die = stats["die"]
            rate = (approved / total * 100) if total > 0 else 0
            
            stats_bn = f"""
📊 **চেকিং স্ট্যাটাস**

🔄 **টোটাল চেক:** `{total}`
✅ **অ্যাপ্রুভ:** `{approved}`
❌ **ডিক্লাইন:** `{declined}`
⚠️ **এরর:** `{errors}`

📈 **সাফল্যের হার:** `{rate:.1f}%`
💚 **লাইভ কার্ড:** `{live}`
💀 **ডাই কার্ড:** `{die}`

🔍 **গেটওয়ে:** Shopify API
⏱️ **ডিলে:** {CHECK_DELAY}s/কার্ড
            """
            
            stats_en = f"""
📊 **Checking Status**

🔄 **Total Checked:** `{total}`
✅ **Approved:** `{approved}`
❌ **Declined:** `{declined}`
⚠️ **Errors:** `{errors}`

📈 **Success Rate:** `{rate:.1f}%`
💚 **Live Cards:** `{live}`
💀 **Die Cards:** `{die}`

🔍 **Gateway:** Shopify API
⏱️ **Delay:** {CHECK_DELAY}s/card
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 রিফ্রেশ / Refresh", callback_data="stats")],
                [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                stats_bn if lang == "bn" else stats_en,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # ===== CHANGE COUNTRY =====
        elif data == "change_country":
            keyboard = []
            row = []
            for code, info in COUNTRIES.items():
                row.append(InlineKeyboardButton(
                    info["name"],
                    callback_data=f"country_{code}"
                ))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")])
            
            await query.edit_message_text(
                "🌐 **দেশ সিলেক্ট করুন / Select Country:**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data.startswith("country_"):
            country = data.replace("country_", "")
            settings["country"] = country
            country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
            await query.answer(f"Country: {country_name}")
            await self.back_to_start(query)
        
        # ===== CHANGE LANGUAGE =====
        elif data == "change_lang":
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
                    InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
                ],
                [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                "🗣 **ভাষা সিলেক্ট করুন / Select Language:**",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data.startswith("lang_"):
            lang = data.replace("lang_", "")
            settings["language"] = lang
            await query.answer(f"Language: {'বাংলা' if lang == 'bn' else 'English'}")
            await self.back_to_start(query)
        
        # ===== HELP =====
        elif data == "help":
            help_bn = f"""
ℹ️ **হেল্প ও তথ্য**

**কার্ড ফরম্যাট:**
`4111111111111111|12|2026|123`
`number|month|year|cvv`

**রেজাল্ট বুঝবেন কিভাবে:**
✅ **APPROVED** = কার্ড কাজ করে (Live)
❌ **DECLINED** = কার্ড রিজেক্ট (Die)
⚠️ **UNKNOWN** = ম্যানুয়াল চেক প্রয়োজন

**ফাইল চেকিং:**
• .txt ফাইল মাত্র
• সর্বোচ্চ ১০,০০০ কার্ড
• প্রতি লাইনে ১টি কার্ড

**গেটওয়ে:** Shopify, Stripe
**স্পিড:** {CHECK_DELAY}s/কার্ড

**সাপোর্ট:** {OWNER_USERNAME}
**বট:** {BOT_USERNAME}
            """
            
            help_en = f"""
ℹ️ **Help & Information**

**Card Format:**
`4111111111111111|12|2026|123`
`number|month|year|cvv`

**Understanding Results:**
✅ **APPROVED** = Card works (Live)
❌ **DECLINED** = Card rejected (Die)
⚠️ **UNKNOWN** = Manual check needed

**File Checking:**
• .txt files only
• Maximum 10,000 cards
• 1 card per line

**Gateway:** Shopify, Stripe
**Speed:** {CHECK_DELAY}s/card

**Support:** {OWNER_USERNAME}
**Bot:** {BOT_USERNAME}
            """
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                help_bn if lang == "bn" else help_en,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # ===== BACK TO START =====
        elif data == "back_to_start":
            await self.back_to_start(query)
    
    # ==================== BACK TO START ====================
    async def back_to_start(self, query):
        """Return to main menu"""
        user_id = query.from_user.id
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        msg = (
            "🔄 **মেন মেনুতে ফিরে এসেছেন**\n\n"
            "নিচের বাটন থেকে অপশন সিলেক্ট করুন 👇"
        ) if lang == "bn" else (
            "🔄 **Back to Main Menu**\n\n"
            "Select option from buttons below 👇"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Check Card", callback_data="check_card"),
                InlineKeyboardButton("📤 Upload File", callback_data="upload_file")
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
                InlineKeyboardButton("🌐 Country: " + country, callback_data="change_country")
            ],
            [
                InlineKeyboardButton("🗣 Language", callback_data="change_lang"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help")
            ]
        ])
        
        await query.edit_message_text(
            msg,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== HANDLE CARD INPUT - FIXED OUTPUT ====================
    async def handle_card_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle card text input - WITH PROPER OUTPUT"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        # Check access
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Access Blocked!", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            if db.is_pending(user_id):
                await update.message.reply_text("⏳ Approval Pending...", parse_mode=ParseMode.MARKDOWN)
            else:
                await self.send_access_request(update)
            return
        
        text = update.message.text.strip()
        cards = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not cards:
            await update.message.reply_text(
                "❌ কোনো কার্ড পাওয়া যায়নি! / No cards found!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if len(cards) > 100:
            await update.message.reply_text(
                "⚠️ ১০০+ কার্ডের জন্য .txt ফাইল ব্যবহার করুন!\n"
                "⚠️ Use .txt file for 100+ cards!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        # ===== SEND PROCESSING MESSAGE =====
        processing_msg = await update.message.reply_text(
            f"⏳ **{len(cards)}টি কার্ড চেক হচ্ছে...**\n\n"
            f"🌐 কান্ট্রি: {country} - {country_name}\n"
            f"⏱️ আনুমানিক সময়: {len(cards) * CHECK_DELAY} সেকেন্ড\n"
            f"🔍 গেটওয়ে: Shopify API\n\n"
            f"🔄 চেকিং শুরু... দয়া করে অপেক্ষা করুন..." if lang == "bn" else
            f"⏳ **Checking {len(cards)} cards...**\n\n"
            f"🌐 Country: {country} - {country_name}\n"
            f"⏱️ Estimated time: {len(cards) * CHECK_DELAY} seconds\n"
            f"🔍 Gateway: Shopify API\n\n"
            f"🔄 Starting check... Please wait...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # ===== PROCESS CARDS =====
            results = await checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.update_progress(
                    processing_msg, c, t, card, lang
                )
            )
            
            # ===== FORMAT RESULTS =====
            result_text = self.format_results(results, lang, country_name)
            
            # ===== DELETE PROCESSING MESSAGE =====
            await processing_msg.delete()
            
            # ===== SEND RESULTS - ALWAYS =====
            if len(result_text) > 4000:
                # Save as file
                filename = f"shopify_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=(
                            f"✅ **চেক সম্পন্ন!** {len(results)} কার্ড\n\n"
                            f"💚 লাইভ: {checker.stats['live']}\n"
                            f"💀 ডাই: {checker.stats['die']}\n"
                            f"📊 সাফল্য: {checker.stats['approved']/max(1,checker.stats['total'])*100:.1f}%"
                        ) if lang == "bn" else (
                            f"✅ **Check Complete!** {len(results)} cards\n\n"
                            f"💚 Live: {checker.stats['live']}\n"
                            f"💀 Die: {checker.stats['die']}\n"
                            f"📊 Success: {checker.stats['approved']/max(1,checker.stats['total'])*100:.1f}%"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                os.remove(filename)
            else:
                # Send as text message
                await update.message.reply_text(
                    result_text,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        except Exception as e:
            logger.error(f"Card check error: {e}")
            await processing_msg.edit_text(
                f"❌ **এরর হয়েছে!**\n\n"
                f"কারণ: `{str(e)[:200]}`\n\n"
                f"আবার চেষ্টা করুন বা /start দিন।" if lang == "bn" else
                f"❌ **Error occurred!**\n\n"
                f"Reason: `{str(e)[:200]}`\n\n"
                f"Try again or send /start.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ==================== UPDATE PROGRESS ====================
    async def update_progress(self, msg, current: int, total: int, card: str, lang: str):
        """Update progress message"""
        if current % 3 == 0 or current == total:
            percent = int(current / total * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            
            text = (
                f"⏳ **চেকিং প্রোগ্রেস:** {current}/{total}\n"
                f"📊 [{bar}] {percent}%\n"
                f"🔍 `{card}`\n"
                f"🌐 Shopify API রিয়েল চেক চলছে..."
            ) if lang == "bn" else (
                f"⏳ **Checking Progress:** {current}/{total}\n"
                f"📊 [{bar}] {percent}%\n"
                f"🔍 `{card}`\n"
                f"🌐 Real Shopify API check running..."
            )
            
            try:
                await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
            except:
                pass
    
    # ==================== HANDLE FILE UPLOAD ====================
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file upload"""
        user_id = update.effective_user.id
        
        if db.is_blocked(user_id):
            await update.message.reply_text("⛔ Access Blocked!", parse_mode=ParseMode.MARKDOWN)
            return
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            if db.is_pending(user_id):
                await update.message.reply_text("⏳ Approval Pending...", parse_mode=ParseMode.MARKDOWN)
            else:
                await self.send_access_request(update)
            return
        
        document = update.message.document
        
        if not document.file_name.endswith('.txt'):
            await update.message.reply_text(
                "❌ শুধু .txt ফাইল / Only .txt files allowed!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if document.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ ফাইল 5MB এর বেশি / File too large (max 5MB)!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        progress_msg = await update.message.reply_text(
            "📥 ফাইল ডাউনলোড হচ্ছে... / Downloading file...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            content = file_bytes.decode('utf-8')
            
            cards = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not cards:
                await progress_msg.edit_text(
                    "❌ ফাইলে কোনো কার্ড পাওয়া যায়নি! / No cards found!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            if len(cards) > MAX_FILE_CARDS:
                cards = cards[:MAX_FILE_CARDS]
            
            await progress_msg.edit_text(
                f"⏳ **{len(cards)}টি কার্ড চেক হচ্ছে...**\n\n"
                f"🌐 কান্ট্রি: {country} - {country_name}\n"
                f"⏱️ আনুমানিক সময়: {len(cards) * CHECK_DELAY // 60} মিনিট\n"
                f"🔍 গেটওয়ে: Shopify API\n\n"
                f"🔄 চেকিং শুরু..." if lang == "bn" else
                f"⏳ **Checking {len(cards)} cards...**\n\n"
                f"🌐 Country: {country} - {country_name}\n"
                f"⏱️ Estimated: {len(cards) * CHECK_DELAY // 60} minutes\n"
                f"🔍 Gateway: Shopify API\n\n"
                f"🔄 Starting check...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Process cards
            results = await checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.update_progress(
                    progress_msg, c, t, card, lang
                )
            )
            
            # Format results
            result_text = self.format_results(results, lang, country_name)
            
            # Save and send file
            filename = f"shopify_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result_text)
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=(
                        f"✅ **চেক সম্পন্ন!** {len(results)} কার্ড\n\n"
                        f"💚 লাইভ: {checker.stats['live']}\n"
                        f"💀 ডাই: {checker.stats['die']}\n"
                        f"📊 সাফল্য: {checker.stats['approved']/max(1,checker.stats['total'])*100:.1f}%\n\n"
                        f"🤖 {BOT_USERNAME}"
                    ) if lang == "bn" else (
                        f"✅ **Check Complete!** {len(results)} cards\n\n"
                        f"💚 Live: {checker.stats['live']}\n"
                        f"💀 Die: {checker.stats['die']}\n"
                        f"📊 Success: {checker.stats['approved']/max(1,checker.stats['total'])*100:.1f}%\n\n"
                        f"🤖 {BOT_USERNAME}"
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            os.remove(filename)
            await progress_msg.delete()
        
        except Exception as e:
            logger.error(f"File error: {e}")
            await progress_msg.edit_text(
                f"❌ এরর: {str(e)[:200]}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ==================== FORMAT RESULTS - FIXED ====================
    def format_results(self, results: list, lang: str, country_name: str = "") -> str:
        """Format results for output"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = len(results)
        
        approved = [r for r in results if r["status"] == "APPROVED"]
        declined = [r for r in results if r["status"] == "DECLINED"]
        others = [r for r in results if r["status"] not in ("APPROVED", "DECLINED", "INVALID")]
        invalid = [r for r in results if r["status"] == "INVALID"]
        
        # Header
        output = "╔══════════════════════════════════════════╗\n"
        output += "║     SHOPIFY CARD CHECK RESULTS         ║\n"
        output += "╚══════════════════════════════════════════╝\n\n"
        
        output += f"📅 **তারিখ:** {now}\n" if lang == "bn" else f"📅 **Date:** {now}\n"
        output += f"📊 **টোটাল:** {total}\n"
        output += f"✅ **অ্যাপ্রুভ:** {len(approved)}\n" if lang == "bn" else f"✅ **Approved:** {len(approved)}\n"
        output += f"❌ **ডিক্লাইন:** {len(declined)}\n" if lang == "bn" else f"❌ **Declined:** {len(declined)}\n"
        if others:
            output += f"⚠️ **অন্যান্য:** {len(others)}\n" if lang == "bn" else f"⚠️ **Other:** {len(others)}\n"
        if invalid:
            output += f"🚫 **ইনভ্যালিড:** {len(invalid)}\n" if lang == "bn" else f"🚫 **Invalid:** {len(invalid)}\n"
        
        output += "\n" + "═" * 50 + "\n"
        
        # Approved cards
        if approved:
            output += "\n✅ **APPROVED / LIVE CARDS:**\n"
            output += "─" * 45 + "\n"
            for i, r in enumerate(approved, 1):
                output += f"\n🔹 **{i}.** `{r['card']}`\n"
                output += f"   ├─ BIN: `{r.get('bin', 'N/A')}`\n"
                output += f"   ├─ Type: {r.get('card_type', 'Unknown')}\n"
                output += f"   ├─ Gateway: {r.get('gateway', 'N/A')}\n"
                output += f"   ├─ Country: {r.get('country', 'US')}\n"
                output += f"   ├─ Time: {r.get('response_time', 'N/A')}\n"
                output += f"   └─ Status: {r.get('message', 'N/A')}\n"
        
        # Declined cards
        if declined:
            output += "\n❌ **DECLINED / DIE CARDS:**\n"
            output += "─" * 45 + "\n"
            for i, r in enumerate(declined, 1):
                output += f"\n🔸 **{i}.** `{r['card']}`\n"
                output += f"   ├─ BIN: `{r.get('bin', 'N/A')}`\n"
                output += f"   ├─ Type: {r.get('card_type', 'Unknown')}\n"
                output += f"   ├─ Gateway: {r.get('gateway', 'N/A')}\n"
                output += f"   └─ Status: {r.get('message', 'N/A')}\n"
        
        # Other/Unknown cards
        if others:
            output += "\n⚠️ **UNKNOWN / ERRORS:**\n"
            output += "─" * 45 + "\n"
            for i, r in enumerate(others, 1):
                output += f"\n▪️ **{i}.** `{r['card']}`\n"
                output += f"   └─ {r.get('message', 'Unknown error')}\n"
        
        # Invalid cards
        if invalid:
            output += "\n🚫 **INVALID FORMAT:**\n"
            output += "─" * 45 + "\n"
            for i, r in enumerate(invalid, 1):
                output += f"\n✖️ **{i}.** `{r['card']}`\n"
                output += f"   └─ {r.get('message', 'Invalid format')}\n"
        
        # Footer
        output += f"""
{'═' * 50}
📊 **সারাংশ:** {len(approved)} LIVE | {len(declined)} DIE | {total} TOTAL
🤖 Bot: {BOT_USERNAME}
👤 Owner: {OWNER_USERNAME}
⏰ {now}
"""
        
        return output
    
    # ==================== ADMIN COMMANDS ====================
    async def admin_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin commands"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            return
        
        command = update.message.text.strip().split()
        cmd = command[0].lower()
        
        if cmd == "/users":
            pending = db.get_pending_users()
            approved = db.get_approved_users()
            
            msg = "📊 **User Management**\n\n"
            msg += f"⏳ **Pending ({len(pending)}):**\n"
            for u in pending:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - `{u['id']}`\n"
            
            msg += f"\n✅ **Approved ({len(approved)}):**\n"
            for u in approved[:20]:
                msg += f"• {u['first_name']} (@{u.get('username', 'N/A')}) - `{u['id']}`\n"
            
            if len(approved) > 20:
                msg += f"... and {len(approved) - 20} more\n"
            
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        
        elif cmd == "/approve":
            if len(command) > 1:
                target = int(command[1])
                db.approve_user(target, user_id)
                await update.message.reply_text(
                    f"✅ User `{target}` Approved!",
                    parse_mode=ParseMode.MARKDOWN
                )
                try:
                    await context.bot.send_message(
                        chat_id=target,
                        text="🎉 Your access has been approved!\nSend /start to use the bot."
                    )
                except:
                    pass
        
        elif cmd == "/block":
            if len(command) > 1:
                target = int(command[1])
                db.block_user(target)
                await update.message.reply_text(
                    f"🚫 User `{target}` Blocked!",
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif cmd == "/unblock":
            if len(command) > 1:
                target = int(command[1])
                db.unblock_user(target)
                await update.message.reply_text(
                    f"✅ User `{target}` Unblocked!",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    # ==================== RUN BOT ====================
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
        
        logger.info("""
╔══════════════════════════════════════════╗
║   🤖 Shopify Card Checker Bot v3.0     ║
║   ✅ 100% Real API Check               ║
║   👥 User Management                   ║
║   📊 Fixed Output                      ║
║   🚀 Railway Ready                     ║
╚══════════════════════════════════════════╝
        """)
        
        print("✅ Bot is running... Press Ctrl+C to stop")
        
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

# ==================== MAIN ====================
if __name__ == "__main__":
    bot = ShopifyCardBot()
    bot.run()
