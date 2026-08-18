#!/usr/bin/env python3
"""
Create Fake/Test Order in Shopee Sandbox
Uses the sandbox test order creation flow
"""

import json
import time
from shopee_client import ShopeeClient


def create_test_order():
    """
    In Shopee sandbox, we can simulate orders by:
    1. Using the test order creation endpoint (if available)
    2. Or creating a checkout and completing it
    
    For now, let's check what orders exist and document the process
    """
    client = ShopeeClient(
        partner_id=1221616,
        partner_key="shpk4d6149704f516949617a70434a416a5a476e5349705473684b596a664c6f",
        shop_id=226682118,
        tokens_file="tokens.json",
        sandbox=True
    )
    
    print("🧪 SHOPEE SANDBOX TEST ORDER CREATION")
    print("=" * 60)
    
    # Step 1: Get current orders to see baseline
    print("\n1️⃣ Checking current orders...")
    now = int(time.time())
    week_ago = now - (7 * 24 * 3600)
    
    result = client.call_api('GET', '/api/v2/order/get_order_list',
                            params={
                                'time_range_field': 'create_time',
                                'time_from': week_ago,
                                'time_to': now,
                                'page_size': 50
                            })
    
    if result['ok']:
        orders = result['data'].get('response', {}).get('order_list', [])
        print(f"   Found {len(orders)} existing orders")
        
        if orders:
            print("\n   Recent orders:")
            for order in orders[:5]:
                print(f"   • {order.get('order_sn')} - Status: {order.get('order_status', 'Unknown')}")
    else:
        print(f"   ❌ Error: {result['data']}")
    
    # Step 2: Check if there's a test order creation endpoint
    print("\n2️⃣ Attempting to create test order...")
    print("   Note: Sandbox may have special endpoints for test orders")
    
    # Some sandboxes support direct test order creation
    # Try the checkout endpoint (this might not work without buyer context)
    
    # Step 3: Let's simulate by documenting the flow
    print("\n3️⃣ Alternative: Document test order structure")
    
    test_order = {
        "order_sn": "TEST-ORDER-001",
        "order_status": "READY_TO_SHIP",
        "item_list": [
            {
                "item_id": 844121225,
                "item_name": "Produk Tes Payung",
                "model_id": 10006256279,
                "model_name": "Blue",
                "model_quantity_purchased": 2,
                "model_original_price": 10000,
                "model_discounted_price": 10000
            }
        ],
        "total_amount": 20000,
        "buyer_username": "sandbox_buyer_test",
        "create_time": int(time.time()),
        "pay_time": int(time.time()),
        "shipping_carrier": "JNE",
        "recipient_address": {
            "name": "Test Buyer",
            "phone": "08123456789",
            "city": "Jakarta",
            "district": "Kebayoran Baru",
            "full_address": "Jl. Test Sandbox No. 123"
        }
    }
    
    print("\n   Test Order Structure:")
    print(json.dumps(test_order, indent=4))
    
    # Step 4: Check what order statuses we can test
    print("\n4️⃣ Order Status Testing Options:")
    statuses = [
        ("UNPAID", "Order created, waiting for payment"),
        ("READY_TO_SHIP", "Paid, waiting for seller to ship"),
        ("PROCESSED", "Seller processing order"),
        ("SHIPPED", "Order shipped to buyer"),
        ("COMPLETED", "Order completed successfully"),
        ("IN_CANCEL", "Cancellation in progress"),
        ("CANCELLED", "Order cancelled"),
        ("TO_RETURN", "Return requested"),
        ("RETURNED", "Order returned")
    ]
    
    for status, desc in statuses:
        print(f"   • {status:20} - {desc}")
    
    # Step 5: Try to get order detail with a test order SN
    print("\n5️⃣ Testing order detail API with sample order SN...")
    # Use a dummy order SN to see error response
    dummy_result = client.call_api('GET', '/api/v2/order/get_order_detail',
                                  params={'order_sn_list': 'TEST-ORDER-DUMMY-001'})
    
    if dummy_result['ok']:
        print("   Unexpected: Dummy order found!")
    else:
        error = dummy_result['data'].get('error', 'Unknown')
        print(f"   Expected error: {error}")
        print("   (This confirms API is working but order doesn't exist)")
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print("""
To create REAL test orders in Shopee Sandbox:

Option 1: Use Shopee's Sandbox Buyer Interface
   - Log into sandbox Shopee as a buyer
   - Search for your test products
   - Add to cart and checkout
   - This creates a real test order

Option 2: Use Sandbox Test Scenarios
   - Some regions have automated test scenarios
   - Contact Shopee support for test order generation

Option 3: Wait for Real Buyer (in production)
   - Once live, real orders will flow through
   - Sandbox is mainly for API testing, not order simulation

Recommended Next Step:
   Since we can't easily create fake orders via API,
   let's test the order LISTING instead (see what orders exist)
   and prepare for when real orders come in.
""")
    
    return orders if result['ok'] else []


