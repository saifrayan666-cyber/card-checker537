#!/usr/bin/env python3
"""
Shopify Card Checker Bot
100% Real Shopify API Check
Supports 10,000+ cards, multi-language, real gateway detection
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

from config import *
from checker import ShopifyChecker

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

class CardCheckerBot:
    """Telegram Bot for Shopify Card Checking"""
    
    def __init__(self):
        self.checker = ShopifyChecker()
        self.user_settings: Dict[int, Dict] = {}  # User settings (language, country)
        self.active_checks: Dict[int, bool] = {}  # Active check status
        
    def get_user_setting(self, user_id: int) -> Dict:
        """Get or create user settings"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                "language": "bn",  # Default Bengali
                "country": "US",   # Default United States
                "auto_check": True
            }
        return self.user_settings[user_id]
    
    def get_text(self, user_id: int, bn_text: str, en_text: str) -> str:
        """Get text based on user language"""
        lang = self.get_user_setting(user_id)["language"]
        return bn_text if lang == "bn" else en_text
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        user_id = user.id
        
        # Admin check
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(
                "⛔ **Access Denied**\n\n"
                "❌ আপনি এই বট ব্যবহারের অনুমোদিত নন।\n"
                "❌ You are not authorized to use this bot.\n\n"
                "📞 Contact admin for access."
            )
            return
        
        settings = self.get_user_setting(user_id)
        lang = settings["language"]
        country = settings["country"]
        country_name = COUNTRIES.get(country, COUNTRIES["US"])["name"]
        
        # Welcome message in both languages
        welcome_bn = f"""
🌟 **Shopify Card Checker Bot** 🌟

👋 **স্বাগতম** {user.first_name}!

**🔍 এই বট যা করে:**
• ১০০% রিয়েল Shopify API চেক
• Shopify, Stripe গেটওয়ে ডিটেকশন
• ১০,০০০+ কার্ড চেক সাপোর্ট
• BIN, কার্ড টাইপ, কান্ট্রি ডিটেকশন
• লাইভ/ডাই স্ট্যাটাস

**📊 বর্তমান সেটিংস:**
• ভাষা: {"🇧🇩 বাংলা" if lang == "bn" else "🇺🇸 English"}
• কান্ট্রি: {country_name}

**⚙️ সেটিংস পরিবর্তন করতে নিচের বাটন ব্যবহার করুন**

**🔄 এখনই কার্ড চেক করতে নিচের বাটনে ক্লিক করুন**
        """
        
        welcome_en = f"""
🌟 **Shopify Card Checker Bot** 🌟

👋 **Welcome** {user.first_name}!

**🔍 What this bot does:**
• 100% Real Shopify API Check
• Shopify, Stripe Gateway Detection
• 10,000+ Card Support
• BIN, Card Type, Country Detection
• Live/Die Status

**📊 Current Settings:**
• Language: {"🇧🇩 বাংলা" if lang == "bn" else "🇺🇸 English"}
• Country: {country_name}

**⚙️ Use buttons below to change settings**

**🔄 Click below to start checking cards**
        """
        
        welcome = welcome_bn if lang == "bn" else welcome_en
        
        # Buttons below the message
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔍 চেক কার্ড / Check Card",
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
        """Handle all button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ Unauthorized!")
            return
        
        data = query.data
        settings = self.get_user_setting(user_id)
        
        if data == "check_card":
            lang = settings["language"]
            msg = (
                "📝 **কার্ড ইনপুট দিন:**\n\n"
                "**ফরম্যাট:** `4111111111111111|12|2026|123`\n"
                "**সাপোর্টেড সেপারেটর:** | : , ; space\n\n"
                "• সিঙ্গেল কার্ড পাঠান\n"
                "• একাধিক কার্ড লাইন বাই লাইন দিন\n"
                "• ১০০+ কার্ডের জন্য ফাইল ব্যবহার করুন\n\n"
                "এখন কার্ড পাঠান ⬇️"
            ) if lang == "bn" else (
                "📝 **Enter card details:**\n\n"
                "**Format:** `4111111111111111|12|2026|123`\n"
                "**Supported separators:** | : , ; space\n\n"
                "• Send single card\n"
                "• Multiple cards line by line\n"
                "• Use file for 100+ cards\n\n"
                "Send cards now ⬇️"
            )
            
            back_button = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 ব্যাক / Back",
                    callback_data="back_to_start"
                )]
            ])
            
            await query.edit_message_text(
                msg,
                reply_markup=back_button,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == "upload_file":
            lang = settings["language"]
            msg = (
                "📤 **ফাইল আপলোড নির্দেশিকা:**\n\n"
                "• .txt ফাইল মাত্র\n"
                "• প্রতি লাইনে ১টি কার্ড\n"
                "• সর্বোচ্চ ১০,০০০ কার্ড\n"
                "• ফরম্যাট: `number|mm|yyyy|cvv`\n\n"
                "এখন .txt ফাইল আপলোড করুন 📎"
            ) if lang == "bn" else (
                "📤 **File Upload Guide:**\n\n"
                "• .txt files only\n"
                "• 1 card per line\n"
                "• Maximum 10,000 cards\n"
                "• Format: `number|mm|yyyy|cvv`\n\n"
                "Upload .txt file now 📎"
            )
            
            back_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                msg,
                reply_markup=back_button,
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == "stats":
            await self.show_stats(query)
        
        elif data == "change_country":
            await self.show_country_selection(query)
        
        elif data.startswith("country_"):
            country = data.replace("country_", "")
            settings["country"] = country
            await query.answer(f"Country changed to {country}")
            await self.back_to_start(query)
        
        elif data == "change_lang":
            await self.show_language_selection(query)
        
        elif data.startswith("lang_"):
            lang = data.replace("lang_", "")
            settings["language"] = lang
            await query.answer(
                f"Language changed to {'বাংলা' if lang == 'bn' else 'English'}"
            )
            await self.back_to_start(query)
        
        elif data == "help":
            await self.show_help(query)
        
        elif data == "back_to_start":
            await self.back_to_start(query)
    
    async def back_to_start(self, query):
        """Return to start menu"""
        user_id = query.from_user.id
        settings = self.get_user_setting(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        msg = (
            "🔄 **মেন মেনুতে ফিরে এসেছেন**\n"
            "নিচের বাটন থেকে অপশন সিলেক্ট করুন"
        ) if lang == "bn" else (
            "🔄 **Back to Main Menu**\n"
            "Select option from buttons below"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 চেক কার্ড / Check", callback_data="check_card"),
                InlineKeyboardButton("📤 আপলোড / Upload", callback_data="upload_file")
            ],
            [
                InlineKeyboardButton("📊 স্ট্যাটাস / Stats", callback_data="stats"),
                InlineKeyboardButton("🌐 কান্ট্রি: " + country, callback_data="change_country")
            ],
            [
                InlineKeyboardButton("🗣 ভাষা / Language", callback_data="change_lang"),
                InlineKeyboardButton("ℹ️ হেল্প / Help", callback_data="help")
            ]
        ])
        
        await query.edit_message_text(
            msg,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_stats(self, query):
        """Show checking statistics"""
        user_id = query.from_user.id
        lang = self.get_user_setting(user_id)["language"]
        stats = self.checker.stats
        
        total = stats["total"]
        approved = stats["approved"]
        declined = stats["declined"]
        errors = stats["errors"]
        live = stats["live"]
        die = stats["die"]
        
        success_rate = (approved / total * 100) if total > 0 else 0
        
        stats_bn = f"""
