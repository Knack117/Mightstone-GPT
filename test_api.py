#!/usr/bin/env python3
"""
Test script for Mightstone GPT Webservice
"""

import asyncio
import json
import sys
from typing import Any, Dict

import httpx


class MightstoneGPTTester:
    """Test suite for Mightstone GPT API."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_health(self) -> bool:
        """Test health endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_root(self) -> bool:
        """Test root endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Root endpoint: {data['service']} v{data['version']}")
                return True
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    async def test_card_search(self) -> bool:
        """Test card search functionality."""
        try:
            params = {"q": "type:creature cmc:3", "limit": 5}
            response = await self.client.get(f"{self.base_url}/cards/search", params=params)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Card search: Found {data['total_cards']} cards")
                return True
            else:
                print(f"❌ Card search failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Card search error: {e}")
            return False
    
    async def test_commander_data(self) -> bool:
        """Test commander data retrieval."""
        try:
            response = await self.client.get(f"{self.base_url}/commander/Sol%20Ring")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Commander data: {data['commander']['name']}")
                return True
            else:
                print(f"❌ Commander data failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Commander data error: {e}")
            return False
    
    async def test_theme_data(self) -> bool:
        """Test theme data retrieval."""
        try:
            response = await self.client.get(f"{self.base_url}/themes/prowess?colors=UR")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Theme data: {data['theme_name']} with {len(data['items']['items'])} cards")
                return True
            else:
                print(f"❌ Theme data failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Theme data error: {e}")
            return False
    
    async def test_privacy(self) -> bool:
        """Test privacy policy endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/privacy")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Privacy policy: {data['title']}")
                return True
            else:
                print(f"❌ Privacy policy failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Privacy policy error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        print("🧪 Running Mightstone GPT API Tests")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health),
            ("Root Endpoint", self.test_root),
            ("Card Search", self.test_card_search),
            ("Commander Data", self.test_commander_data),
            ("Theme Data", self.test_theme_data),
            ("Privacy Policy", self.test_privacy)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n🧪 Testing: {test_name}")
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        return results
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()


async def main():
    """Main test runner."""
    print("🚀 Starting Mightstone GPT API Test Suite")
    
    tester = MightstoneGPTTester()
    
    try:
        results = await tester.run_all_tests()
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n🏆 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! API is ready for use.")
            return 0
        else:
            print("⚠️ Some tests failed. Check the API implementation.")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        return 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)