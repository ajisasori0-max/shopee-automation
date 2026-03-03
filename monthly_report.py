#!/usr/bin/env python3
"""
Monthly Sales Report Generator
Run on 29th of each month
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from shopee_client import ShopeeClient


class MonthlyReport:
    def __init__(self):
        self.client = ShopeeClient(
            partner_id=1221616,
            partner_key="shpk4d6149704f516949617a70434a416a5a476e5349705473684b596a664c6f",
            shop_id=226682118,
            tokens_file="tokens.json",
            sandbox=True
        )
        self.report_date = datetime.now()
        self.month_start = self.report_date.replace(day=1, hour=0, minute=0, second=0)
        self.month_end = self.report_date
    
    def generate_report(self):
        """Generate comprehensive monthly report."""
        
        report = {
            "period": f"{self.month_start.strftime('%Y-%m-%d')} to {self.month_end.strftime('%Y-%m-%d')}",
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "orders": {},
            "products": {},
            "ads": {},
            "financial": {}
        }
        
        print("📊 Generating Monthly Report...")
        print(f"Period: {report['period']}")
        
        # 1. Order Summary
        print("\n📦 Fetching orders...")
        orders_data = self._get_orders_summary()
        report['orders'] = orders_data
        
        # 2. Product Performance
        print("📈 Analyzing products...")
        products_data = self._get_product_summary()
        report['products'] = products_data
        
        # 3. Ad Performance
        print("📊 Analyzing ads...")
        ads_data = self._get_ad_summary()
        report['ads'] = ads_data
        
        # 4. Financial Summary
        print("💰 Calculating finances...")
        financial_data = self._get_financial_summary()
        report['financial'] = financial_data
        
        # 5. Overall Summary
        report['summary'] = {
            'total_revenue': financial_data.get('total_revenue', 0),
            'total_orders': orders_data.get('total_orders', 0),
            'total_products_sold': orders_data.get('total_items', 0),
            'ad_spend': ads_data.get('total_spend', 0),
            'ad_roas': ads_data.get('roas', 0),
            'net_profit': financial_data.get('total_revenue', 0) - ads_data.get('total_spend', 0)
        }
        
        return report
    
    def _get_orders_summary(self):
        """Get order statistics for the month."""
        start_ts = int(self.month_start.timestamp())
        end_ts = int(self.month_end.timestamp())
        
        result = self.client.call_api('GET', '/api/v2/order/get_order_list',
                                     params={
                                         'time_range_field': 'create_time',
                                         'time_from': start_ts,
                                         'time_to': end_ts,
                                         'order_status': 'COMPLETED',  # Only completed orders
                                         'page_size': 100
                                     })
        
        if not result['ok']:
            return {'total_orders': 0, 'total_items': 0, 'average_order_value': 0}
        
        orders = result['data'].get('response', {}).get('order_list', [])
        
        total_revenue = 0
        total_items = 0
        
        for order in orders[:50]:  # Limit to prevent rate limiting
            order_sn = order.get('order_sn')
            detail = self.client.call_api('GET', '/api/v2/order/get_order_detail',
                                         params={'order_sn_list': order_sn})
            
            if detail['ok']:
                order_detail = detail['data'].get('response', {}).get('order_list', [{}])[0]
                total_revenue += float(order_detail.get('total_amount', 0))
                total_items += sum(item.get('model_quantity_purchased', 0) 
                                  for item in order_detail.get('item_list', []))
        
        return {
            'total_orders': len(orders),
            'total_items': total_items,
            'average_order_value': total_revenue / len(orders) if orders else 0,
            'total_revenue': total_revenue
        }
    
    def _get_product_summary(self):
        """Get product performance summary."""
        result = self.client.call_api('GET', '/api/v2/product/get_item_list',
                                     params={'offset': 0, 'page_size': 100})
        
        if not result['ok']:
            return {'total_products': 0, 'active_products': 0, 'inactive_products': 0}
        
        items = result['data'].get('response', {}).get('item', [])
        active = [i for i in items if i.get('item_status') == 'NORMAL']
        
        return {
            'total_products': len(items),
            'active_products': len(active),
            'inactive_products': len(items) - len(active)
        }
    
    def _get_ad_summary(self):
        """Get ad performance summary."""
        start_date = self.month_start.strftime('%Y-%m-%d')
        end_date = self.month_end.strftime('%Y-%m-%d')
        
        result = self.client.call_api('GET', '/api/v2/ads/get_all_cpc_ads_daily_performance',
                                     params={'start_date': start_date, 'end_date': end_date})
        
        if not result['ok']:
            return {'total_spend': 0, 'total_gmv': 0, 'roas': 0, 'total_clicks': 0, 'total_impressions': 0}
        
        data = result['data'].get('response', {}).get('data_list', [])
        
        total_spend = sum(d.get('expenditure', 0) for d in data)
        total_gmv = sum(d.get('gmv', 0) for d in data)
        roas = total_gmv / total_spend if total_spend > 0 else 0
        
        return {
            'total_spend': total_spend,
            'total_gmv': total_gmv,
            'roas': round(roas, 2),
            'total_clicks': sum(d.get('clicks', 0) for d in data),
            'total_impressions': sum(d.get('impression', 0) for d in data)
        }
    
    def _get_financial_summary(self):
        """Get financial summary."""
        # This would integrate with your accounting system
        # For now, use order data
        
        orders_data = self._get_orders_summary()
        ads_data = self._get_ad_summary()
        
        return {
            'total_revenue': orders_data.get('total_revenue', 0),
            'ad_costs': ads_data.get('total_spend', 0),
            'platform_fees': orders_data.get('total_revenue', 0) * 0.05,  # ~5% estimated
            'net_revenue': orders_data.get('total_revenue', 0) * 0.95 - ads_data.get('total_spend', 0)
        }
    
    def format_report(self, report):
        """Format report for display."""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 MONTHLY SALES REPORT")
        lines.append(f"Period: {report['period']}")
        lines.append("=" * 60)
        
        summary = report['summary']
        lines.append("\n💰 FINANCIAL SUMMARY")
        lines.append(f"Total Revenue: Rp {summary['total_revenue']:,.0f}")
        lines.append(f"Ad Spend: Rp {summary['ad_spend']:,.0f}")
        lines.append(f"Net Profit: Rp {summary['net_profit']:,.0f}")
        lines.append(f"Ad ROAS: {report['ads']['roas']:.2f}x")
        
        lines.append("\n📦 ORDER SUMMARY")
        lines.append(f"Total Orders: {summary['total_orders']}")
        lines.append(f"Products Sold: {summary['total_products_sold']}")
        lines.append(f"Avg Order Value: Rp {report['orders']['average_order_value']:,.0f}")
        
        lines.append("\n📈 AD PERFORMANCE")
        lines.append(f"Total Spend: Rp {report['ads']['total_spend']:,.0f}")
        lines.append(f"GMV from Ads: Rp {report['ads']['total_gmv']:,.0f}")
        lines.append(f"Clicks: {report['ads']['total_clicks']}")
        lines.append(f"Impressions: {report['ads']['total_impressions']}")
        
        lines.append("\n📦 PRODUCT SUMMARY")
        lines.append(f"Total Products: {report['products']['total_products']}")
        lines.append(f"Active: {report['products']['active_products']}")
        lines.append(f"Inactive: {report['products']['inactive_products']}")
        
        lines.append("\n" + "=" * 60)
        lines.append("Report Generated Successfully ✅")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_report(self, report, filename=None):
        """Save report to file."""
        if not filename:
            filename = f"monthly_report_{self.report_date.strftime('%Y%m')}.json"
        
        filepath = Path(filename)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath


if __name__ == "__main__":
    reporter = MonthlyReport()
    report = reporter.generate_report()
    
    # Display
    print("\n" + reporter.format_report(report))
    
    # Save
    filepath = reporter.save_report(report)
    print(f"\n💾 Report saved to: {filepath}")