📊 **চেকিং স্ট্যাটাস**

🔄 **টোটাল চেক:** `{total}`
✅ **অ্যাপ্রুভ/লাইভ:** `{approved}`
❌ **ডিক্লাইন/ডাই:** `{declined}`
⚠️ **এরর:** `{errors}`

📈 **সাফল্যের হার:** `{success_rate:.1f}%`
💚 **লাইভ কার্ড:** `{live}`
💀 **ডাই কার্ড:** `{die}`

🔍 **গেটওয়ে:** Shopify API + Stripe
⏱️ **ডিলে:** {CHECK_DELAY}s/কার্ড
        """
        
        stats_en = f"""
📊 **Checking Status**

🔄 **Total Checked:** `{total}`
✅ **Approved/Live:** `{approved}`
❌ **Declined/Die:** `{declined}`
⚠️ **Errors:** `{errors}`

📈 **Success Rate:** `{success_rate:.1f}%`
💚 **Live Cards:** `{live}`
💀 **Die Cards:** `{die}`

🔍 **Gateway:** Shopify API + Stripe
⏱️ **Delay:** {CHECK_DELAY}s/card
        """
        
        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 রিফ্রেশ / Refresh", callback_data="stats")],
            [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
        ])
        
        await query.edit_message_text(
            stats_bn if lang == "bn" else stats_en,
            reply_markup=back_button,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_country_selection(self, query):
        """Show country selection menu"""
        keyboard = []
        row = []
        
        for code, info in COUNTRIES.items():
            button = InlineKeyboardButton(
                f"{info['name']} ({code})",
                callback_data=f"country_{code}"
            )
            row.append(button)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")
        ])
        
        await query.edit_message_text(
            "🌐 **দেশ সিলেক্ট করুন / Select Country:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_language_selection(self, query):
        """Show language selection"""
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
    
    async def show_help(self, query):
        """Show help message"""
        user_id = query.from_user.id
        lang = self.get_user_setting(user_id)["language"]
        
        help_bn = """
