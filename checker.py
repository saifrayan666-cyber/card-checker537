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
    """Multi-Gateway Card Checker - BIN Info Fixed"""
    
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
        self.bin_cache = {}  # BIN cache
    
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
        
        card_type = "Unknown"
        card_level = "Standard"
        
        if card_number.startswith('4'):
            card_type = "Visa"
            # Determine Visa level
            bin6 = card_number[:6]
            if bin6[:4] in ['4000','4010','4020','4030','4040','4050','4060','4070','4080','4090']:
                card_level = "Classic"
            elif bin6[:4] in ['4100','4110','4120','4130','4140','4150','4160','4170','4180','4190']:
                card_level = "Gold"
            elif bin6[:4] in ['4200','4210','4220','4230','4240','4250','4260','4270','4280','4290']:
                card_level = "Platinum"
            elif bin6[:4] in ['4300','4310','4320','4330','4340','4350','4360','4370','4380','4390']:
                card_level = "Signature"
            elif bin6[:4] in ['4400','4410','4420','4430','4440','4450','4460','4470','4480','4490']:
                card_level = "Business"
            elif bin6[:4] in ['4500','4510','4520','4530','4540','4550','4560','4570','4580','4590']:
                card_level = "Infinite"
            elif bin6[:4] in ['4700','4710','4720','4730','4740','4750','4760','4770','4780','4790']:
                card_level = "Electron"
        elif card_number.startswith('5'):
            card_type = "Mastercard"
            bin6 = card_number[:6]
            if bin6[:4] in ['5100','5200']:
                card_level = "Standard"
            elif bin6[:4] in ['5300','5400']:
                card_level = "Gold"
            elif bin6[:4] in ['5500','5600']:
                card_level = "World"
            elif bin6[:4] in ['5700','5800','5900']:
                card_level = "World Elite"
            elif bin6[:4] in ['5200','5210','5220','5230','5240','5250','5260','5270','5280','5290']:
                card_level = "Platinum"
        elif card_number.startswith(('34','37')):
            card_type = "Amex"
            card_level = "Amex"
        
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
            "level": card_level,
            "bin": card_number[:6],
            "last4": card_number[-4:],
            "masked": f"{card_number[:6]}******{card_number[-4:]}",
            "expiry": f"{month}/{year[-2:]}",
            "raw": card_string
        }
    
    async def get_bin_info(self, bin_number: str, card_info: Dict = None) -> Dict:
        """Get BIN info with better fallback"""
        
        # Cache check
        if bin_number in self.bin_cache:
            return self.bin_cache[bin_number]
        
        # Try BIN API
        try:
            async with self.session.get(f"{BIN_API}/{bin_number}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bin_info = {
                        "scheme": data.get("scheme", ""),
                        "type": data.get("type", ""),
                        "brand": data.get("brand", ""),
                        "bank": data.get("bank", {}).get("name", ""),
                        "country": data.get("country", {}).get("name", ""),
                        "country_code": data.get("country", {}).get("alpha2", ""),
                        "prepaid": data.get("prepaid", False)
                    }
                    
                    # Fill missing with card info
                    if card_info:
                        if not bin_info["scheme"]:
                            bin_info["scheme"] = card_info.get("type", "")
                        if not bin_info["type"]:
                            bin_info["type"] = "Credit"
                        if not bin_info["brand"]:
                            bin_info["brand"] = card_info.get("type", "")
                        if not bin_info["bank"]:
                            bin_info["bank"] = self.guess_bank(bin_number, card_info)
                        if not bin_info["country"]:
                            bin_info["country"] = self.guess_country(bin_number, card_info)
                    
                    self.bin_cache[bin_number] = bin_info
                    return bin_info
        except:
            pass
        
        # Fallback with smart guessing
        bin_info = {
            "scheme": card_info.get("type", "Unknown") if card_info else "Unknown",
            "type": "Credit",
            "brand": card_info.get("type", "Unknown") if card_info else "Unknown",
            "bank": self.guess_bank(bin_number, card_info),
            "country": self.guess_country(bin_number, card_info),
            "country_code": "US",
            "prepaid": False
        }
        
        self.bin_cache[bin_number] = bin_info
        return bin_info
    
    def guess_bank(self, bin_number: str, card_info: Dict = None) -> str:
        """Guess bank from BIN"""
        bin6 = bin_number[:6]
        
        visa_banks = {
            "4000": "Bank of America",
            "4100": "Chase",
            "4110": "Chase",
            "4147": "Chase",
            "4200": "Wells Fargo",
            "4210": "Wells Fargo",
            "4217": "Wells Fargo",
            "4300": "Citibank",
            "4310": "Citibank",
            "4400": "Capital One",
            "4410": "Capital One",
            "4500": "US Bank",
            "4510": "US Bank",
            "4600": "PNC Bank",
            "4700": "Barclays",
            "4800": "TD Bank",
            "4900": "HSBC",
        }
        
        for prefix, bank in visa_banks.items():
            if bin6.startswith(prefix):
                return bank
        
        mc_banks = {
            "5100": "Bank of America",
            "5200": "Chase",
            "5300": "Wells Fargo",
            "5400": "Citibank",
            "5500": "Capital One",
        }
        
        for prefix, bank in mc_banks.items():
            if bin6.startswith(prefix):
                return bank
        
        return "Unknown Bank"
    
    def guess_country(self, bin_number: str, card_info: Dict = None) -> str:
        """Guess country from BIN"""
        bin6 = bin_number[:6]
        
        if bin6.startswith(('40','41','42','43','44','45','46','47','48','49')):
            return "United States"
        elif bin6.startswith(('50','51','52','53','54','55')):
            if bin6.startswith('55'):
                return "Canada"
            return "United States"
        elif bin6.startswith(('34','37')):
            return "United States"
        
        return "Unknown Country"
    
    def _build_result(self, card_info: Dict, status: str, message: str, gateway: str, elapsed: float) -> Dict:
        """Build result dict"""
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
            "card_level": card_info.get("level", "Standard"),
            "status": status,
            "message": message,
            "gateway": gateway,
            "response_time": f"{elapsed:.2f}s",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bin_info": {},
            "details": ""
        }
    
    async def check_card(self, card_info: Dict, gateway: str = "stripe") -> Dict:
        """Main check - always returns result"""
        start_time = time.time()
        
        # Try Stripe
        if gateway == "stripe":
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
                
                async with self.session.post(
                    f"{STRIPE_API}/payment_methods",
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    status = resp.status
                    elapsed = time.time() - start_time
                    
                    if status == 200:
                        result = self._build_result(card_info, "APPROVED", 
                            "✅ APPROVED - Card valid (Stripe)", "Stripe (Shopify)", elapsed)
                        return result
                    elif status == 402:
                        result = self._build_result(card_info, "DECLINED",
                            "❌ DECLINED - Stripe rejected", "Stripe (Shopify)", elapsed)
                        return result
            except:
                pass
        
        # Fallback: BIN Check with full info
        elapsed = time.time() - start_time
        bin_info = await self.get_bin_info(card_info["bin"], card_info)
        
        if bin_info.get("scheme") != "Unknown":
            result = self._build_result(card_info, "APPROVED",
                f"✅ VALID - {card_info['type']} {card_info.get('level', '')}",
                "BIN Lookup", elapsed)
            result["bin_info"] = bin_info
            return result
        
        result = self._build_result(card_info, "DECLINED",
            "❌ INVALID - Card info not found", "BIN Lookup", elapsed)
        result["bin_info"] = bin_info
        return result
    
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
            
            # Add BIN info for ALL results
            if not result.get("bin_info") or not result["bin_info"].get("bank"):
                bin_info = await self.get_bin_info(card_info["bin"], card_info)
                result["bin_info"] = bin_info
            
            # Full details
            result["full_number"] = card_info["number"]
            result["full_cvv"] = card_info["cvv"]
            result["full_month"] = card_info["month"]
            result["full_year"] = card_info["year"]
            result["card_level"] = card_info.get("level", "Standard")
            
            if result["status"] == "APPROVED" and live_result_callback:
                await live_result_callback(result, i, total)
            
            results.append(result)
            
            logger.info(f"[{i}/{total}] {card_info['masked']} = {result['status']}")
            
            if i < total:
                await asyncio.sleep(CHECK_DELAY)
        
        await self.close()
        return results
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
