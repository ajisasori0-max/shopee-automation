#!/usr/bin/env python3
"""
Shopee Automation Suite - Main Controller
Handles: Stock monitoring, Order tracking, Price monitoring, Ad monitoring
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from shopee_client import ShopeeClient

class ShopeeAutomation:
    def __init__(self):
        self.client = ShopeeClient(
            partner_id=1221616,
            partner_key="shpk4d6149704f516949617a70434a416a5a476e5349705473684b596a664c6f",
            shop_id=226682118,
            tokens_file="tokens.json",
            sandbox=True
        )
        self.state_file = Path("automation_state.json")
        self.state = self._load_state()
    
    def _load_state(self):
        """Load persistent state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "last_stock_check": 0,
            "last_order_check": 0,
            "alerted_products": {},  # Track which products we've alerted for
            "price_history": {},
            "ad_performance_history": []
        }
    
    def _save_state(self):
        """Save persistent state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    # ===== 1. STOCK MONITORING =====
    
    def check_stock_levels(self, known_product_ids=None):
        """
        Check all products for low stock.
        Alert levels: 105 (warning), 101 (critical)
        
        Args:
            known_product_ids: List of product IDs to check (for sandbox)
        """
        print("🔍 Checking stock levels...")
        
        alerts = {
            "warning": [],    # 102-105
            "critical": []    # <= 101
        }
        
        items = []
        
        # Try to get product list
        result = self.client.call_api('GET', '/api/v2/product/get_item_list', 
                                     params={'offset': 0, 'page_size': 100})
        
        if result['ok']:
            items = result['data'].get('response', {}).get('item', [])
        
        # Fallback: use known product IDs (for sandbox)
        if not items and known_product_ids:
            print(f"⚠️  Product list API failed, checking known products: {known_product_ids}")
            for pid in known_product_ids:
                detail = self.client.get_product_detail(item_id=pid)
                if detail['ok']:
                    item_list = detail['data'].get('response', {}).get('item_list', [])
                    if item_list:
                        items.extend(item_list)
        
        for item in items:
            item_id = item['item_id']
            item_name = item['item_name']
            
            # Check if product has variants
            if item.get('has_model'):
                # Get model details
                model_result = self.client.call_api('GET', '/api/v2/product/get_model_list',
                                                   params={'item_id': item_id})
                if model_result['ok']:
                    models = model_result['data'].get('response', {}).get('model', [])
                    for model in models:
                        stock = model.get('stock_info_v2', {}).get('summary_info', {}).get('total_available_stock', 0)
                        model_name = model.get('model_name', 'Unknown')
                        model_id = model['model_id']
                        
                        alert_key = f"{item_id}_{model_id}"
                        
                        if stock <= 101:
                            if self._should_alert(alert_key, stock, 'critical'):
                                alerts['critical'].append({
                                    'item_id': item_id,
                                    'item_name': item_name,
                                    'model_id': model_id,
                                    'model_name': model_name,
                                    'stock': stock,
                                    'level': 'CRITICAL'
                                })
                        elif stock <= 105:
                            if self._should_alert(alert_key, stock, 'warning'):
                                alerts['warning'].append({
                                    'item_id': item_id,
                                    'item_name': item_name,
                                    'model_id': model_id,
                                    'model_name': model_name,
                                    'stock': stock,
                                    'level': 'WARNING'
                                })
            else:
                # Simple product (no variants)
                stock = item.get('stock', 0)
                alert_key = str(item_id)
                
                if stock <= 101:
                    if self._should_alert(alert_key, stock, 'critical'):
                        alerts['critical'].append({
                            'item_id': item_id,
                            'item_name': item_name,
                            'stock': stock,
                            'level': 'CRITICAL'
                        })
                elif stock <= 105:
                    if self._should_alert(alert_key, stock, 'warning'):
                        alerts['warning'].append({
                            'item_id': item_id,
                            'item_name': item_name,
                            'stock': stock,
                            'level': 'WARNING'
                        })
        
        self._save_state()
        return alerts
    
    def _should_alert(self, alert_key, current_stock, level):
        """Check if we should send alert (avoid spam)."""
        last_alert = self.state['alerted_products'].get(alert_key, {})
        
        # Alert if:
        # 1. Never alerted before
        # 2. Stock dropped since last alert
        # 3. Level changed (warning -> critical)
        
        if not last_alert:
            self.state['alerted_products'][alert_key] = {
                'stock': current_stock,
                'level': level,
                'time': time.time()
            }
            return True
        
        if current_stock < last_alert['stock']:
            self.state['alerted_products'][alert_key] = {
                'stock': current_stock,
                'level': level,
                'time': time.time()
            }
            return True
        
        if level == 'critical' and last_alert['level'] == 'warning':
            self.state['alerted_products'][alert_key] = {
                'stock': current_stock,
                'level': level,
                'time': time.time()
            }
            return True
        
        return False
    
    # ===== 2. ORDER MONITORING (Returns/Cancellations) =====
    
    def check_returns_cancellations(self):
        """
        Track orders with:
        - IN_CANCEL status (cancellation in progress)
        - CANCELLED status (cancelled)
        - TO_RETURN status (return requested)
        - RETURNED status (returned)
        """
        print("📋 Checking returns and cancellations...")
        
        issues = {
            'cancellations': [],
            'returns': [],
            'in_cancel': []
        }
        
        # Check last 7 days
        now = int(time.time())
        week_ago = now - (7 * 24 * 3600)
        
        # Get orders with different statuses
        statuses_to_check = ['CANCELLED', 'TO_RETURN', 'IN_CANCEL']
        
        for status in statuses_to_check:
            result = self.client.call_api('GET', '/api/v2/order/get_order_list',
                                         params={
                                             'time_range_field': 'create_time',
                                             'time_from': week_ago,
                                             'time_to': now,
                                             'order_status': status,
                                             'page_size': 50
                                         })
            
            if result['ok']:
                orders = result['data'].get('response', {}).get('order_list', [])
                
                for order in orders:
                    order_sn = order.get('order_sn')
                    
                    # Get order details
                    detail_result = self.client.call_api('GET', '/api/v2/order/get_order_detail',
                                                        params={'order_sn_list': order_sn})
                    
                    if detail_result['ok']:
                        order_detail = detail_result['data'].get('response', {}).get('order_list', [{}])[0]
                        
                        issue = {
                            'order_sn': order_sn,
                            'status': status,
                            'create_time': order_detail.get('create_time'),
                            'total_amount': order_detail.get('total_amount'),
                            'item_name': order_detail.get('item_list', [{}])[0].get('item_name', 'Unknown'),
                            'variation_name': order_detail.get('item_list', [{}])[0].get('model_name', ''),
                            'buyer_username': order_detail.get('buyer_username'),
                            'cancel_reason': order_detail.get('cancel_reason', 'N/A'),
                            'return_reason': order_detail.get('return_reason', 'N/A')
                        }
                        
                        if status == 'IN_CANCEL':
                            issues['in_cancel'].append(issue)
                        elif status == 'CANCELLED':
                            issues['cancellations'].append(issue)
                        elif status in ['TO_RETURN', 'RETURNED']:
                            issues['returns'].append(issue)
        
        return issues
    
    # ===== 3. PRICE MONITORING =====
    
    def monitor_prices(self):
        """
        Track price changes for all products.
        """
        print("💰 Monitoring prices...")
        
        changes = []
        
        result = self.client.call_api('GET', '/api/v2/product/get_item_list',
                                     params={'offset': 0, 'page_size': 100})
        
        if not result['ok']:
            return changes
        
        items = result['data'].get('response', {}).get('item', [])
        
        for item in items:
            item_id = item['item_id']
            current_price = item.get('price', 0)
            
            # Check against history
            if str(item_id) in self.state['price_history']:
                old_price = self.state['price_history'][str(item_id)]
                if current_price != old_price:
                    changes.append({
                        'item_id': item_id,
                        'item_name': item['item_name'],
                        'old_price': old_price,
                        'new_price': current_price,
                        'change': current_price - old_price
                    })
            
            # Update history
            self.state['price_history'][str(item_id)] = current_price
        
        self._save_state()
        return changes
    
    # ===== 4. AD MONITORING =====
    
    def monitor_ads(self):
        """
        Monitor ad performance and give feedback.
        """
        print("📊 Monitoring ad performance...")
        
        feedback = {
            'balance': 0,
            'performance': [],
            'recommendations': []
        }
        
        # Get balance
        balance_result = self.client.get_ad_balance()
        if balance_result['ok']:
            feedback['balance'] = balance_result['data'].get('response', {}).get('total_balance', 0)
        
        # Get daily performance (last 7 days)
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        perf_result = self.client.get_ad_performance_daily(start_date, end_date)
        if perf_result['ok']:
            perf_data = perf_result['data'].get('response', {}).get('data_list', [])
            feedback['performance'] = perf_data
            
            # Generate recommendations
            if perf_data:
                total_spend = sum(d.get('expenditure', 0) for d in perf_data)
                total_gmv = sum(d.get('gmv', 0) for d in perf_data)
                total_orders = sum(d.get('orders', 0) for d in perf_data)
                
                if total_spend > 0:
                    roas = total_gmv / total_spend
                    feedback['recommendations'].append(f"ROAS (7-day): {roas:.2f}x")
                    
                    if roas < 2:
                        feedback['recommendations'].append("⚠️ ROAS is low. Consider optimizing targeting or reducing bids.")
                    elif roas > 4:
                        feedback['recommendations'].append("✅ Great ROAS! Consider increasing budget to scale.")
                
                if feedback['balance'] < 100000:  # Less than 100k IDR
                    feedback['recommendations'].append("⚠️ Low ad balance. Consider topping up.")
        
        return feedback
    
    # ===== 5. SALES GROWTH RESEARCH =====
    
    def analyze_sales_growth(self):
        """
        Analyze sales trends and suggest growth strategies.
        """
        print("📈 Analyzing sales growth opportunities...")
        
        insights = []
        
        # Get recent orders
        now = int(time.time())
        day_ago = now - (24 * 3600)
        week_ago = now - (7 * 24 * 3600)
        
        # Today's orders
        today_result = self.client.call_api('GET', '/api/v2/order/get_order_list',
                                           params={
                                               'time_range_field': 'create_time',
                                               'time_from': day_ago,
                                               'time_to': now,
                                               'page_size': 100
                                           })
        
        today_orders = 0
        today_revenue = 0
        
        if today_result['ok']:
            orders = today_result['data'].get('response', {}).get('order_list', [])
            today_orders = len(orders)
            # Would need order details for revenue
        
        # Compare with yesterday (simplified)
        insights.append(f"📊 Today's Orders: {today_orders}")
        
        # Product performance
        result = self.client.call_api('GET', '/api/v2/product/get_item_list',
                                     params={'offset': 0, 'page_size': 100})
        
        if result['ok']:
            items = result['data'].get('response', {}).get('item', [])
            
            # Find best sellers by stock movement (simplified metric)
            # In real scenario, you'd use sales data API
            
            insights.append(f"📦 Total Products: {len(items)}")
            
            # Check for inactive products
            inactive = [i for i in items if i.get('item_status') != 'NORMAL']
            if inactive:
                insights.append(f"⚠️ {len(inactive)} products are not active. Consider re-listing.")
        
        # Growth suggestions
        suggestions = [
            "💡 Enable auto top-up for ads to avoid losing momentum",
            "💡 Add more variations to best-selling products",
            "💡 Use Shopee's 'Boost' feature during peak hours (8-10 PM)",
            "💡 Offer bundle deals for products frequently bought together",
            "💡 Respond to chats within 1 hour for higher conversion",
            "💡 Use high-quality images (at least 3 per product)",
            "💡 Enable free shipping to increase cart conversion",
            "💡 Run flash sales on weekends for higher traffic"
        ]
        
        insights.extend(suggestions[:3])  # Top 3 suggestions
        
        return insights


if __name__ == "__main__":
    auto = ShopeeAutomation()
    
    print("=" * 60)
    print("🦊 SHOPEE AUTOMATION SUITE")
    print("=" * 60)
    
    # Run all checks
    print("\n1️⃣ STOCK MONITORING")
    stock_alerts = auto.check_stock_levels()
    if stock_alerts['critical']:
        print(f"🚨 CRITICAL ({len(stock_alerts['critical'])} products):")
        for a in stock_alerts['critical']:
            print(f"   • {a['item_name']} ({a.get('model_name', '')}): {a['stock']} left")
    if stock_alerts['warning']:
        print(f"⚠️  WARNING ({len(stock_alerts['warning'])} products):")
        for a in stock_alerts['warning']:
            print(f"   • {a['item_name']} ({a.get('model_name', '')}): {a['stock']} left")
    if not stock_alerts['critical'] and not stock_alerts['warning']:
        print("✅ All stock levels healthy")
    
    print("\n2️⃣ RETURNS/CANCELLATIONS")
    issues = auto.check_returns_cancellations()
    total_issues = len(issues['cancellations']) + len(issues['returns']) + len(issues['in_cancel'])
    if total_issues > 0:
        print(f"📋 Found {total_issues} issues:")
        print(f"   • In Cancellation: {len(issues['in_cancel'])}")
        print(f"   • Cancelled: {len(issues['cancellations'])}")
        print(f"   • Returns: {len(issues['returns'])}")
    else:
        print("✅ No returns or cancellations")
    
    print("\n3️⃣ PRICE MONITORING")
    price_changes = auto.monitor_prices()
    if price_changes:
        print(f"💰 {len(price_changes)} price changes detected:")
        for c in price_changes:
            direction = "📈" if c['change'] > 0 else "📉"
            print(f"   {direction} {c['item_name']}: {c['old_price']} → {c['new_price']}")
    else:
        print("✅ No price changes")
    
    print("\n4️⃣ AD MONITORING")
    ad_feedback = auto.monitor_ads()
    print(f"💰 Ad Balance: {ad_feedback['balance']:,} IDR")
    for rec in ad_feedback['recommendations']:
        print(f"   {rec}")
    
    print("\n5️⃣ GROWTH INSIGHTS")
    insights = auto.analyze_sales_growth()
    for insight in insights:
        print(f"   {insight}")
    
    print("\n" + "=" * 60)
    print("✅ AUTOMATION CHECK COMPLETE")
    print("=" * 60)
