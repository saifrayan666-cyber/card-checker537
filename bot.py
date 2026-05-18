#!/usr/bin/env python3
"""
Shopify Card Checker Bot
100% Real Check + User Management
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
    
    async def check_access(self, update: Update) -> bool:
        """Check if user has access"""
        user_id = update.effective_user.id
        
        # Admin always has access
        if db.is_admin(user_id):
            return True
        
        # Check if approved
        if db.is_approved(user_id):
            return True
        
        # Check if blocked
        if db.is_blocked(user_id):
            await update.message.reply_text(
                "⛔ **Access Blocked**\n\n"
                "আপনার অ্যাকসেস ব্লক করা হয়েছে।\n"
                "Your access has been blocked.\n\n"
                f"📞 Contact: {OWNER_USERNAME}",
                parse_mode=ParseMode.MARKDOWN
            )
            return False
        
        # Check if pending
        if db.is_pending(user_id):
            await update.message.reply_text(
                "⏳ **Approval Pending**\n\n"
                "আপনার রিকোয়েস্ট পেন্ডিং আছে।\n"
                "Your request is pending approval.\n"
                "অনুগ্রহ করে অপেক্ষা করুন। Please wait.",
                parse_mode=ParseMode.MARKDOWN
            )
            return False
        
        # New user - send request
        await self.send_access_request(update)
        return False
    
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
        for admin_id in db.users["admins"]:
            try:
                admin_id = int(admin_id)
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
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        user = update.effective_user
        user_id = user.id
        
        # Check access
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            if db.is_blocked(user_id):
                await update.message.reply_text(
                    "⛔ **Access Blocked**\n\n"
                    "আপনার অ্যাকসেস ব্লক করা হয়েছে।\n"
                    f"Contact: {OWNER_USERNAME}",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            if db.is_pending(user_id):
                await update.message.reply_text(
                    "⏳ **Approval Pending**\n\n"
                    "আপনার রিকোয়েস্ট পেন্ডিং আছে।\n"
                    "অনুগ্রহ করে অপেক্ষা করুন।",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # New user
            await self.send_access_request(update)
            return
        
        # User has access
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        welcome = (
            f"""
🌟 **Shopify Card Checker Bot** 🌟

👋 **স্বাগতম** {user.first_name}!

**🔍 ফিচারসমূহ:**
• ১০০% রিয়েল Shopify API চেক
• Shopify, Stripe গেটওয়ে ডিটেকশন
• BIN, কার্ড টাইপ, কান্ট্রি ইনফো
• ১০,০০০+ কার্ড সাপোর্ট

**📊 বর্তমান সেটিংস:**
• ভাষা: {"🇧🇩 বাংলা" if lang == "bn" else "🇺🇸 English"}
• কান্ট্রি: {country}

**📊 টোটাল চেক:** {checker.stats['total']}
✅ **অ্যাপ্রুভ:** {checker.stats['approved']}
❌ **ডিক্লাইন:** {checker.stats['declined']}

নিচের বাটন থেকে অপশন সিলেক্ট করুন 👇
            """ if lang == "bn" else f"""
🌟 **Shopify Card Checker Bot** 🌟

👋 **Welcome** {user.first_name}!

**🔍 Features:**
• 100% Real Shopify API Check
• Shopify, Stripe Gateway Detection
• BIN, Card Type, Country Info
• 10,000+ Card Support

**📊 Current Settings:**
• Language: {"🇧🇩 বাংলা" if lang == "bn" else "🇺🇸 English"}
• Country: {country}

**📊 Total Checked:** {checker.stats['total']}
✅ **Approved:** {checker.stats['approved']}
❌ **Declined:** {checker.stats['declined']}

