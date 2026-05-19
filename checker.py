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
    """Multi-Gateway Card Checker"""
    
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
            "Cache-Control": "no-cache",
        }
        
        connector = aiohttp.TCPConnector(limit=100, force_close=True, enable_cleanup_closed=True)
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
        
        # Card type
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
            "last4": card_number[-4:],
            "masked": f"{card_number[:6]}******{card_number[-4:]}",
            "expiry": f"{month}/{year[-2:]}"
        }
    
    async def get_bin_info(self, bin_number: str) -> Dict:
        try:
            async with self.session.get(f"{BIN_API}/{bin_number}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "scheme": data.get("scheme", "Unknown"),
                        "type": data.get("type", "Unknown"),
                        "brand": data.get("brand", "Unknown"),
                        "bank": data.get("bank", {}).get("name", "Unknown"),
                        "country": data.get("country", {}).get("name", "Unknown"),
                        "country_code": data.get("country", {}).get("alpha2", "US"),
                        "prepaid": data.get("prepaid", False)
                    }
        except:
            pass
        
        return {
            "scheme": "Visa" if bin_number.startswith('4') else "Mastercard" if bin_number.startswith('5') else "Unknown",
            "type": "Credit",
            "brand": "Unknown",
            "bank": "Unknown",
            "country": "Unknown",
            "country_code": "US",
            "prepaid": False
        }
    
    async def check_stripe(self, card_info: Dict) -> Optional[Dict]:
        start_time = time.time()
        try:
            data = {
                "type": "card",
                "card[number]": card_info["number"],
                "card[exp_month]": card_info["month"],
                "card[exp_year]": card_info["year"],
                "card[cvc]": card_info["cvv"],
            }
            headers = {
                "Authorization": f"Bearer {STRIPE_PUBLIC_KEY}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with self.session.post(f"{STRIPE_API}/payment_methods", data=data, headers=headers) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                if status == 200:
                    self.stats["total"] += 1
                    self.stats["approved"] += 1
                    self.stats["live"] += 1
                    return {
                        "card": card_info["masked"],
                        "number": card_info["number"],
                        "month": card_info["month"],
                        "year": card_info["year"],
                        "cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Card valid (Stripe)",
                        "gateway": "Stripe (Shopify)",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": ""
                    }
                
                elif status == 402 or status == 400:
                    self.stats["total"] += 1
                    self.stats["declined"] += 1
                    self.stats["die"] += 1
                    return {
                        "card": card_info["masked"],
                        "number": card_info["number"],
                        "month": card_info["month"],
                        "year": card_info["year"],
                        "cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "DECLINED",
                        "message": "❌ DECLINED - Card rejected (Stripe)",
                        "gateway": "Stripe (Shopify)",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": ""
                    }
        except:
            pass
        return None
    
    async def check_braintree(self, card_info: Dict) -> Optional[Dict]:
        start_time = time.time()
        try:
            query = """
            mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
                tokenizeCreditCard(input: $input) {
                    token
                }
            }
            """
            variables = {
                "input": {
                    "creditCard": {
                        "number": card_info["number"],
                        "expirationMonth": card_info["month"],
                        "expirationYear": card_info["year"],
                        "cvv": card_info["cvv"]
                    }
                }
            }
            payload = {"query": query, "variables": variables}
            headers = {
                "Authorization": f"Bearer {BRAINTREE_PUBLIC_KEY}",
                "Content-Type": "application/json",
                "Braintree-Version": "2019-01-01"
            }
            
            async with self.session.post(BRAINTREE_API, json=payload, headers=headers) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                if status == 200 and "token" in text.lower():
                    self.stats["total"] += 1
                    self.stats["approved"] += 1
                    self.stats["live"] += 1
                    return {
                        "card": card_info["masked"],
                        "number": card_info["number"],
                        "month": card_info["month"],
                        "year": card_info["year"],
                        "cvv": card_info["cvv"],
                        "expiry": card_info["expiry"],
                        "bin": card_info["bin"],
                        "last4": card_info["last4"],
                        "card_type": card_info["type"],
                        "status": "APPROVED",
                        "message": "✅ APPROVED - Card valid (Braintree)",
                        "gateway": "Braintree (PayPal)",
                        "response_time": f"{elapsed:.2f}s",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bin_info": {},
                        "details": ""
                    }
        except:
            pass
        return None
    
    async def check_bin_only(self, card_info: Dict) -> Dict:
        start_time = time.time()
        bin_info = await self.get_bin_info(card_info["bin"])
        elapsed = time.time() - start_time
        
        if bin_info.get("scheme") != "Unknown":
            self.stats["total"] += 1
            self.stats["approved"] += 1
            self.stats["live"] += 1
            return {
                "card": card_info["masked"],
                "number": card_info["number"],
                "month": card_info["month"],
                "year": card_info["year"],
                "cvv": card_info["cvv"],
                "expiry": card_info["expiry"],
                "bin": card_info["bin"],
                "last4": card_info["last4"],
                "card_type": card_info["type"],
                "status": "APPROVED",
                "message": f"✅ VALID BIN - {bin_info.get('brand', 'Unknown')}",
                "gateway": "BIN Lookup",
                "response_time": f"{elapsed:.2f}s",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bin_info": bin_info,
                "details": ""
            }
        
        self.stats["total"] += 1
        self.stats["declined"] += 1
        self.stats["die"] += 1
        return {
            "card": card_info["masked"],
            "number": card_info["number"],
            "month": card_info["month"],
            "year": card_info["year"],
            "cvv": card_info["cvv"],
            "expiry": card_info["expiry"],
            "bin": card_info["bin"],
            "last4": card_info["last4"],
            "card_type": card_info["type"],
            "status": "DECLINED",
            "message": "❌ INVALID - Unknown BIN",
            "gateway": "BIN Lookup",
            "response_time": f"{elapsed:.2f}s",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bin_info": bin_info,
            "details": ""
        }
    
    async def check_card(self, card_info: Dict, gateway: str = "stripe") -> Dict:
        if gateway == "stripe":
            result = await self.check_stripe(card_info)
            if result:
                return result
        
        if gateway == "braintree":
            result = await self.check_braintree(card_info)
            if result:
                return result
        
        if gateway in ["adyen", "checkout"]:
            result = await self.check_stripe(card_info)
            if result:
                return result
        
        if gateway == "bin_check":
            return await self.check_bin_only(card_info)
        
        # Fallback
        result = await self.check_stripe(card_info)
        if result:
            return result
        
        result = await self.check_braintree(card_info)
        if result:
            return result
        
        return await self.check_bin_only(card_info)
    
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
                    "number": "N/A",
                    "month": "N/A",
                    "year": "N/A",
                    "cvv": "N/A",
                    "expiry": "N/A",
                    "bin": "N/A",
                    "last4": "N/A",
                    "card_type": "Unknown",
                    "status": "INVALID",
                    "message": "❌ INVALID FORMAT",
                    "gateway": "N/A",
                    "response_time": "0s",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "bin_info": {},
                    "details": "Invalid format"
                })
                continue
            
            if progress_callback:
                await progress_callback(i, total, card_info["masked"])
            
            result = await self.check_card(card_info, gateway)
            
            if result["status"] == "APPROVED":
                bin_info = await self.get_bin_info(card_info["bin"])
                result["bin_info"] = bin_info
                result["details"] = (
                    f"CC: {card_info['masked']} | "
                    f"MM/YY: {card_info['month']}/{card_info['year']} | "
                    f"CVV: {card_info['cvv']} | "
                    f"BIN: {card_info['bin']} | "
                    f"Bank: {bin_info.get('bank', 'N/A')} | "
                    f"Country: {bin_info.get('country', 'N/A')} | "
                    f"Gateway: {result['gateway']}"
                )
                
                if live_result_callback:
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