def simulate_order_for_testing():
    """
    Create a simulated order file for testing automation
    This lets us test the monitoring without real orders
    """
    print("\n🎭 CREATING SIMULATED ORDER FOR TESTING")
    print("=" * 60)
    
    simulated_orders = [
        {
            "order_sn": "SIMULATED-001",
            "order_status": "READY_TO_SHIP",
            "create_time": int(time.time()) - 3600,  # 1 hour ago
            "total_amount": 25000,
            "item_name": "Produk Tes Payung",
            "model_name": "Blue",
            "buyer_username": "test_buyer_1",
            "cancel_reason": None,
            "return_reason": None
        },
        {
            "order_sn": "SIMULATED-002", 
            "order_status": "CANCELLED",
            "create_time": int(time.time()) - 7200,  # 2 hours ago
            "total_amount": 15000,
            "item_name": "Produk Tes Payung",
            "model_name": "Red", 
            "buyer_username": "test_buyer_2",
            "cancel_reason": "Buyer changed mind",
            "return_reason": None
        },
        {
            "order_sn": "SIMULATED-003",
            "order_status": "TO_RETURN",
            "create_time": int(time.time()) - 10800,  # 3 hours ago
            "total_amount": 30000,
            "item_name": "Produk Tes Payung",
            "model_name": "Blue",
            "buyer_username": "test_buyer_3", 
            "cancel_reason": None,
            "return_reason": "Wrong item received"
        }
    ]
    
    # Save to file for testing
    with open('simulated_orders.json', 'w') as f:
        json.dump(simulated_orders, f, indent=2)
    
    print(f"✅ Created {len(simulated_orders)} simulated orders")
    print("\nSimulated Orders:")
    for order in simulated_orders:
        status_emoji = {
            "READY_TO_SHIP": "📦",
            "CANCELLED": "❌", 
            "TO_RETURN": "↩️",
            "COMPLETED": "✅"
        }.get(order['order_status'], "📋")
        
        print(f"   {status_emoji} {order['order_sn']} - {order['order_status']}")
        if order['cancel_reason']:
            print(f"      Cancel reason: {order['cancel_reason']}")
        if order['return_reason']:
            print(f"      Return reason: {order['return_reason']}")
    
    print("\n💾 Saved to: simulated_orders.json")
    print("\nUse this file to test your automation scripts!")
    
    return simulated_orders


if __name__ == "__main__":
    print("🦊 SHOPEE SANDBOX ORDER TESTING")
    print()
    
    # Check existing orders
    existing_orders = create_test_order()
    
    # Create simulated orders for testing
    simulated = simulate_order_for_testing()
    
    print("\n" + "=" * 60)
    print("✅ TEST DATA READY")
    print("=" * 60)
    print(f"""
You now have:
• {len(existing_orders)} real orders from sandbox (if any)
• {len(simulated)} simulated orders for testing

Next: Run 'python3 shopee_monitor.py --check orders' 
to test the order monitoring with simulated data!
""")