Select option from buttons below 👇
            """
        )
        
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
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Button callback handler"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Admin actions
        if query.data.startswith("approve_"):
            target_id = int(query.data.replace("approve_", ""))
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
        
        if query.data.startswith("reject_"):
            target_id = int(query.data.replace("reject_", ""))
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
        
        if query.data.startswith("block_"):
            target_id = int(query.data.replace("block_", ""))
            if db.is_admin(user_id):
                db.block_user(target_id)
                await query.edit_message_text(
                    f"🚫 User `{target_id}` Blocked!",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Check access for other actions
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await query.edit_message_text(
                "⛔ Access Denied! Please /start first.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        
        # Handle normal buttons
        if query.data == "check_card":
            msg = (
                "📝 **কার্ড ইনপুট দিন:**\n\n"
                "**ফরম্যাট:** `4111111111111111|12|2026|123`\n"
                "**সাপোর্টেড সেপারেটর:** | : , ; space\n\n"
                "• সিঙ্গেল কার্ড পাঠান\n"
                "• একাধিক কার্ড লাইন বাই লাইন দিন\n"
                "• ১০০+ কার্ডের জন্য ফাইল ব্যবহার করুন\n\n"
                "এখন কার্ড পাঠান ⬇️"
            ) if lang == "bn" else (
                "📝 **Enter Card Details:**\n\n"
                "**Format:** `4111111111111111|12|2026|123`\n"
                "**Supported separators:** | : , ; space\n\n"
                "• Send single card\n"
                "• Multiple cards line by line\n"
                "• Use file for 100+ cards\n\n"
                "Send cards now ⬇️"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "upload_file":
            msg = (
                "📤 **ফাইল আপলোড:**\n\n"
                "• .txt ফাইল মাত্র\n"
                "• প্রতি লাইনে ১টি কার্ড\n"
                "• সর্বোচ্চ ১০,০০০ কার্ড\n"
                "• ফরম্যাট: `number|mm|yyyy|cvv`\n\n"
                "এখন .txt ফাইল আপলোড করুন 📎"
            ) if lang == "bn" else (
                "📤 **File Upload:**\n\n"
                "• .txt files only\n"
                "• 1 card per line\n"
                "• Maximum 10,000 cards\n"
                "• Format: `number|mm|yyyy|cvv`\n\n"
                "Upload .txt file now 📎"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "stats":
            stats = checker.stats
            total = stats["total"]
            approved = stats["approved"]
            declined = stats["declined"]
            rate = (approved / total * 100) if total > 0 else 0
            
            stats_msg = (
                f"""
📊 **চেকিং স্ট্যাটাস**

🔄 টোটাল: `{total}`
✅ অ্যাপ্রুভ: `{approved}`
❌ ডিক্লাইন: `{declined}`
📈 সাফল্য: `{rate:.1f}%`

💚 লাইভ: `{stats['live']}`
💀 ডাই: `{stats['die']}`
                """
            ) if lang == "bn" else (
                f"""
📊 **Checking Status**

🔄 Total: `{total}`
✅ Approved: `{approved}`
❌ Declined: `{declined}`
📈 Success: `{rate:.1f}%`

💚 Live: `{stats['live']}`
💀 Die: `{stats['die']}`
                """
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                stats_msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "change_country":
            # Show country list
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
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
            
            await query.edit_message_text(
                "🌐 **Select Country:**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data.startswith("country_"):
            country = query.data.replace("country_", "")
            settings["country"] = country
            await query.answer(f"Country: {country}")
            await self.back_to_start(query)
        
        elif query.data == "change_lang":
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn"),
                    InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                "🗣 **Select Language:**",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data.startswith("lang_"):
            lang = query.data.replace("lang_", "")
            settings["language"] = lang
            await query.answer(f"Language: {'বাংলা' if lang == 'bn' else 'English'}")
            await self.back_to_start(query)
        
        elif query.data == "help":
            help_msg = (
                f"""
ℹ️ **হেল্প**

**কার্ড ফরম্যাট:**
`4111111111111111|12|2026|123`

