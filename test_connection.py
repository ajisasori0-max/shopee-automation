#!/usr/bin/env python3
"""
Shopee API Connection Test

Simple test script to verify your API credentials work.
Run this after getting your tokens.

Usage:
    python test_connection.py
"""

from shopee_client import ShopeeClient
import json

def main():
    print("=" * 60)
    print("🧪 Shopee API Connection Test")
    print("=" * 60)
    
    try:
        # Initialize client
        print("\n1️⃣  Initializing client...")
        client = ShopeeClient()
        print(f"   ✅ Client created")
        print(f"   📋 Partner ID: {client.partner_id}")
        print(f"   🏪 Shop ID: {client.shop_id}")
        
        # Test connection
        print("\n2️⃣  Testing connection to Shopee API...")
        result = client.test_connection()
        
        if result['success']:
            print("\n" + "=" * 60)
            print("✅ SUCCESS! API connection working!")
            print("=" * 60)
            print(f"\n🏪 Shop Info:")
            print(f"   Name:    {result['shop_name']}")
            print(f"   Shop ID: {result['shop_id']}")
            print(f"   Country: {result['country']}")
            print(f"   Status:  {result['status']}")
            
            # Try to get some products
            print("\n3️⃣  Testing product fetch...")
            products = client.get_item_list(page_size=5)
            if products.get('error') == '':
                items = products.get('response', {}).get('item', [])
                print(f"   ✅ Found {len(items)} products")
                if items:
                    print("\n   📦 Sample products:")
                    for item in items[:3]:
                        print(f"      - {item.get('item_name', 'N/A')} (ID: {item.get('item_id')})")
            else:
                print(f"   ⚠️  Could not fetch products: {products.get('error')}")
            
            # Try to get recent orders
            print("\n4️⃣  Testing order fetch...")
            orders = client.get_order_list(page_size=5)
            if orders.get('error') == '':
                order_list = orders.get('response', {}).get('order_list', [])
                print(f"   ✅ Found {len(order_list)} recent orders")
                if order_list:
                    print("\n   📋 Sample orders:")
                    for order in order_list[:3]:
                        print(f"      - Order: {order.get('order_sn')}")
            else:
                print(f"   ⚠️  Could not fetch orders: {orders.get('error')}")
            
            print("\n" + "=" * 60)
            print("🎉 All tests passed! You're ready to use the Shopee API!")
            print("=" * 60)
            print("\n👆 NEXT STEPS:")
            print("   • Run quick_examples.py to see common operations")
            print("   • Check API_REFERENCE.md for endpoint documentation")
            print("   • Build your own scripts using shopee_client.py")
            
        else:
            print("\n" + "=" * 60)
            print("❌ CONNECTION FAILED")
            print("=" * 60)
            print(f"\nError: {result.get('error')}")
            print(f"Message: {result.get('message')}")
            print("\n🔧 Troubleshooting:")
            print("   1. Check your .env file has correct credentials")
            print("   2. Verify Partner ID and Key from Developer Portal")
            print("   3. Make sure Shop ID is correct")
            print("   4. Try refreshing token: python refresh_token.py")
            print("   5. Check if token expired - re-run auth flow")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔧 Make sure you've:")
        print("   1. Created .env file from .env.example")
        print("   2. Filled in your Partner ID and Key")
        print("   3. Run get_token.py to get access tokens")

if __name__ == '__main__':
    main()