ℹ️ **হেল্প ও তথ্য**

**বট সম্পর্কে:**
এই বট Shopify-এর রিয়েল API ব্যবহার করে কার্ড চেক করে।

**কার্ড ফরম্যাট:**
`4111111111111111|12|2026|123`
`number|month|year|cvv`

**রেজাল্ট বুঝবেন কিভাবে:**
✅ **APPROVED** = কার্ড কাজ করে
❌ **DECLINED** = কার্ড রিজেক্ট
⚠️ **UNKNOWN** = ম্যানুয়াল চেক প্রয়োজন

**ফাইল চেকিং:**
• .txt ফাইল মাত্র
• সর্বোচ্চ ১০,০০০ কার্ড
• প্রতি লাইনে ১টি কার্ড

**গেটওয়ে:**
• Shopify Payments
• Stripe
• Shopify Checkout

**স্পিড:**
• {CHECK_DELAY}s/কার্ড (রিয়েল চেক)

**সাপোর্ট:** @YourUsername
        """.format(CHECK_DELAY=CHECK_DELAY)
        
        help_en = """
ℹ️ **Help & Information**

**About Bot:**
This bot checks cards using Shopify's REAL API.

**Card Format:**
`4111111111111111|12|2026|123`
`number|month|year|cvv`

**Understanding Results:**
✅ **APPROVED** = Card works
❌ **DECLINED** = Card rejected
⚠️ **UNKNOWN** = Manual check needed

**File Checking:**
• .txt files only
• Maximum 10,000 cards
• 1 card per line

**Gateway:**
• Shopify Payments
• Stripe
• Shopify Checkout

**Speed:**
• {CHECK_DELAY}s/card (real check)

