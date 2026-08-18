#!/usr/bin/env python3
"""
Shopee Financial Engine
-----------------------
Fetches order/income data from Shopee API, filters cancelled/returned/refunded,
computes net sales & profit, caches in SQLite, and exports tax-ready Excel.

Author: AI assistant
"""

import json
import time
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from shopee_client import ShopeeClient
from commerceos.platform.shopee_config import get_seller_credentials

# --- Paths ---
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "financial_data.db"
COGS_PATH = BASE_DIR / "cogs_config.json"
EXPENSES_PATH = BASE_DIR / "expenses_config.json"

# Default COGS if no config is provided (clearly marked as estimate)
DEFAULT_COGS_RATE = 0.45  # 45% of net item price


def _default_seller_creds():
    """Load production seller credentials from SecretManager."""
    return get_seller_credentials()


class ShopeeFinancialEngine:
    """End-to-end financial data pipeline for Shopee."""

    def __init__(self, partner_key: str | None = None, partner_id: int | None = None,
                 shop_id: int | None = None, tokens_file: str | Path = "tokens_production.json"):
        creds = _default_seller_creds()
        self.client = ShopeeClient(
            partner_id=partner_id if partner_id is not None else creds["partner_id"],
            partner_key=partner_key if partner_key is not None else creds["partner_key"],
            shop_id=shop_id if shop_id is not None else creds["shop_id"],
            tokens_file=str(tokens_file),
            sandbox=False,
        )
        self._init_db()
        self.cogs_map = self._load_cogs_map()
        self.expenses = self._load_expenses()

    # ===== DB =====
    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_sn TEXT PRIMARY KEY,
                created_time INTEGER,
                updated_time INTEGER,
                order_status TEXT,
                total_amount REAL,
                shipping_fee REAL,
                seller_discount REAL,
                voucher REAL,
                coins REAL,
                buyer_paid_amount REAL,
                net_income REAL,
                escrow_amount REAL,
                commission_fee REAL,
                service_fee REAL,
                seller_transaction_fee REAL,
                buyer_username TEXT,
                item_count INTEGER,
                cancelled INTEGER,
                returned INTEGER,
                refunded INTEGER,
                synced_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_sn TEXT,
                item_id INTEGER,
                item_name TEXT,
                item_sku TEXT,
                model_name TEXT,
                model_sku TEXT,
                quantity INTEGER,
                original_price REAL,
                paid_price REAL,
                discount_from_seller REAL,
                discount_from_shopee REAL,
                cogs_per_unit REAL,
                total_cogs REAL,
                FOREIGN KEY (order_sn) REFERENCES orders(order_sn)
            );

            CREATE TABLE IF NOT EXISTS ad_daily (
                date TEXT PRIMARY KEY,
                spend REAL,
                impressions INTEGER,
                clicks INTEGER,
                orders INTEGER,
                gmv REAL,
                roas REAL,
                synced_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS manual_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                category TEXT,
                description TEXT,
                amount REAL,
                added_at INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(created_time);
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_sn);
            """
        )
        conn.commit()
        conn.close()

    def _load_cogs_map(self) -> dict:
        """Map item_id -> cogs_per_unit. Falls back to default rate."""
        if not COGS_PATH.exists():
            return {}
        with open(COGS_PATH) as f:
            return json.load(f)

    def _load_expenses(self) -> list:
        if not EXPENSES_PATH.exists():
            return []
        with open(EXPENSES_PATH) as f:
            return json.load(f)

    # ===== API Helpers =====
    def _fetch_all_pages(self, fetch_fn, **kwargs):
        """Generic paginator for cursor-based APIs."""
        results = []
        cursor = None
        page = 0
        while True:
            resp = fetch_fn(cursor=cursor, **kwargs)
            data = resp.get("data", {})
            response = data.get("response", {})
            more = response.get("more", False)
            next_cursor = response.get("next_cursor")

            batch = response.get("order_list", response.get("return_list", []))
            results.extend(batch)

            page += 1
            if not more or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
            if page > 50:  # safety guard
                break
        return results

    def fetch_orders(self, start_date: datetime, end_date: datetime, status: str = "ALL"):
        """
        Fetch all order SNs in date range.
        Date range is inclusive of start, exclusive of end (in API terms).
        """
        time_from = int(start_date.timestamp())
        time_to = int(end_date.timestamp())

        def fetch(cursor=None):
            return self.client.get_order_list(
                time_from=time_from,
                time_to=time_to,
                time_range_field="create_time",
                page_size=100,
                cursor=cursor,
                order_status=status,
            )

        return self._fetch_all_pages(fetch)

    def fetch_order_details(self, order_sn_list: list):
        """Fetch details in batches of 50 (Shopee limit)."""
        all_details = []
        for i in range(0, len(order_sn_list), 50):
            batch = order_sn_list[i : i + 50]
            resp = self.client.get_order_detail(batch)
            data = resp.get("data", {})
            response = data.get("response", {})
            all_details.extend(response.get("order_list", []))
        return all_details

    def fetch_order_income(self, order_sn_list: list):
        """Fetch income in batches of 50."""
        all_income = []
        for i in range(0, len(order_sn_list), 50):
            batch = order_sn_list[i : i + 50]
            resp = self.client.get_order_income(batch)
            data = resp.get("data", {})
            response = data.get("response", {})
            all_income.extend(response.get("order_income_list", []))
        return all_income

    def fetch_returns(self, start_date: datetime, end_date: datetime):
        """Fetch return/refund list for the period."""
        def fetch(cursor=None):
            return self.client.get_return_list(
                page_size=100,
                cursor=cursor,
                start_time=int(start_date.timestamp()),
                end_time=int(end_date.timestamp()),
            )

        return self._fetch_all_pages(fetch)

    # ===== Transformers =====
    @staticmethod
    def _safe_float(val):
        try:
            return float(val or 0)
        except (TypeError, ValueError):
            return 0.0

    def _extract_order_summary(self, order_detail: dict, income_detail: dict | None) -> dict:
        """Normalize one order + its income into a flat dict."""
        order_sn = order_detail.get("order_sn")
        created_time = order_detail.get("create_time", 0)
        updated_time = order_detail.get("update_time", 0)
        status = order_detail.get("order_status", "UNKNOWN")

        cancelled = 1 if status in ("CANCELLED", "CANCELLED_RETURN") else 0
        returned = 1 if status in ("RETURN_REFUND", "RETURNED") else 0
        refunded = 1 if status in ("REFUNDED", "RETURN_REFUND") else 0

        # Income detail contains the real escrow numbers
        income = income_detail or {}
        escrow = income.get("escrow", {}) if income else {}

        # Seller protection fee / commission etc
        commission_fee = self._safe_float(escrow.get("commission_fee", 0))
        service_fee = self._safe_float(escrow.get("service_fee", 0))
        seller_transaction_fee = self._safe_float(escrow.get("seller_transaction_fee", 0))
        escrow_amount = self._safe_float(escrow.get("escrow_amount", 0))
        buyer_total_amount = self._safe_float(escrow.get("buyer_total_amount", 0))
        final_return_amount = self._safe_float(escrow.get("final_return_amount", 0))

        # Order-level amounts from order_detail
        total_amount = self._safe_float(order_detail.get("total_amount", 0))
        shipping_fee = self._safe_float(order_detail.get("estimated_shipping_fee", 0))
        seller_discount = self._safe_float(order_detail.get("seller_discount", 0))
        voucher = self._safe_float(order_detail.get("voucher_absorbed_by_seller", 0))
        coins = self._safe_float(order_detail.get("buyer_coin_paid_amount", 0))

        # Net income = what actually hits your account, minus returns
        net_income = escrow_amount - final_return_amount

        # Item extraction
        item_list = order_detail.get("item_list", [])
        items = []
        for item in item_list:
            item_id = item.get("item_id")
            qty = int(item.get("item_quantity", 1))
            paid_price = self._safe_float(item.get("model_original_price", item.get("item_original_price", 0)))
            original_price = self._safe_float(item.get("item_original_price", paid_price))
            seller_disc = self._safe_float(item.get("discount_from_seller", 0)) * qty
            shopee_disc = self._safe_float(item.get("discount_from_shopee", 0)) * qty

            # COGS per unit
            cogs_per_unit = self.cogs_map.get(str(item_id), paid_price * DEFAULT_COGS_RATE)
            total_cogs = cogs_per_unit * qty

            items.append(
                {
                    "order_sn": order_sn,
                    "item_id": item_id,
                    "item_name": item.get("item_name", ""),
                    "item_sku": item.get("item_sku", ""),
                    "model_name": item.get("model_name", ""),
                    "model_sku": item.get("model_sku", ""),
                    "quantity": qty,
                    "original_price": original_price,
                    "paid_price": paid_price,
                    "discount_from_seller": seller_disc,
                    "discount_from_shopee": shopee_disc,
                    "cogs_per_unit": cogs_per_unit,
                    "total_cogs": total_cogs,
                }
            )

        return {
            "order_sn": order_sn,
            "created_time": created_time,
            "updated_time": updated_time,
            "order_status": status,
            "total_amount": total_amount,
            "shipping_fee": shipping_fee,
            "seller_discount": seller_discount,
            "voucher": voucher,
            "coins": coins,
            "buyer_paid_amount": buyer_total_amount,
            "net_income": net_income,
            "escrow_amount": escrow_amount,
            "commission_fee": commission_fee,
            "service_fee": service_fee,
            "seller_transaction_fee": seller_transaction_fee,
            "buyer_username": order_detail.get("buyer_username", ""),
            "item_count": len(items),
            "cancelled": cancelled,
            "returned": returned,
            "refunded": refunded,
            "items": items,
            "synced_at": int(time.time()),
        }

    # ===== Sync =====
    def sync_orders(self, start_date: datetime, end_date: datetime):
        """
        Full sync: orders + details + income for a date range.
        Returns number of orders synced.
        """
        print(f"🔄 Syncing orders from {start_date.date()} to {end_date.date()}...")

        order_list = self.fetch_orders(start_date, end_date, status="ALL")
        order_sns = [o.get("order_sn") for o in order_list if o.get("order_sn")]
        if not order_sns:
            print("⚠️ No orders found in range.")
            return 0

        print(f"📦 {len(order_sns)} order SNs fetched")

        details = self.fetch_order_details(order_sns)
        income = self.fetch_order_income(order_sns)
        income_map = {i.get("order_sn"): i for i in income}

        summaries = [self._extract_order_summary(d, income_map.get(d.get("order_sn"))) for d in details]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        for summary in summaries:
            cur.execute(
                """
                INSERT OR REPLACE INTO orders VALUES (
                    :order_sn, :created_time, :updated_time, :order_status,
                    :total_amount, :shipping_fee, :seller_discount, :voucher, :coins,
                    :buyer_paid_amount, :net_income, :escrow_amount, :commission_fee,
                    :service_fee, :seller_transaction_fee, :buyer_username, :item_count,
                    :cancelled, :returned, :refunded, :synced_at
                )
                """,
                summary,
            )
            cur.execute("DELETE FROM order_items WHERE order_sn = ?", (summary["order_sn"],))
            for item in summary["items"]:
                cur.execute(
                    """
                    INSERT INTO order_items (
                        order_sn, item_id, item_name, item_sku, model_name, model_sku,
                        quantity, original_price, paid_price, discount_from_seller,
                        discount_from_shopee, cogs_per_unit, total_cogs
                    ) VALUES (
                        :order_sn, :item_id, :item_name, :item_sku, :model_name, :model_sku,
                        :quantity, :original_price, :paid_price, :discount_from_seller,
                        :discount_from_shopee, :cogs_per_unit, :total_cogs
                    )
                    """,
                    item,
                )

        conn.commit()
        conn.close()
        print(f"✅ Synced {len(summaries)} orders")
        return len(summaries)

    # ===== Reporting =====
    def get_orders_df(self, start_date: datetime | None = None, end_date: datetime | None = None,
                      exclude_cancelled: bool = True, exclude_returned: bool = True) -> pd.DataFrame:
        """Load orders from DB into a pandas DataFrame, optionally filtering."""
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM orders"
        params = []
        conditions = []

        if start_date is not None and end_date is not None:
            conditions.append("created_time BETWEEN ? AND ?")
            params.extend([int(start_date.timestamp()), int(end_date.timestamp())])
        elif end_date is not None:
            conditions.append("created_time <= ?")
            params.append(int(end_date.timestamp()))

        if exclude_cancelled:
            conditions.append("cancelled = 0")
        if exclude_returned:
            conditions.append("returned = 0")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if not df.empty:
            df["created_dt"] = pd.to_datetime(df["created_time"], unit="s").dt.tz_localize("UTC").dt.tz_convert("Asia/Jakarta")
        return df

    def get_items_df(self, order_sns: list | None = None) -> pd.DataFrame:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM order_items"
        params = []
        if order_sns:
            placeholders = ",".join("?" * len(order_sns))
            query += f" WHERE order_sn IN ({placeholders})"
            params = order_sns
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def get_ad_daily_df(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM ad_daily WHERE date BETWEEN ? AND ? ORDER BY date",
            conn,
            params=[start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")],
        )
        conn.close()
        return df

    def sync_ad_daily(self, start_date: datetime, end_date: datetime):
        """Fetch ad daily performance and store in DB."""
        print(f"🔄 Syncing ad daily from {start_date.date()} to {end_date.date()}...")
        resp = self.client.get_ad_performance_daily(
            start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        )
        data = resp.get("data", {})
        response = data.get("response", {})
        rows = response.get("data", {}).get("daily_performance", [])

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for row in rows:
            cur.execute(
                """
                INSERT OR REPLACE INTO ad_daily
                (date, spend, impressions, clicks, orders, gmv, roas, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("date"),
                    self._safe_float(row.get("spend", 0)),
                    int(row.get("impressions", 0) or 0),
                    int(row.get("clicks", 0) or 0),
                    int(row.get("orders", 0) or 0),
                    self._safe_float(row.get("gmv", 0)),
                    self._safe_float(row.get("roas", 0)),
                    int(time.time()),
                ),
            )
        conn.commit()
        conn.close()
        print(f"✅ Synced {len(rows)} ad daily rows")
        return len(rows)

    # ===== Financial Statements =====
    def compute_pl(self, start_date: datetime, end_date: datetime) -> dict:
        """
        Compute Profit & Loss for the period.
        Net Sales = total_amount from non-cancelled/returned orders.
        """
        df = self.get_orders_df(start_date, end_date, exclude_cancelled=True, exclude_returned=True)
        items_df = self.get_items_df(df["order_sn"].tolist() if not df.empty else [])
        ad_df = self.get_ad_daily_df(start_date, end_date)

        # Revenue
        gross_sales = df["total_amount"].sum() if not df.empty else 0.0
        net_sales = df["buyer_paid_amount"].sum() if not df.empty else 0.0
        order_count = len(df) if not df.empty else 0
        item_count = int(items_df["quantity"].sum().item()) if not items_df.empty else 0
        aov = net_sales / order_count if order_count else 0.0

        # Cost of Goods Sold
        cogs = items_df["total_cogs"].sum() if not items_df.empty else 0.0

        # Shopee fees
        commission = df["commission_fee"].sum() if not df.empty else 0.0
        service = df["service_fee"].sum() if not df.empty else 0.0
        transaction = df["seller_transaction_fee"].sum() if not df.empty else 0.0
        shopee_fees = commission + service + transaction

        # Discounts given by seller (treat as contra-revenue or marketing expense)
        seller_discounts = df["seller_discount"].sum() if not df.empty else 0.0

        # Ads
        ad_spend = ad_df["spend"].sum() if not ad_df.empty else 0.0

        # Gross profit
        gross_profit = net_sales - cogs - seller_discounts

        # Operating expenses
        operating_expenses = ad_spend + shopee_fees
        # Add manual expenses within period
        manual_exp = sum(
            e.get("amount", 0)
            for e in self.expenses
            if start_date.strftime("%Y-%m-%d") <= e.get("date", "") <= end_date.strftime("%Y-%m-%d")
        )
        total_opex = operating_expenses + manual_exp

        # Net profit before tax
        ebit = gross_profit - total_opex

        # Tax (placeholder)
        tax_rate = 0.0  # configure in expenses_config as needed
        tax = ebit * tax_rate if ebit > 0 else 0.0

        net_profit = ebit - tax

        return {
            "period_start": start_date.strftime("%Y-%m-%d"),
            "period_end": end_date.strftime("%Y-%m-%d"),
            "order_count": int(order_count),
            "item_count": int(item_count),
            "aov": round(aov, 2),
            "gross_sales": round(gross_sales, 2),
            "seller_discounts": round(seller_discounts, 2),
            "net_sales": round(net_sales, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round(gross_profit / net_sales * 100, 2) if net_sales else 0.0,
            "shopee_fees": round(shopee_fees, 2),
            "commission_fee": round(commission, 2),
            "service_fee": round(service, 2),
            "transaction_fee": round(transaction, 2),
            "ad_spend": round(ad_spend, 2),
            "manual_expenses": round(manual_exp, 2),
            "total_opex": round(total_opex, 2),
            "ebit": round(ebit, 2),
            "tax": round(tax, 2),
            "net_profit": round(net_profit, 2),
            "net_margin_pct": round(net_profit / net_sales * 100, 2) if net_sales else 0.0,
        }

    def compute_balance_sheet(self, end_date: datetime) -> dict:
        """
        Simplified balance sheet as of a given date.
        Cash = net income received (escrow) minus expenses paid.
        Inventory = COGS not yet sold (simplified: we don't have full stock, so zero/estimate).
        Receivable = pending escrow not yet released.
        """
        # All orders up to date
        all_df = self.get_orders_df(end_date=end_date, exclude_cancelled=True, exclude_returned=True)
        cash = all_df["net_income"].sum() if not all_df.empty else 0.0

        # Subtract all expenses paid up to date
        all_expenses = sum(e.get("amount", 0) for e in self.expenses if e.get("date", "") <= end_date.strftime("%Y-%m-%d"))
        cash -= all_expenses

        # Receivable = pending escrow. Shopee income is escrow_amount, received is net_income.
        # We approximate receivable as escrow_amount - net_income for orders not yet completed.
        pending = all_df[all_df["order_status"] != "COMPLETED"] if not all_df.empty else pd.DataFrame()
        receivable = (pending["escrow_amount"] - pending["net_income"]).sum() if not pending.empty else 0.0

        # Inventory placeholder
        inventory = 0.0

        total_assets = cash + receivable + inventory
        equity = total_assets  # simplified, no liabilities tracked

        return {
            "as_of": end_date.strftime("%Y-%m-%d"),
            "cash": round(cash, 2),
            "accounts_receivable": round(receivable, 2),
            "inventory": round(inventory, 2),
            "total_assets": round(total_assets, 2),
            "total_liabilities": 0.0,
            "equity": round(equity, 2),
        }

    def compute_cash_flow(self, start_date: datetime, end_date: datetime) -> dict:
        """Simplified cash flow statement for the period."""
        df = self.get_orders_df(start_date, end_date, exclude_cancelled=True, exclude_returned=True)
        operating_in = df["net_income"].sum() if not df.empty else 0.0

        ad_df = self.get_ad_daily_df(start_date, end_date)
        ad_out = ad_df["spend"].sum() if not ad_df.empty else 0.0

        manual_exp = sum(
            e.get("amount", 0)
            for e in self.expenses
            if start_date.strftime("%Y-%m-%d") <= e.get("date", "") <= end_date.strftime("%Y-%m-%d")
        )

        net_cash_flow = operating_in - ad_out - manual_exp

        return {
            "period_start": start_date.strftime("%Y-%m-%d"),
            "period_end": end_date.strftime("%Y-%m-%d"),
            "cash_from_operations": round(operating_in, 2),
            "ad_spend": round(ad_out, 2),
            "manual_expenses": round(manual_exp, 2),
            "net_cash_flow": round(net_cash_flow, 2),
        }

    # ===== Excel Export =====
    def export_excel(self, start_date: datetime, end_date: datetime, output_path: Path = None) -> Path:
        """Export P&L, Balance Sheet, Cash Flow, and order details to Excel."""
        if output_path is None:
            output_path = BASE_DIR / f"financial_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        pl = self.compute_pl(start_date, end_date)
        bs = self.compute_balance_sheet(end_date)
        cf = self.compute_cash_flow(start_date, end_date)
        orders_df = self.get_orders_df(start_date, end_date, exclude_cancelled=True, exclude_returned=True)
        items_df = self.get_items_df(orders_df["order_sn"].tolist() if not orders_df.empty else [])
        ad_df = self.get_ad_daily_df(start_date, end_date)

        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            workbook = writer.book
            money_fmt = workbook.add_format({"num_format": "Rp #,##0", "align": "right"})
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1})
            pct_fmt = workbook.add_format({"num_format": "0.00%", "align": "right"})

            # P&L
            pl_df = pd.DataFrame(
                [
                    ["Gross Sales", pl["gross_sales"]],
                    ["Less: Seller Discounts", -pl["seller_discounts"]],
                    ["Net Sales", pl["net_sales"]],
                    ["Cost of Goods Sold", -pl["cogs"]],
                    ["Gross Profit", pl["gross_profit"]],
                    ["Gross Margin %", pl["gross_margin_pct"] / 100],
                    ["Shopee Fees", -pl["shopee_fees"]],
                    ["  Commission Fee", -pl["commission_fee"]],
                    ["  Service Fee", -pl["service_fee"]],
                    ["  Transaction Fee", -pl["transaction_fee"]],
                    ["Ad Spend", -pl["ad_spend"]],
                    ["Manual Expenses", -pl["manual_expenses"]],
                    ["Total OpEx", -pl["total_opex"]],
                    ["EBIT", pl["ebit"]],
                    ["Tax", -pl["tax"]],
                    ["Net Profit", pl["net_profit"]],
                    ["Net Margin %", pl["net_margin_pct"] / 100],
                ],
                columns=["Item", "Amount"],
            )
            pl_df.to_excel(writer, sheet_name="P&L", index=False)
            pl_sheet = writer.sheets["P&L"]
            pl_sheet.set_column("A:A", 35)
            pl_sheet.set_column("B:B", 18, money_fmt)
            # Fix percentage rows
            for idx in [5, 16]:
                pl_sheet.write(idx, 1, pl_df.iloc[idx, 1], pct_fmt)

            # Balance Sheet
            bs_df = pd.DataFrame(
                [
                    ["Cash", bs["cash"]],
                    ["Accounts Receivable", bs["accounts_receivable"]],
                    ["Inventory", bs["inventory"]],
                    ["Total Assets", bs["total_assets"]],
                    ["Total Liabilities", bs["total_liabilities"]],
                    ["Equity", bs["equity"]],
                ],
                columns=["Item", "Amount"],
            )
            bs_df.to_excel(writer, sheet_name="Balance Sheet", index=False)
            bs_sheet = writer.sheets["Balance Sheet"]
            bs_sheet.set_column("A:A", 35)
            bs_sheet.set_column("B:B", 18, money_fmt)

            # Cash Flow
            cf_df = pd.DataFrame(
                [
                    ["Cash from Operations", cf["cash_from_operations"]],
                    ["Ad Spend", -cf["ad_spend"]],
                    ["Manual Expenses", -cf["manual_expenses"]],
                    ["Net Cash Flow", cf["net_cash_flow"]],
                ],
                columns=["Item", "Amount"],
            )
            cf_df.to_excel(writer, sheet_name="Cash Flow", index=False)
            cf_sheet = writer.sheets["Cash Flow"]
            cf_sheet.set_column("A:A", 35)
            cf_sheet.set_column("B:B", 18, money_fmt)

            # Orders detail
            if not orders_df.empty:
                export_orders = orders_df[
                    ["order_sn", "created_dt", "order_status", "total_amount", "buyer_paid_amount",
                     "net_income", "commission_fee", "service_fee", "seller_transaction_fee", "item_count"]
                ].copy()
                export_orders["created_dt"] = export_orders["created_dt"].dt.tz_localize(None)
                export_orders.to_excel(writer, sheet_name="Orders", index=False)
                writer.sheets["Orders"].set_column("A:J", 18)

            # Items detail
            if not items_df.empty:
                items_df.to_excel(writer, sheet_name="Order Items", index=False)
                writer.sheets["Order Items"].set_column("A:M", 18)

            # Ad daily
            if not ad_df.empty:
                ad_df.to_excel(writer, sheet_name="Ad Daily", index=False)
                writer.sheets["Ad Daily"].set_column("A:H", 16)

        print(f"✅ Excel exported: {output_path}")
        return output_path


# ===== CLI / Test =====
if __name__ == "__main__":
    engine = ShopeeFinancialEngine()

    end = datetime.now()
    start = end - timedelta(days=30)

    engine.sync_orders(start, end)
    engine.sync_ad_daily(start, end)

    pl = engine.compute_pl(start, end)
    bs = engine.compute_balance_sheet(end)
    cf = engine.compute_cash_flow(start, end)

    print("\n📊 P&L")
    for k, v in pl.items():
        print(f"  {k}: {v}")

    print("\n📊 Balance Sheet")
    for k, v in bs.items():
        print(f"  {k}: {v}")

    print("\n📊 Cash Flow")
    for k, v in cf.items():
        print(f"  {k}: {v}")

    engine.export_excel(start, end)
