#!/usr/bin/env python3

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.devino_sms_service import devino_sms_service
from config import settings


async def test_devino_balance():
    print("🔍 Testing Devino balance...")
    result = await devino_sms_service.get_balance()
    
    if result.success:
        print(f"✅ Balance check successful: {result.description}")
        print(f"💰 Balance data: {result.data}")
    else:
        print(f"❌ Balance check failed: {result.description}")
    
    return result.success


async def test_sms_send(phone: str):
    print(f"📱 Testing SMS send to {phone}...")
    result = await devino_sms_service.send_verification_code(phone)
    
    if result.success:
        print(f"✅ SMS sent successfully: {result.description}")
        if 'code' in result.data:
            print(f"🔑 Generated code: {result.data['code']}")
        return True, result.data.get('code')
    else:
        print(f"❌ SMS send failed: {result.description}")
        return False, None


async def test_sms_verify(phone: str, code: str):
    print(f"🔍 Testing SMS verification for {phone} with code {code}...")
    result = await devino_sms_service.verify_code(phone, code)
    
    if result.success:
        print(f"✅ SMS verification successful: {result.description}")
    else:
        print(f"❌ SMS verification failed: {result.description}")
    
    return result.success


async def main():
    print("=" * 80)
    print("🚀 DEVINO SMS API TEST SUITE")
    print("=" * 80)
    
    print("\n📋 Configuration:")
    print(f"   API URL: {devino_sms_service.api_url}")
    print(f"   API Key: {'✅ Set' if devino_sms_service.api_key else '❌ Missing'}")
    print(f"   Debug Mode: {devino_sms_service.debug_mode}")
    print(f"   Timeout: {devino_sms_service.timeout}s")
    
    if devino_sms_service.api_key:
        print(f"   API Key Preview: {devino_sms_service.api_key[:8]}...{devino_sms_service.api_key[-4:]}")
    
    print("\n" + "=" * 80)
    
    test_phone = input("📱 Enter test phone number (or press Enter for +996555123456): ").strip()
    if not test_phone:
        test_phone = "+996555123456"
    
    print(f"\n🧪 Running tests with phone: {test_phone}")
    print("=" * 80)
    
    try:
        print("\n1️⃣ Testing balance check...")
        balance_ok = await test_devino_balance()
        
        print("\n2️⃣ Testing SMS sending...")
        send_ok, test_code = await test_sms_send(test_phone)
        
        if send_ok and test_code:
            print("\n3️⃣ Testing SMS verification...")
            verify_ok = await test_sms_verify(test_phone, test_code)
        elif send_ok:
            manual_code = input("\n🔑 Enter the SMS code you received: ").strip()
            if manual_code:
                print("\n3️⃣ Testing SMS verification with manual code...")
                verify_ok = await test_sms_verify(test_phone, manual_code)
            else:
                print("⏭️  Skipping verification test")
                verify_ok = False
        else:
            print("⏭️  Skipping verification test (send failed)")
            verify_ok = False
        
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS:")
        print(f"   Balance Check: {'✅ PASS' if balance_ok else '❌ FAIL'}")
        print(f"   SMS Send: {'✅ PASS' if send_ok else '❌ FAIL'}")
        print(f"   SMS Verify: {'✅ PASS' if verify_ok else '❌ FAIL'}")
        
        if all([balance_ok, send_ok, verify_ok]):
            print("\n🎉 ALL TESTS PASSED! Devino SMS is working correctly.")
        elif devino_sms_service.debug_mode and send_ok:
            print("\n🔧 DEBUG MODE: Tests completed. Check debug logs for details.")
        else:
            print("\n⚠️  Some tests failed. Check configuration and API credentials.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main()) 