**Support:** @YourUsername
        """.format(CHECK_DELAY=CHECK_DELAY)
        
        back_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ব্যাক / Back", callback_data="back_to_start")]
        ])
        
        await query.edit_message_text(
            help_bn if lang == "bn" else help_en,
            reply_markup=back_button,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_card_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle card text input"""
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
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
        
        settings = self.get_user_setting(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        # Processing message
        processing_msg = await update.message.reply_text(
            f"⏳ {len(cards)}টি কার্ড চেক হচ্ছে...\n"
            f"🌐 কান্ট্রি: {country}\n"
            f"⏱️ আনুমানিক সময়: {len(cards) * CHECK_DELAY}s\n\n"
            f"🔄 ১০০% রিয়েল Shopify API চেক..." if lang == "bn" else
            f"⏳ Checking {len(cards)} cards...\n"
            f"🌐 Country: {country}\n"
            f"⏱️ Estimated time: {len(cards) * CHECK_DELAY}s\n\n"
            f"🔄 100% Real Shopify API Check...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Real checking
            results = await self.checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.update_progress(
                    processing_msg, c, t, card, lang
                )
            )
            
            # Format results
            result_text = self.format_results(results, lang, country)
            
            await processing_msg.delete()
            
            # Send results
            if len(result_text) > 4000:
                # Save as file
                filename = f"shopify_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"✅ Check Completed! {len(results)} cards"
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
        """Update progress message"""
        if current % 5 == 0 or current == total:
            percent = int(current / total * 100)
            progress_bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            
            text = (
                f"⏳ **চেকিং:** {current}/{total}\n"
                f"📊 [{progress_bar}] {percent}%\n"
                f"🔍 `{card}`\n"
                f"🌐 Shopify API রিয়েল চেক..."
            ) if lang == "bn" else (
                f"⏳ **Checking:** {current}/{total}\n"
                f"📊 [{progress_bar}] {percent}%\n"
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
        if user_id not in ADMIN_IDS:
            return
        
        document = update.message.document
        
        # Validate file type
        if not document.file_name.endswith('.txt'):
            await update.message.reply_text(
                "❌ শুধু .txt ফাইল / Only .txt files allowed!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check file size (max 5MB)
        if document.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ ফাইল 5MB এর বেশি / File too large (max 5MB)!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        settings = self.get_user_setting(user_id)
        lang = settings["language"]
        country = settings["country"]
        
        progress_msg = await update.message.reply_text(
            "📥 ফাইল ডাউনলোড হচ্ছে... / Downloading file...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            content = file_bytes.decode('utf-8')
            
            # Parse cards
            cards = []
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    cards.append(line)
            
            # Limit to MAX_FILE_CARDS
            if len(cards) > MAX_FILE_CARDS:
                cards = cards[:MAX_FILE_CARDS]
            
            if not cards:
                await progress_msg.edit_text(
                    "❌ ফাইলে কোনো কার্ড পাওয়া যায়নি! / No cards found!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            await progress_msg.edit_text(
                f"⏳ {len(cards)}টি কার্ড চেক হচ্ছে ({country})...\n"
                f"⏱️ আনুমানিক সময়: {len(cards) * CHECK_DELAY // 60} মিনিট\n\n"
                f"🔄 ১০০% রিয়েল Shopify API চেক..." if lang == "bn" else
                f"⏳ Checking {len(cards)} cards ({country})...\n"
                f"⏱️ Estimated time: {len(cards) * CHECK_DELAY // 60} minutes\n\n"
                f"🔄 100% Real Shopify API Check...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Process cards
            results = await self.checker.check_batch(
                cards,
                country=country,
                progress_callback=lambda c, t, card: self.update_progress(
                    progress_msg, c, t, card, lang
                )
            )
            
            # Format and save results
            result_text = self.format_results(results, lang, country)
            
            filename = f"shopify_full_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result_text)
            
            # Send file
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=(
                        f"✅ চেক সম্পন্ন! {len(results)} কার্ড\n"
                        f"💚 লাইভ: {self.checker.stats['live']} | 💀 ডাই: {self.checker.stats['die']}"
                    ) if lang == "bn" else (
                        f"✅ Check Complete! {len(results)} cards\n"
                        f"💚 Live: {self.checker.stats['live']} | 💀 Die: {self.checker.stats['die']}"
                    )
                )
            
            os.remove(filename)
            await progress_msg.delete()
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            await progress_msg.edit_text(
                f"❌ এরর: {str(e)[:200]}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def format_results(self, results: list, lang: str, country: str) -> str:
        """Format check results"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = len(results)
        
        approved = [r for r in results if r["status"] == "APPROVED"]
        declined = [r for r in results if r["status"] == "DECLINED"]
        others = [r for r in results if r["status"] not in ("APPROVED", "DECLINED")]
        
        if lang == "bn":
            output = f"""
╔════════════════════════════════════════╗
║     SHOPIFY CARD CHECK RESULTS       ║
╚════════════════════════════════════════╝

📅 **তারিখ:** {now}
🌐 **কান্ট্রি:** {country}
📊 **টোটাল:** {total}
✅ **অ্যাপ্রুভ:** {len(approved)}
❌ **ডিক্লাইন:** {len(declined)}
⚠️ **অন্যান্য:** {len(others)}

{'═' * 50}

"""
        else:
            output = f"""
╔════════════════════════════════════════╗
║     SHOPIFY CARD CHECK RESULTS       ║
╚════════════════════════════════════════╝

📅 **Date:** {now}
🌐 **Country:** {country}
📊 **Total:** {total}
✅ **Approved:** {len(approved)}
❌ **Declined:** {len(declined)}
⚠️ **Other:** {len(others)}

{'═' * 50}

"""
        
        # Approved cards
        if approved:
            output += "✅ **APPROVED/LIVE CARDS:**\n" + "─" * 40 + "\n"
            for r in approved:
                output += f"\n🔹 `{r['card']}`\n"
                output += f"   ├─ BIN: `{r.get('bin', 'N/A')}`\n"
                output += f"   ├─ Type: {r.get('card_type', 'Unknown')}\n"
                output += f"   ├─ Gateway: {r.get('gateway', 'N/A')}\n"
                output += f"   ├─ Country: {r.get('country', country)}\n"
                output += f"   ├─ Time: {r.get('response_time', 'N/A')}\n"
                output += f"   └─ Status: {r['message']}\n"
        
        # Declined cards
        if declined:
            output += "\n❌ **DECLINED/DIE CARDS:**\n" + "─" * 40 + "\n"
            for r in declined:
                output += f"\n🔸 `{r['card']}`\n"
                output += f"   ├─ BIN: `{r.get('bin', 'N/A')}`\n"
                output += f"   ├─ Type: {r.get('card_type', 'Unknown')}\n"
                output += f"   ├─ Gateway: {r.get('gateway', 'N/A')}\n"
                output += f"   └─ Status: {r['message']}\n"
        
        # Other/errors
        if others:
            output += "\n⚠️ **ERRORS/UNKNOWN:**\n" + "─" * 40 + "\n"
            for r in others:
                output += f"\n▪️ `{r['card']}` - {r['message']}\n"
        
        output += f"""
{'═' * 50}
📊 **সারাংশ:** {len(approved)} লাইভ | {len(declined)} ডাই | {total} টোটাল
🤖 @ShopifyCardCheckerBot
"""
        
        return output
    
    def run(self):
        """Run the bot"""
        # Validate configuration
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("BOT_TOKEN not configured!")
            print("❌ Please set BOT_TOKEN in config.py or environment variables")
            sys.exit(1)
        
        # Create bot application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_card_input
        ))
        application.add_handler(MessageHandler(
            filters.Document.ALL, self.handle_file
        ))
        
        # Graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Shutting down...")
            asyncio.create_task(self.checker.close())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("""
╔══════════════════════════════════════════╗
║   🤖 Shopify Card Checker Bot v2.0     ║
║   ✅ 100% Real API Check               ║
║   🌐 Multi-Gateway Detection           ║
║   📊 10,000+ Card Support              ║
║   🚀 Railway Ready                     ║
╚══════════════════════════════════════════╝
        """)
        
        print("✅ Bot is running... Press Ctrl+C to stop")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

# Main entry
if __name__ == "__main__":
    bot = CardCheckerBot()
    bot.run()