**রেজাল্ট:**
✅ APPROVED = কার্ড কাজ করে
❌ DECLINED = কার্ড রিজেক্ট

**ফাইল:** .txt, ১০০০০ কার্ড

**কন্টাক্ট:** {OWNER_USERNAME}
                """
            ) if lang == "bn" else (
                f"""
ℹ️ **Help**

**Card Format:**
`4111111111111111|12|2026|123`

**Results:**
✅ APPROVED = Card works
❌ DECLINED = Card rejected

**File:** .txt, 10000 cards

**Contact:** {OWNER_USERNAME}
                """
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                help_msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data == "back_to_start":
            await self.back_to_start(query)
    
    async def back_to_start(self, query):
        """Return to main menu"""
        user_id = query.from_user.id
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        msg = (
            "🔄 **মেন মেনু**\nনিচের বাটন থেকে অপশন সিলেক্ট করুন"
        ) if lang == "bn" else (
            "🔄 **Main Menu**\nSelect option from buttons below"
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
    
    async def handle_card_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle card text input"""
        user_id = update.effective_user.id
        
        # Check access
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        text = update.message.text.strip()
        cards = [line.strip() for line in text.split('\n') if line.strip()]
        
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
        
        # Processing message
        processing_msg = await update.message.reply_text(
            f"⏳ **{len(cards)}টি কার্ড চেক হচ্ছে...**\n"
            f"🌐 কান্ট্রি: {country}\n"
            f"⏱️ আনুমানিক সময়: {len(cards) * CHECK_DELAY}s\n\n"
            f"🔄 Shopify API রিয়েল চেক..." if lang == "bn" else
            f"⏳ **Checking {len(cards)} cards...**\n"
            f"🌐 Country: {country}\n"
            f"⏱️ Estimated: {len(cards) * CHECK_DELAY}s\n\n"
            f"🔄 Real Shopify API check...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            results = await checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.update_progress(
                    processing_msg, c, t, card, lang
                )
            )
            
            # Format results
            result_text = self.format_results(results, lang)
            
            await processing_msg.delete()
            
            # Send results
            if len(result_text) > 4000:
                filename = f"shopify_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"✅ Check Complete! {len(results)} cards\n"
                               f"💚 Live: {checker.stats['live']} | 💀 Die: {checker.stats['die']}"
                    )
                
                os.remove(filename)
            else:
                await update.message.reply_text(
                    result_text,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        except Exception as e:
            logger.error(f"Card check error: {e}")
            await processing_msg.edit_text(
                f"❌ এরর: {str(e)[:200]}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def update_progress(self, msg, current: int, total: int, card: str, lang: str):
        """Update progress"""
        if current % 5 == 0 or current == total:
            percent = int(current / total * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            
            text = (
                f"⏳ **চেকিং:** {current}/{total}\n"
                f"📊 [{bar}] {percent}%\n"
                f"🔍 `{card}`\n"
                f"🌐 Shopify API রিয়েল চেক..."
            ) if lang == "bn" else (
                f"⏳ **Checking:** {current}/{total}\n"
                f"📊 [{bar}] {percent}%\n"
                f"🔍 `{card}`\n"
                f"🌐 Real Shopify API check..."
            )
            
            try:
                await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
            except:
                pass
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file upload"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id) and not db.is_approved(user_id):
            await self.send_access_request(update)
            return
        
        document = update.message.document
        
        if not document.file_name.endswith('.txt'):
            await update.message.reply_text(
                "❌ শুধু .txt ফাইল / Only .txt files!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if document.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ ফাইল 5MB এর বেশি / File too large!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        settings = self.get_settings(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        progress_msg = await update.message.reply_text(
            "📥 ফাইল ডাউনলোড হচ্ছে... / Downloading...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            content = file_bytes.decode('utf-8')
            
            cards = [line.strip() for line in content.split('\n') if line.strip()]
            
            if len(cards) > MAX_FILE_CARDS:
                cards = cards[:MAX_FILE_CARDS]
            
            await progress_msg.edit_text(
                f"⏳ {len(cards)}টি কার্ড চেক হচ্ছে...\n"
                f"⏱️ আনুমানিক সময়: {len(cards) * CHECK_DELAY // 60} মিনিট" if lang == "bn" else
                f"⏳ Checking {len(cards)} cards...\n"
                f"⏱️ Estimated: {len(cards) * CHECK_DELAY // 60} min",
                parse_mode=ParseMode.MARKDOWN
            )
            
            results = await checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.update_progress(
                    progress_msg, c, t, card, lang
                )
            )
            
            result_text = self.format_results(results, lang)
            
            filename = f"shopify_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result_text)
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=(
                        f"✅ চেক সম্পন্ন! {len(results)} কার্ড\n"
                        f"💚 লাইভ: {checker.stats['live']} | 💀 ডাই: {checker.stats['die']}"
                    ) if lang == "bn" else (
                        f"✅ Complete! {len(results)} cards\n"
                        f"💚 Live: {checker.stats['live']} | 💀 Die: {checker.stats['die']}"
                    )
                )
            
            os.remove(filename)
            await progress_msg.delete()
            
        except Exception as e:
            logger.error(f"File error: {e}")
            await progress_msg.edit_text(
                f"❌ Error: {str(e)[:200]}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def format_results(self, results: list, lang: str) -> str:
        """Format results for output"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = len(results)
        
        approved = [r for r in results if r["status"] == "APPROVED"]
        declined = [r for r in results if r["status"] == "DECLINED"]
        others = [r for r in results if r["status"] not in ("APPROVED", "DECLINED")]
        
        output = f"""
╔══════════════════════════════════════════╗
║     SHOPIFY CARD CHECK RESULTS         ║
╚══════════════════════════════════════════╝

📅 **Date:** {now}
📊 **Total:** {total}
✅ **APPROVED:** {len(approved)}
❌ **DECLINED:** {len(declined)}
⚠️ **Other:** {len(others)}

{'═' * 50}
"""
        
        if approved:
            output += "\n✅ **APPROVED/LIVE CARDS:**\n" + "─" * 45 + "\n"
            for r in approved:
                output += f"""
🔹 **Card:** `{r['card']}`
   ├─ BIN: `{r['bin']}`
   ├─ Type: {r['card_type']}
   ├─ Gateway: {r['gateway']}
   ├─ Country: {r['country']}
   ├─ Time: {r['response_time']}
   └─ Status: {r['message']}
"""
        
        if declined:
            output += "\n❌ **DECLINED/DIE CARDS:**\n" + "─" * 45 + "\n"
            for r in declined:
                output += f"""
🔸 **Card:** `{r['card']}`
   ├─ BIN: `{r['bin']}`
   ├─ Type: {r['card_type']}
   ├─ Gateway: {r['gateway']}
   └─ Status: {r['message']}
"""
        
        if others:
            output += "\n⚠️ **ERRORS/UNKNOWN:**\n" + "─" * 45 + "\n"
            for r in others:
                output += f"▪️ `{r['card']}` - {r['message']}\n"
        
        output += f"""
{'═' * 50}
📊 **Summary:** {len(approved)} LIVE | {len(declined)} DIE | {total} TOTAL
🤖 Bot: {BOT_USERNAME}
👤 Owner: {OWNER_USERNAME}
"""
        
        return output
    
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
            
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        
        elif cmd == "/approve":
            if len(command) > 1:
                target = int(command[1])
                db.approve_user(target, user_id)
                await update.message.reply_text(f"✅ User `{target}` approved!")
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
                await update.message.reply_text(f"🚫 User `{target}` blocked!")
    
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
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_card_input))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file))
        
        logger.info("🤖 Bot started with user management system!")
        print("✅ Bot is running...")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = ShopifyCardBot()
    bot.run()