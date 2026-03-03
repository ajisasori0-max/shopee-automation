#!/usr/bin/env python3
"""
Shopee Monitor - Individual check runner for cron jobs
Usage: python shopee_monitor.py --check [stock|orders|prices|ads|growth|all]
"""

import argparse
import sys
from datetime import datetime
from automation import ShopeeAutomation


def log_message(level, message):
    """Print formatted log message."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")


def check_stock(auto):
    """Run stock monitoring."""
    log_message("INFO", "Starting stock check...")
    
    # Known product IDs for sandbox (add your products here)
    known_products = [844121225]  # Add more as needed
    
    alerts = auto.check_stock_levels(known_product_ids=known_products)
    
    critical_count = len(alerts['critical'])
    warning_count = len(alerts['warning'])
    
    if critical_count > 0:
        log_message("CRITICAL", f"🚨 {critical_count} product(s) at CRITICAL stock level (≤101)")
        for alert in alerts['critical']:
            model = f" ({alert.get('model_name', '')})" if alert.get('model_name') else ""
            log_message("ALERT", f"  • {alert['item_name']}{model}: {alert['stock']} left")
            # Here you could send Telegram/Email notification
    
    if warning_count > 0:
        log_message("WARNING", f"⚠️  {warning_count} product(s) at WARNING stock level (102-105)")
        for alert in alerts['warning']:
            model = f" ({alert.get('model_name', '')})" if alert.get('model_name') else ""
            log_message("ALERT", f"  • {alert['item_name']}{model}: {alert['stock']} left")
    
    if critical_count == 0 and warning_count == 0:
        log_message("INFO", "✅ All stock levels healthy")
    
    return critical_count + warning_count


def check_orders(auto):
    """Run order monitoring (returns/cancellations)."""
    log_message("INFO", "Starting order check...")
    
    issues = auto.check_returns_cancellations()
    
    total = len(issues['cancellations']) + len(issues['returns']) + len(issues['in_cancel'])
    
    if total > 0:
        log_message("WARNING", f"📋 Found {total} order issues:")
        
        if issues['in_cancel']:
            log_message("INFO", f"  In Cancellation: {len(issues['in_cancel'])}")
            for order in issues['in_cancel']:
                log_message("DETAIL", f"    • Order {order['order_sn']} - {order['item_name']}")
        
        if issues['cancellations']:
            log_message("INFO", f"  Cancelled: {len(issues['cancellations'])}")
            for order in issues['cancellations']:
                reason = order.get('cancel_reason', 'Unknown')
                log_message("DETAIL", f"    • Order {order['order_sn']} - Reason: {reason}")
        
        if issues['returns']:
            log_message("INFO", f"  Returns: {len(issues['returns'])}")
            for order in issues['returns']:
                reason = order.get('return_reason', 'Unknown')
                log_message("DETAIL", f"    • Order {order['order_sn']} - Reason: {reason}")
    else:
        log_message("INFO", "✅ No returns or cancellations")
    
    return total


def check_prices(auto):
    """Run price monitoring."""
    log_message("INFO", "Starting price monitoring...")
    
    changes = auto.monitor_prices()
    
    if changes:
        log_message("INFO", f"💰 {len(changes)} price change(s) detected:")
        for change in changes:
            direction = "📈 UP" if change['change'] > 0 else "📉 DOWN"
            log_message("CHANGE", f"  {direction} {change['item_name']}: "
                       f"{change['old_price']} → {change['new_price']} "
                       f"({change['change']:+.0f})")
    else:
        log_message("INFO", "✅ No price changes")
    
    return len(changes)


def check_ads(auto):
    """Run ad monitoring."""
    log_message("INFO", "Starting ad monitoring...")
    
    feedback = auto.monitor_ads()
    
    log_message("INFO", f"💰 Ad Balance: {feedback['balance']:,} IDR")
    
    for rec in feedback['recommendations']:
        if '⚠️' in rec:
            log_message("WARNING", f"  {rec}")
        elif '✅' in rec:
            log_message("SUCCESS", f"  {rec}")
        else:
            log_message("INFO", f"  {rec}")
    
    if feedback['balance'] < 50000:
        log_message("CRITICAL", "🚨 Ad balance critically low! Top up immediately.")
    elif feedback['balance'] < 100000:
        log_message("WARNING", "⚠️  Ad balance running low. Consider topping up.")
    
    return 0


def check_growth(auto):
    """Run sales growth analysis."""
    log_message("INFO", "Starting growth analysis...")
    
    insights = auto.analyze_sales_growth()
    
    for insight in insights:
        if '📊' in insight or '📦' in insight:
            log_message("METRIC", insight)
        elif '💡' in insight:
            log_message("TIP", insight)
        elif '⚠️' in insight:
            log_message("WARNING", insight)
        else:
            log_message("INFO", insight)
    
    return 0


def run_all_checks(auto):
    """Run all monitoring checks."""
    log_message("INFO", "=" * 60)
    log_message("INFO", "Running full automation check")
    log_message("INFO", "=" * 60)
    
    results = {
        'stock': check_stock(auto),
        'orders': check_orders(auto),
        'prices': check_prices(auto),
        'ads': check_ads(auto),
        'growth': check_growth(auto)
    }
    
    log_message("INFO", "=" * 60)
    log_message("INFO", "Full check complete")
    log_message("INFO", f"Results: {results}")
    log_message("INFO", "=" * 60)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Shopee Automation Monitor')
    parser.add_argument('--check', required=True,
                       choices=['stock', 'orders', 'prices', 'ads', 'growth', 'all'],
                       help='Which check to run')
    
    args = parser.parse_args()
    
    try:
        auto = ShopeeAutomation()
        
        if args.check == 'stock':
            return check_stock(auto)
        elif args.check == 'orders':
            return check_orders(auto)
        elif args.check == 'prices':
            return check_prices(auto)
        elif args.check == 'ads':
            return check_ads(auto)
        elif args.check == 'growth':
            return check_growth(auto)
        elif args.check == 'all':
            run_all_checks(auto)
            return 0
            
    except Exception as e:
        log_message("ERROR", f"Failed to run check: {str(e)}")
        import traceback
        log_message("ERROR", traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
