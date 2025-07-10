import httpx
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from config import settings
import random
import sys

class ColoredFormatter(logging.Formatter):
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

logger = logging.getLogger("devino_sms")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    file_handler = logging.FileHandler('devino_sms.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


class DevinoSMSResponse:
    
    def __init__(self, code: str, description: str, success: bool = False, data: Optional[Dict] = None):
        self.code = code
        self.description = description
        self.success = success
        self.data = data or {}
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevinoSMSResponse':
        logger.debug(f"🔍 Parsing response: {json.dumps(data, ensure_ascii=False)}")
        
        code = str(data.get("Code", ""))
        description = data.get("Description", "Unknown error")
        success = code == "0"
        
        logger.info(f"📊 Result → Code: {code} | Success: {success} | Description: {description}")
        
        return cls(code=code, description=description, success=success, data=data)


class DevinoSMSService:
    
    def __init__(self):
        logger.info("🚀 Initializing Devino SMS Service")
        
        self.api_url = settings.DEVINO_API_URL or "https://phoneverification.devinotele.com"
        self.api_key = settings.DEVINO_API_KEY
        self.timeout = settings.DEVINO_TIMEOUT or 30
        self.debug_mode = settings.DEBUG_SMS
        
        self._log_config()
        self._validate_config()
    
    def _log_config(self):
        logger.info("⚙️  Configuration:")
        logger.info(f"   📍 API URL: {self.api_url}")
        logger.info(f"   🔑 API Key: {'✅ Set' if self.api_key else '❌ Missing'}")
        if self.api_key:
            logger.info(f"   🔑 API Key Preview: {self.api_key[:8]}...{self.api_key[-4:]}")
        logger.info(f"   ⏱️  Timeout: {self.timeout}s")
        logger.info(f"   🐛 Debug Mode: {self.debug_mode}")
    
    def _validate_config(self):
        logger.info("🔍 Validating configuration...")
        
        if not self.api_url:
            logger.error("❌ DEVINO_API_URL is missing!")
            raise ValueError("DEVINO_API_URL is required")
            
        if not self.api_key and not self.debug_mode:
            logger.warning("⚠️  DEVINO_API_KEY is missing - running in DEBUG mode")
            
        if self.api_key and len(self.api_key) < 10:
            logger.warning("⚠️  API Key seems too short")
            
        logger.info("✅ Configuration validation complete")
    
    def _get_headers(self) -> Dict[str, str]:
        logger.debug("🔧 Building request headers")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Wazir-FastAPI/1.0"
        }
        
        if self.api_key:
            headers["X-ApiKey"] = self.api_key
            logger.debug("✅ X-ApiKey header added")
        else:
            logger.warning("⚠️  No API key - headers without auth")
            
        logger.debug(f"📋 Headers ready: {list(headers.keys())}")
        return headers
    
    def _normalize_phone(self, phone: str) -> str:
        logger.debug(f"📱 Normalizing phone: '{phone}'")
        
        original = phone
        normalized = ''.join(filter(str.isdigit, phone))
        
        if normalized.startswith('0'):
            normalized = '996' + normalized[1:]
            logger.debug(f"   🔄 Local format detected: 0xxx → 996xxx")
        elif len(normalized) == 9:
            normalized = '996' + normalized
            logger.debug(f"   🔄 9-digit format detected: xxx → 996xxx")
        elif not normalized.startswith('996') and len(normalized) > 9:
            logger.debug(f"   ✅ International format detected")
        
        logger.info(f"📱 Phone normalized: '{original}' → '{normalized}'")
        return normalized
    
    async def send_verification_code(self, phone: str, imsi_code: Optional[str] = None) -> DevinoSMSResponse:
        logger.info("=" * 60)
        logger.info("🚀 SENDING SMS CODE via DEVINO 2FA API")
        logger.info("=" * 60)
        
        if not self.api_key:
            logger.warning("❌ No API key configured!")
            if self.debug_mode:
                code = ''.join(random.choices('0123456789', k=4))
                logger.warning(f"🔧 DEBUG MODE: Generated test code: {code}")
                print(f"\n🔥 DEBUG CODE FOR {phone}: {code}\n")
                return DevinoSMSResponse("0", f"DEBUG: Test code {code}", True, {"code": code})
            else:
                return DevinoSMSResponse("1", "API key not configured", False)
        
        try:
            step = 1
            logger.info(f"📍 Step {step}: Phone normalization")
            normalized_phone = self._normalize_phone(phone)
            
            step += 1
            logger.info(f"📍 Step {step}: Building request payload")
            request_data = {"DestinationNumber": normalized_phone}
            
            if imsi_code:
                request_data["Imsi"] = imsi_code
                logger.info(f"🔐 IMSI code included: {imsi_code}")
            
            logger.debug(f"📦 Request payload: {json.dumps(request_data, ensure_ascii=False)}")
            
            step += 1
            logger.info(f"📍 Step {step}: Preparing HTTP request")
            headers = self._get_headers()
            full_url = f"{self.api_url}/SendCode"
            logger.info(f"🌐 Target URL: {full_url}")
            
            step += 1
            logger.info(f"📍 Step {step}: Sending HTTP request")
            start_time = datetime.now()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"🔌 HTTP client created with {self.timeout}s timeout")
                
                response = await client.post(
                    full_url,
                    json=request_data,
                    headers=headers
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"⏱️  Request completed in {duration:.2f}s")
                
                step += 1
                logger.info(f"📍 Step {step}: Processing response")
                logger.info(f"📨 HTTP Status: {response.status_code}")
                logger.debug(f"📨 Response headers: {dict(response.headers)}")
                
                response_text = response.text
                logger.debug(f"📨 Raw response: {response_text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"📨 JSON parsed successfully")
                        
                        devino_response = DevinoSMSResponse.from_dict(response_data)
                        
                        if devino_response.success:
                            logger.info(f"✅ SMS code successfully sent to {normalized_phone}")
                        else:
                            logger.error(f"❌ Devino error: {devino_response.description}")
                        
                        return devino_response
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON parsing failed: {e}")
                        logger.error(f"❌ Raw response: {response_text}")
                        return DevinoSMSResponse(
                            str(response.status_code), 
                            f"JSON parsing error: {response_text}", 
                            False
                        )
                else:
                    logger.error(f"❌ HTTP error {response.status_code}")
                    logger.error(f"❌ Response: {response_text}")
                    return DevinoSMSResponse(
                        str(response.status_code), 
                        f"HTTP error: {response_text}", 
                        False
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"❌ Request timeout ({self.timeout}s)")
            return DevinoSMSResponse("timeout", f"Request timeout ({self.timeout}s)", False)
            
        except httpx.RequestError as e:
            logger.error(f"❌ Network error: {e}")
            return DevinoSMSResponse("network_error", f"Network error: {str(e)}", False)
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return DevinoSMSResponse("unexpected_error", f"Unexpected error: {str(e)}", False)
        
        finally:
            logger.info("=" * 60)
    
    async def verify_code(self, phone: str, code: str) -> DevinoSMSResponse:
        logger.info("=" * 60)
        logger.info("🔍 VERIFYING SMS CODE via DEVINO 2FA API")
        logger.info("=" * 60)
        
        if not self.api_key:
            logger.warning("❌ No API key configured!")
            if self.debug_mode:
                if len(code) == 4 and code.isdigit():
                    logger.warning(f"🔧 DEBUG MODE: Code {code} accepted")
                    return DevinoSMSResponse("0", "DEBUG: Code accepted", True)
                else:
                    logger.warning(f"🔧 DEBUG MODE: Invalid code format")
                    return DevinoSMSResponse("1", "DEBUG: Invalid code format", False)
            else:
                return DevinoSMSResponse("1", "API key not configured", False)
        
        try:
            step = 1
            logger.info(f"📍 Step {step}: Input validation")
            logger.info(f"📱 Phone: {phone}")
            logger.info(f"🔢 Code: {code}")
            
            if not code or len(code) != 4 or not code.isdigit():
                logger.error(f"❌ Invalid code format: '{code}'")
                return DevinoSMSResponse("1", "Invalid code format", False)
            
            step += 1
            logger.info(f"📍 Step {step}: Phone normalization")
            normalized_phone = self._normalize_phone(phone)
            
            step += 1
            logger.info(f"📍 Step {step}: Building verification payload")
            request_data = {
                "DestinationNumber": normalized_phone,
                "Code": code
            }
            logger.debug(f"📦 Verification payload: {json.dumps(request_data, ensure_ascii=False)}")
            
            step += 1
            logger.info(f"📍 Step {step}: Preparing verification request")
            headers = self._get_headers()
            full_url = f"{self.api_url}/CheckCode"
            logger.info(f"🌐 Target URL: {full_url}")
            
            step += 1
            logger.info(f"📍 Step {step}: Sending verification request")
            start_time = datetime.now()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    full_url,
                    json=request_data,
                    headers=headers
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"⏱️  Verification completed in {duration:.2f}s")
                
                step += 1
                logger.info(f"📍 Step {step}: Processing verification response")
                logger.info(f"📨 HTTP Status: {response.status_code}")
                
                response_text = response.text
                logger.debug(f"📨 Raw verification response: {response_text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"📨 Verification JSON parsed successfully")
                        
                        devino_response = DevinoSMSResponse.from_dict(response_data)
                        
                        if devino_response.success:
                            logger.info(f"✅ Code {code} verified successfully for {normalized_phone}")
                        else:
                            logger.warning(f"❌ Code verification failed: {devino_response.description}")
                        
                        return devino_response
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Verification JSON parsing failed: {e}")
                        return DevinoSMSResponse(
                            str(response.status_code), 
                            f"JSON parsing error: {response_text}", 
                            False
                        )
                else:
                    logger.error(f"❌ Verification HTTP error {response.status_code}")
                    logger.error(f"❌ Response: {response_text}")
                    return DevinoSMSResponse(
                        str(response.status_code), 
                        f"HTTP error: {response_text}", 
                        False
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"❌ Verification timeout ({self.timeout}s)")
            return DevinoSMSResponse("timeout", f"Verification timeout ({self.timeout}s)", False)
            
        except httpx.RequestError as e:
            logger.error(f"❌ Verification network error: {e}")
            return DevinoSMSResponse("network_error", f"Network error: {str(e)}", False)
            
        except Exception as e:
            logger.error(f"❌ Verification unexpected error: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return DevinoSMSResponse("unexpected_error", f"Unexpected error: {str(e)}", False)
        
        finally:
            logger.info("=" * 60)
    
    async def get_balance(self) -> DevinoSMSResponse:
        logger.info("💰 Checking Devino account balance")
        
        if not self.api_key:
            logger.error("❌ Cannot check balance: API key not configured")
            return DevinoSMSResponse("1", "API key not configured", False)
        
        try:
            headers = self._get_headers()
            full_url = f"{self.api_url}/GetBalance"
            logger.info(f"🌐 Balance URL: {full_url}")
            
            start_time = datetime.now()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(full_url, headers=headers)
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"⏱️  Balance request completed in {duration:.2f}s")
                
                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"💰 Balance response: {json.dumps(response_data, ensure_ascii=False)}")
                    return DevinoSMSResponse.from_dict(response_data)
                else:
                    logger.error(f"❌ Balance check failed: HTTP {response.status_code}")
                    logger.error(f"❌ Response: {response.text}")
                    return DevinoSMSResponse(str(response.status_code), "Balance check failed", False)
                    
        except Exception as e:
            logger.error(f"❌ Balance check error: {e}")
            return DevinoSMSResponse("error", f"Balance check error: {str(e)}", False)


devino_sms_service = DevinoSMSService()