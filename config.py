import os

# ==================== বট কনফিগ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8989854278:AAFCjZMd7x4W7OfjHh_1mI8x_TgO2pQb1WE")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@thispersonisbrandcardchecker_bot")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@thispersonisbrand537")

# ==================== অ্যাডমিন আইডি ====================
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "1978055060,5994477331").split(",")]
INITIAL_ADMINS = ADMIN_IDS  # প্রথমবারের জন্য

# ==================== Shopify চেকিং কনফিগ ====================
CHECK_DELAY = int(os.getenv("CHECK_DELAY", "3"))  # প্রতি কার্ডের মাঝে delay (seconds)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))  # একবারে কত কার্ড
MAX_FILE_CARDS = int(os.getenv("MAX_FILE_CARDS", "10000"))  # ফাইলে সর্বোচ্চ কার্ড
MAX_CARD_CHECK = int(os.getenv("MAX_CARD_CHECK", "10000"))  # টোটাল চেক লিমিট

# ==================== Shopify API URLs ====================
SHOPIFY_URLS = {
    "signup": "https://www.shopify.com/signup",
    "free_trial": "https://www.shopify.com/free-trial",
    "api_signup": "https://www.shopify.com/api/signup",
    "api_trial": "https://www.shopify.com/api/signup/trial",
    "validate_card": "https://www.shopify.com/payments/validate",
    "checkout_api": "https://www.shopify.com/checkout/validate",
    "store_create": "https://www.shopify.com/store/create",
    "payment_verify": "https://www.shopify.com/api/payments/verify"
}

# ==================== Stripe API (Shopify uses Stripe) ====================
STRIPE_API = "https://api.stripe.com/v1"
STRIPE_PUBLIC_KEY = "pk_live_51H3Y2kCZqK8FwQqSY4K8VQqSZCqK8FwQqSY4K8VQqS"  # Shopify's Stripe public key

# ==================== BIN Lookup API ====================
BIN_API = "https://lookup.binlist.net"
BIN_API_ALT = "https://binlist.io/json"

# ==================== ইউজার এজেন্ট লিস্ট ====================
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
]

# ==================== কান্ট্রি লিস্ট ====================
COUNTRIES = {
    "US": {
        "name": "United States 🇺🇸",
        "zip": "10001",
        "state": "NY",
        "city": "New York",
        "phone_code": "+1"
    },
    "GB": {
        "name": "United Kingdom 🇬🇧",
        "zip": "SW1A 1AA",
        "state": "London",
        "city": "London",
        "phone_code": "+44"
    },
    "CA": {
        "name": "Canada 🇨🇦",
        "zip": "M5V 2T6",
        "state": "ON",
        "city": "Toronto",
        "phone_code": "+1"
    },
    "AU": {
        "name": "Australia 🇦🇺",
        "zip": "2000",
        "state": "NSW",
        "city": "Sydney",
        "phone_code": "+61"
    },
    "DE": {
        "name": "Germany 🇩🇪",
        "zip": "10115",
        "state": "Berlin",
        "city": "Berlin",
        "phone_code": "+49"
    },
    "FR": {
        "name": "France 🇫🇷",
        "zip": "75001",
        "state": "Paris",
        "city": "Paris",
        "phone_code": "+33"
    },
    "IT": {
        "name": "Italy 🇮🇹",
        "zip": "00100",
        "state": "RM",
        "city": "Rome",
        "phone_code": "+39"
    },
    "ES": {
        "name": "Spain 🇪🇸",
        "zip": "28001",
        "state": "Madrid",
        "city": "Madrid",
        "phone_code": "+34"
    },
    "NL": {
        "name": "Netherlands 🇳🇱",
        "zip": "1012",
        "state": "Amsterdam",
        "city": "Amsterdam",
        "phone_code": "+31"
    },
    "JP": {
        "name": "Japan 🇯🇵",
        "zip": "100-0001",
        "state": "Tokyo",
        "city": "Tokyo",
        "phone_code": "+81"
    },
    "BR": {
        "name": "Brazil 🇧🇷",
        "zip": "01001-000",
        "state": "SP",
        "city": "Sao Paulo",
        "phone_code": "+55"
    },
    "IN": {
        "name": "India 🇮🇳",
        "zip": "110001",
        "state": "Delhi",
        "city": "New Delhi",
        "phone_code": "+91"
    },
    "AE": {
        "name": "UAE 🇦🇪",
        "zip": "00000",
        "state": "Dubai",
        "city": "Dubai",
        "phone_code": "+971"
    },
    "SG": {
        "name": "Singapore 🇸🇬",
        "zip": "018989",
        "state": "Singapore",
        "city": "Singapore",
        "phone_code": "+65"
    },
    "HK": {
        "name": "Hong Kong 🇭🇰",
        "zip": "999077",
        "state": "Hong Kong",
        "city": "Hong Kong",
        "phone_code": "+852"
    },
    "KR": {
        "name": "South Korea 🇰🇷",
        "zip": "04524",
        "state": "Seoul",
        "city": "Seoul",
        "phone_code": "+82"
    },
    "TR": {
        "name": "Turkey 🇹🇷",
        "zip": "34000",
        "state": "Istanbul",
        "city": "Istanbul",
        "phone_code": "+90"
    },
    "SA": {
        "name": "Saudi Arabia 🇸🇦",
        "zip": "11564",
        "state": "Riyadh",
        "city": "Riyadh",
        "phone_code": "+966"
    },
    "MX": {
        "name": "Mexico 🇲🇽",
        "zip": "06600",
        "state": "CDMX",
        "city": "Mexico City",
        "phone_code": "+52"
    },
    "MY": {
        "name": "Malaysia 🇲🇾",
        "zip": "50000",
        "state": "Kuala Lumpur",
        "city": "Kuala Lumpur",
        "phone_code": "+60"
    }
}

