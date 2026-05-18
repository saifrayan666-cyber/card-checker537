import os
from typing import List

# বেসিক কনফিগ
BOT_TOKEN = os.getenv("BOT_TOKEN", "8989854278:AAFCjZMd7x4W7OfjHh_1mI8x_TgO2pQb1WE")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "1978055060", "5994477331").split(",")]

# Shopify চেকিং কনফিগ
CHECK_DELAY = int(os.getenv("CHECK_DELAY", "4"))  # প্রতিটি কার্ডের মাঝে delay (seconds)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))  # একবারে কত কার্ড প্রসেস হবে
MAX_FILE_CARDS = int(os.getenv("MAX_FILE_CARDS", "10000"))  # ফাইলে সর্বোচ্চ কার্ড
MAX_CARD_CHECK = int(os.getenv("MAX_CARD_CHECK", "10000"))  # টোটাল কত চেক করতে পারবে

# Shopify API URLs
SHOPIFY_URLS = {
    "signup": "https://www.shopify.com/signup",
    "api_signup": "https://www.shopify.com/api/signup",
    "api_trial": "https://www.shopify.com/api/signup/trial",
    "validate_card": "https://www.shopify.com/payments/validate",
    "checkout_api": "https://www.shopify.com/checkout/validate",
    "store_create": "https://accounts.shopify.com/store/create",
    "payment_verify": "https://www.shopify.com/api/payments/verify"
}

# ইউজার এজেন্ট লিস্ট
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
]

# কান্ট্রি লিস্ট
COUNTRIES = {
    "US": {"name": "United States", "zip_code": "10001", "state": "NY", "code": "US"},
    "GB": {"name": "United Kingdom", "zip_code": "SW1A 1AA", "state": "London", "code": "GB"},
    "CA": {"name": "Canada", "zip_code": "M5V 2T6", "state": "ON", "code": "CA"},
    "AU": {"name": "Australia", "zip_code": "2000", "state": "NSW", "code": "AU"},
    "DE": {"name": "Germany", "zip_code": "10115", "state": "Berlin", "code": "DE"},
    "FR": {"name": "France", "zip_code": "75001", "state": "Paris", "code": "FR"},
    "IT": {"name": "Italy", "zip_code": "00100", "state": "RM", "code": "IT"},
    "ES": {"name": "Spain", "zip_code": "28001", "state": "Madrid", "code": "ES"},
    "NL": {"name": "Netherlands", "zip_code": "1012", "state": "Amsterdam", "code": "NL"},
    "JP": {"name": "Japan", "zip_code": "100-0001", "state": "Tokyo", "code": "JP"}
}

# ভাষা কনফিগ
LANGUAGES = {
    "bn": {
        "name": "বাংলা",
        "welcome": "স্বাগতম",
        "checking": "চেক করা হচ্ছে",
        "approved": "অনুমোদিত",
        "declined": "প্রত্যাখ্যাত"
    },
    "en": {
        "name": "English",
        "welcome": "Welcome",
        "checking": "Checking",
        "approved": "Approved",
        "declined": "Declined"
    }
}