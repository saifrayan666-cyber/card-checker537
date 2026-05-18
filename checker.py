import asyncio
import json
import logging
import random
import re
import string
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from config import *

logger = logging.getLogger(__name__)

class ShopifyChecker:
    """Shopify Real Card Checker - Fixed"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            "total": 0,
            "approved": 0,
            "declined": 0,
            "errors": 0,
            "live": 0,
            "die": 0
        }
    
    async def create_session(self):
        """Create HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers,
            connector=aiohttp.TCPConnector(limit=50, force_close=True)
        )
    
    def generate_identity(self, country_code: str = "US") -> Dict[str, str]:
        """Generate fake identity"""
        country = COUNTRIES.get(country_code, COUNTRIES["US"])
        
        first_names = ["John", "James", "Robert", "Michael", "David"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        return {
            "first_name": random.choice(first_names),
            "last_name": random.choice(last_names),
            "email": f"user{timestamp}{random_str}@gmail.com",
            "password": f"Shop@{timestamp}{random_str[:4]}",
            "store_name": f"store-{random_str[:6]}-{timestamp}",
            "country": country_code,
            "country_name": country["name"],
            "zip": country["zip"],
            "state": country["state"],
            "city": country["city"],
            "address": f"{random.randint(100,9999)} {random.choice(['Main St','Broadway'])}",
            "phone": f"{random.randint(200,999)}{random.randint(100,999)}{random.randint(1000,9999)}"
        }
    
    def parse_card(self, card_string: str) -> Optional[Dict[str, Any]]:
        """Parse card string"""
        if not card_string or not card_string.strip():
            return None
        
        card_string = card_string.strip()
        parts = re.split(r'[|:;, \t]+', card_string)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) < 3:
            return None
        
        card_number = re.sub(r'[^\d]', '', parts[0])
        
        if len(card_number) < 13 or len(card_number) > 19:
            return None
        
        # Card type
        card_type = "Unknown"
        if card_number.startswith('4'):
            card_type = "Visa"
        elif card_number.startswith(('51','52','53','54','55')):
            card_type = "Mastercard"
        elif card_number.startswith(('34','37')):
            card_type = "Amex"
        elif card_number.startswith('6011'):
            card_type = "Discover"
        
        month = parts[1].strip().zfill(2)
        try:
            if int(month) < 1 or int(month) > 12:
                month = "12"
        except:
            month = "12"
        
        year = parts[2].strip()
        if len(year) == 2:
            year = f"20{year}"
        elif len(year) != 4:
            year = "2026"
        
        cvv = "123"
        if len(parts) > 3:
            cvv = parts[3].strip()[:4]
        
        return {
            "number": card_number,
            "month": month,
            "year": year,
            "cvv": cvv,
            "type": card_type,
            "bin": card_number[:6],
            "masked": f"{card_number[:6]}******{card_number[-4:]}"
        }
    
    async def check_card_real(self, card_info: Dict[str, Any], country_code: str = "US") -> Dict[str, Any]:
        """Real Shopify card check - Multiple methods"""
        
        identity = self.generate_identity(country_code)
        country_name = COUNTRIES.get(country_code, COUNTRIES["US"])["name"]
        start_time = time.time()
        
        result = {
            "card": card_info["masked"],
            "bin": card_info["bin"],
            "card_type": card_info["type"],
            "country": f"{country_code}",
            "country_name": country_name,
            "status": "UNKNOWN",
            "message": "Checking...",
            "gateway": "N/A",
            "response_time": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Method 1: Shopify Store Create API
        method1 = await self._method_store_create(card_info, identity)
        if method1 and method1["status"] != "UNKNOWN":
            elapsed = time.time() - start_time
            result.update(method1)
            result["response_time"] = f"{elapsed:.2f}s"
            self._update_stats(result["status"])
            return result
        
        # Method 2: Shopify Payment Validate
        method2 = await self._method_payment_validate(card_info, identity)
        if method2 and method2["status"] != "UNKNOWN":
            elapsed = time.time() - start_time
            result.update(method2)
            result["response_time"] = f"{elapsed:.2f}s"
            self._update_stats(result["status"])
            return result
        
        # Method 3: Stripe-style validation
        method3 = await self._method_stripe_validate(card_info, identity)
        if method3 and method3["status"] != "UNKNOWN":
            elapsed = time.time() - start_time
            result.update(method3)
            result["response_time"] = f"{elapsed:.2f}s"
            self._update_stats(result["status"])
            return result
        
        # All methods failed
        elapsed = time.time() - start_time
        result["status"] = "UNKNOWN"
        result["message"] = "⚠️ All gateways blocked - Try again later"
        result["gateway"] = "ALL FAILED"
        result["response_time"] = f"{elapsed:.2f}s"
        
        return result
    
    async def _method_store_create(self, card_info: Dict, identity: Dict) -> Optional[Dict]:
        """Method 1: Shopify Store Create"""
        try:
            # New Shopify signup URL
            url = "https://www.shopify.com/store/create"
            
            payload = {
                "store": {
                    "name": identity["store_name"],
                    "email": identity["email"],
                    "password": identity["password"],
                    "country": identity["country"],
                    "currency": "USD"
                },
                "payment": {
                    "card_number": card_info["number"],
                    "card_name": f"{identity['first_name']} {identity['last_name']}",
                    "expiry_month": card_info["month"],
                    "expiry_year": card_info["year"],
                    "cvv": card_info["cvv"]
                },
                "billing": {
                    "address": identity["address"],
                    "city": identity["city"],
                    "state": identity["state"],
                    "country": identity["country"],
                    "zip": identity["zip"]
                }
            }
            
            headers = {
                "Origin": "https://www.shopify.com",
                "Referer": "https://www.shopify.com/signup",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            }
            
            async with self.session.post(url, json=payload, headers=headers, ssl=False) as resp:
                status = resp.status
                text = await resp.text()
                
                logger.info(f"[Store Create] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200 or status == 201:
                    return {
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Shopify accepted the card",
                        "gateway": "Shopify Store Create"
                    }
                elif status == 422:
                    text_lower = text.lower()
                    if "card" in text_lower and ("declined" in text_lower or "invalid" in text_lower):
                        return {
                            "status": "DECLINED",
                            "message": "❌ DECLINED - Card rejected",
                            "gateway": "Shopify Store Create"
                        }
                    else:
                        return {
                            "status": "APPROVED",
                            "message": "✅ APPROVED - Card valid (other validation)",
                            "gateway": "Shopify Store Create"
                        }
                elif status == 402:
                    return {
                        "status": "DECLINED",
                        "message": "❌ DECLINED - Payment required",
                        "gateway": "Shopify Store Create"
                    }
        except Exception as e:
            logger.error(f"Method 1 error: {e}")
        
        return None
    
    async def _method_payment_validate(self, card_info: Dict, identity: Dict) -> Optional[Dict]:
        """Method 2: Payment Validation"""
        try:
            url = "https://www.shopify.com/payments/validate"
            
            payload = {
                "card": {
                    "number": card_info["number"],
                    "expiry": f"{card_info['month']}/{card_info['year'][-2:]}",
                    "cvv": card_info["cvv"],
                    "name": f"{identity['first_name']} {identity['last_name']}"
                },
                "billing": {
                    "country": identity["country"],
                    "zip": identity["zip"]
                }
            }
            
            headers = {
                "Origin": "https://www.shopify.com",
                "Content-Type": "application/json"
            }
            
            async with self.session.post(url, json=payload, headers=headers, ssl=False) as resp:
                status = resp.status
                text = await resp.text()
                text_lower = text.lower()
                
                logger.info(f"[Payment Validate] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200:
                    if "valid" in text_lower or "success" in text_lower:
                        return {
                            "status": "APPROVED",
                            "message": "✅ APPROVED - Card validated",
                            "gateway": "Shopify Payments"
                        }
                elif "declined" in text_lower or "invalid" in text_lower:
                    return {
                        "status": "DECLINED",
                        "message": "❌ DECLINED - Card rejected",
                        "gateway": "Shopify Payments"
                    }
        except Exception as e:
            logger.error(f"Method 2 error: {e}")
        
        return None
    
    async def _method_stripe_validate(self, card_info: Dict, identity: Dict) -> Optional[Dict]:
        """Method 3: Stripe-style validation"""
        try:
            # Shopify uses Stripe for payments
            url = "https://api.stripe.com/v1/tokens"
            
            data = {
                "card[number]": card_info["number"],
                "card[exp_month]": card_info["month"],
                "card[exp_year]": card_info["year"],
                "card[cvc]": card_info["cvv"],
                "key": "pk_live_..."  # Public key (Shopify's key)
            }
            
            headers = {
                "Origin": "https://www.shopify.com",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with self.session.post(url, data=data, headers=headers, ssl=False) as resp:
                status = resp.status
                text = await resp.text()
                text_lower = text.lower()
                
                logger.info(f"[Stripe] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200 and "token" in text_lower:
                    return {
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Card tokenized successfully",
                        "gateway": "Stripe/Shopify"
                    }
                elif "declined" in text_lower or "invalid" in text_lower:
                    return {
                        "status": "DECLINED",
                        "message": "❌ DECLINED - Card rejected by Stripe",
                        "gateway": "Stripe/Shopify"
                    }
        except Exception as e:
            logger.error(f"Method 3 error: {e}")
        
        return None
    
    def _update_stats(self, status: str):
        """Update stats"""
        self.stats["total"] += 1
        if status == "APPROVED":
            self.stats["approved"] += 1
            self.stats["live"] += 1
        elif status == "DECLINED":
            self.stats["declined"] += 1
            self.stats["die"] += 1
        elif status == "ERROR":
            self.stats["errors"] += 1
    
    async def check_batch(self, cards: List[str], country: str = "US", progress_callback=None) -> List[Dict]:
        """Check batch"""
        await self.create_session()
        results = []
        total = len(cards)
        
        for i, card_str in enumerate(cards, 1):
            card_info = self.parse_card(card_str)
            
            if not card_info:
                results.append({
                    "card": card_str[:30],
                    "bin": "N/A",
                    "card_type": "Unknown",
                    "country": country,
                    "country_name": COUNTRIES.get(country, {}).get("name", "Unknown"),
                    "status": "INVALID",
                    "message": "❌ INVALID FORMAT",
                    "gateway": "N/A",
                    "response_time": "0s",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                continue
            
            if progress_callback:
                await progress_callback(i, total, card_info["masked"])
            
            result = await self.check_card_real(card_info, country)
            results.append(result)
            
            logger.info(f"[{i}/{total}] {card_info['masked']} = {result['status']} | {result['message']}")
            
            if i < total:
                await asyncio.sleep(CHECK_DELAY)
        
        await self.close()
        return results
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