# ==================== কার্ড টাইপ ====================
CARD_TYPES = {
    "4": "Visa",
    "51": "Mastercard",
    "52": "Mastercard",
    "53": "Mastercard",
    "54": "Mastercard",
    "55": "Mastercard",
    "2221": "Mastercard",
    "2720": "Mastercard",
    "34": "Amex",
    "37": "Amex",
    "6011": "Discover",
    "65": "Discover",
    "644": "Discover",
    "36": "Diners Club",
    "300": "Diners Club",
    "301": "Diners Club",
    "302": "Diners Club",
    "303": "Diners Club",
    "304": "Diners Club",
    "305": "Diners Club",
    "35": "JCB",
    "2131": "JCB",
    "1800": "JCB",
    "62": "UnionPay",
    "50": "Maestro",
    "56": "Maestro",
    "57": "Maestro",
    "58": "Maestro",
    "63": "Maestro",
    "67": "Maestro"
}

# ==================== Shopify Error Messages ====================
SHOPIFY_ERRORS = {
    "card_declined": "Card declined",
    "insufficient_funds": "Insufficient funds",
    "invalid_card": "Invalid card number",
    "expired_card": "Card expired",
    "incorrect_cvc": "Incorrect CVC",
    "processing_error": "Processing error",
    "fraudulent": "Fraud suspected",
    "stolen_card": "Card reported stolen",
    "lost_card": "Card reported lost",
    "test_card": "Test card not allowed",
    "restricted_card": "Card restricted",
    "velocity_exceeded": "Too many attempts"
}

# ==================== Stripe Error Codes ====================
STRIPE_ERRORS = {
    "card_declined": "❌ DECLINED",
    "incorrect_number": "❌ Invalid card number",
    "invalid_number": "❌ Invalid card number",
    "invalid_expiry_month": "❌ Invalid expiry month",
    "invalid_expiry_year": "❌ Invalid expiry year",
    "invalid_cvc": "❌ Invalid CVC",
    "expired_card": "❌ Card expired",
    "incorrect_cvc": "❌ Incorrect CVC",
    "incorrect_zip": "⚠️ Incorrect ZIP (Card may be valid)",
    "card_decline_rate_limit_exceeded": "❌ Too many attempts - Declined",
    "processing_error": "⚠️ Processing error - Try again"
}
