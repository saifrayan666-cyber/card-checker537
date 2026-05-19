import os

# ==================== বট কনফিগ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8989854278:AAFCjZMd7x4W7OfjHh_1mI8x_TgO2pQb1WE")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@thispersonisbrandcardchecker_bot")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "1978055060,5994477331")

# ==================== অ্যাডমিন ====================
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "123456789").split(",")]
INITIAL_ADMINS = ADMIN_IDS

# ==================== চেকিং কনফিগ ====================
CHECK_DELAY = int(os.getenv("CHECK_DELAY", "3"))
MAX_FILE_CARDS = int(os.getenv("MAX_FILE_CARDS", "10000"))
MAX_CONCURRENT_USERS = 25

# ==================== গেটওয়ে ====================
GATEWAYS = {
    "stripe": {
        "name": "💳 Stripe (Real Check)",
        "description": "Real card validation via Stripe"
    },
    "shopify": {
        "name": "🛒 Shopify (Real Check)",
        "description": "Real Shopify store creation check"
    },
    "braintree": {
        "name": "🅱️ Braintree (Real Check)",
        "description": "Real Braintree payment validation"
    }
}

# ==================== API ====================
STRIPE_API = "https://api.stripe.com/v1"
STRIPE_PUBLIC_KEY = "pk_live_51H3Y2kCZqK8FwQqSY4K8VQqSZCqK8FwQqSY4K8VQqS"
BRAINTREE_API = "https://payments.braintree-api.com/graphql"
BRAINTREE_PUBLIC_KEY = "sandbox_8h2v3m8n_6x5y4z3w2q"
BIN_API = "https://lookup.binlist.net"

# ==================== ইউজার এজেন্ট ====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
]

# ==================== কান্ট্রি ====================
COUNTRIES = {
    "US": {"name": "🇺🇸 United States", "zip": "10001", "state": "NY", "city": "New York"},
    "GB": {"name": "🇬🇧 United Kingdom", "zip": "SW1A 1AA", "state": "London", "city": "London"},
    "CA": {"name": "🇨🇦 Canada", "zip": "M5V 2T6", "state": "ON", "city": "Toronto"},
    "AU": {"name": "🇦🇺 Australia", "zip": "2000", "state": "NSW", "city": "Sydney"},
    "DE": {"name": "🇩🇪 Germany", "zip": "10115", "state": "Berlin", "city": "Berlin"},
    "FR": {"name": "🇫🇷 France", "zip": "75001", "state": "Paris", "city": "Paris"},
    "IT": {"name": "🇮🇹 Italy", "zip": "00100", "state": "RM", "city": "Rome"},
    "ES": {"name": "🇪🇸 Spain", "zip": "28001", "state": "Madrid", "city": "Madrid"},
    "NL": {"name": "🇳🇱 Netherlands", "zip": "1012", "state": "Amsterdam", "city": "Amsterdam"},
    "JP": {"name": "🇯🇵 Japan", "zip": "100-0001", "state": "Tokyo", "city": "Tokyo"},
    "BR": {"name": "🇧🇷 Brazil", "zip": "01001-000", "state": "SP", "city": "Sao Paulo"},
    "IN": {"name": "🇮🇳 India", "zip": "110001", "state": "Delhi", "city": "New Delhi"},
    "AE": {"name": "🇦🇪 UAE", "zip": "00000", "state": "Dubai", "city": "Dubai"},
    "SG": {"name": "🇸🇬 Singapore", "zip": "018989", "state": "Singapore", "city": "Singapore"}
}
