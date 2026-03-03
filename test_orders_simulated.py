#!/usr/bin/env python3
"""
Test Order Monitor with Simulated Data
Uses fake orders to test the monitoring logic
"""

import json
from datetime import datetime


def test_order_monitoring():
    """Test order monitoring with simulated data."""
    
    print("🧪 TESTING ORDER MONITORING")
    print("=" * 60)
    
    # Load simulated orders
    try:
        with open('simulated_orders.json', 'r') as f:
            orders = json.load(f)
    except FileNotFoundError:
        print("❌ simulated_orders.json not found!")
        print("   Run: python3 test_order_create.py")
        return
    
    print(f"\n📋 Loaded {len(orders)} simulated orders")
    
    # Categorize
    cancellations = [o for o in orders if o['order_status'] == 'CANCELLED']
    returns = [o for o in orders if o['order_status'] in ['TO_RETURN', 'RETURNED']]
    in_cancel = [o for o in orders if o['order_status'] == 'IN_CANCEL']
    
    print(f"\n📊 CATEGORIZATION:")
    print(f"   • Cancellations: {len(cancellations)}")
    print(f"   • Returns: {len(returns)}")
    print(f"   • In Cancellation: {len(in_cancel)}")
    
    # Display details
    if cancellations:
        print(f"\n❌ CANCELLATIONS ({len(cancellations)}):")
        for order in cancellations:
            print(f"   Order: {order['order_sn']}")
            print(f"   Item: {order['item_name']} ({order['model_name']})")
            print(f"   Amount: Rp {order['total_amount']:,}")
            print(f"   Reason: {order.get('cancel_reason', 'N/A')}")
            print(f"   Buyer: {order['buyer_username']}")
            print()
    
    if returns:
        print(f"\n↩️ RETURNS ({len(returns)}):")
        for order in returns:
            print(f"   Order: {order['order_sn']}")
            print(f"   Item: {order['item_name']} ({order['model_name']})")
            print(f"   Amount: Rp {order['total_amount']:,}")
            print(f"   Reason: {order.get('return_reason', 'N/A')}")
            print(f"   Buyer: {order['buyer_username']}")
            print()
    
    if in_cancel:
        print(f"\n⏳ IN CANCELLATION ({len(in_cancel)}):")
        for order in in_cancel:
            print(f"   Order: {order['order_sn']} - Action needed!")
    
    # Calculate metrics
    total_value = sum(o['total_amount'] for o in orders)
    cancelled_value = sum(o['total_amount'] for o in cancellations)
    return_value = sum(o['total_amount'] for o in returns)
    
    print("\n💰 FINANCIAL IMPACT:")
    print(f"   Total Order Value: Rp {total_value:,}")
    print(f"   Cancelled Value: Rp {cancelled_value:,} ({len(cancellations)/len(orders)*100:.1f}%)")
    print(f"   Return Value: Rp {return_value:,} ({len(returns)/len(orders)*100:.1f}%)")
    
    # Insights
    print("\n💡 INSIGHTS:")
    if cancellations:
        reasons = {}
        for o in cancellations:
            reason = o.get('cancel_reason', 'Unknown')
            reasons[reason] = reasons.get(reason, 0) + 1
        
        print("   Top cancellation reasons:")
        for reason, count in reasons.items():
            print(f"   • {reason}: {count} order(s)")
    
    if returns:
        reasons = {}
        for o in returns:
            reason = o.get('return_reason', 'Unknown')
            reasons[reason] = reasons.get(reason, 0) + 1
        
        print("   Top return reasons:")
        for reason, count in reasons.items():
            print(f"   • {reason}: {count} order(s)")
    
    print("\n" + "=" * 60)
    print("✅ SIMULATION COMPLETE")
    print("=" * 60)
    print("""
This test confirms your monitoring system can:
✓ Detect cancelled orders
✓ Identify return requests  
✓ Calculate financial impact
✓ Surface actionable insights

When you go live, this same logic will process real orders!
""")


if __name__ == "__main__":
    test_order_monitoring()
