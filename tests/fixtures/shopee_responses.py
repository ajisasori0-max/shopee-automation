"""Fake Shopee API responses for unit testing."""

from datetime import datetime, timezone


def order_list_response(order_sns: list[str], next_cursor: str | None = None, more: bool = False) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": {
                "order_list": [{"order_sn": sn} for sn in order_sns],
                "next_cursor": next_cursor,
                "more": more,
                "total": len(order_sns),
            },
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": {
            "order_list": [{"order_sn": sn} for sn in order_sns],
            "next_cursor": next_cursor,
            "more": more,
            "total": len(order_sns),
        },
    }


def order_detail_response(order_sn: str, item_list: list[dict] | None = None) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": {
                "order_list": [
                    {
                        "order_sn": order_sn,
                        "order_status": "COMPLETED",
                        "payment_status": "paid",
                        "currency": "IDR",
                        "total_amount": 250000,
                        "estimated_shipping_fee": 15000,
                        "buyer_paid_shipping_fee": 15000,
                        "seller_discount": 10000,
                        "shopee_discount": 5000,
                        "create_time": 1700000000,
                        "pay_time": 1700000100,
                        "item_list": item_list or [],
                    }
                ]
            },
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": {
            "order_list": [
                {
                    "order_sn": order_sn,
                    "order_status": "COMPLETED",
                    "payment_status": "paid",
                    "currency": "IDR",
                    "total_amount": 250000,
                    "estimated_shipping_fee": 15000,
                    "buyer_paid_shipping_fee": 15000,
                    "seller_discount": 10000,
                    "shopee_discount": 5000,
                    "create_time": 1700000000,
                    "pay_time": 1700000100,
                    "item_list": item_list or [],
                }
            ]
        },
    }


def order_income_response(order_sn: str) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": {
                "order_income_list": [
                    {
                        "order_sn": order_sn,
                        "payment_method": "QRIS",
                        "escrow_status": "RELEASED",
                        "escrow_amount": 255000,
                        "escrow_release_time": 1700001000,
                        "income_details": {
                            "buyer_total_amount": 255000,
                            "commission": 12750,
                            "service_fee": 2550,
                            "seller_shipping_discount": 0,
                            "voucher_amount": 0,
                            "items_total": 250000,
                            "shipping_fee": 15000,
                        },
                    }
                ]
            },
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": {
            "order_income_list": [
                {
                    "order_sn": order_sn,
                    "payment_method": "QRIS",
                    "escrow_status": "RELEASED",
                    "escrow_amount": 255000,
                    "escrow_release_time": 1700001000,
                    "income_details": {
                        "buyer_total_amount": 255000,
                        "commission": 12750,
                        "service_fee": 2550,
                        "seller_shipping_discount": 0,
                        "voucher_amount": 0,
                        "items_total": 250000,
                        "shipping_fee": 15000,
                    },
                }
            ]
        },
    }


def shop_info_response() -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": {
                "shop_id": 123456789,
                "shop_name": "Test Shopee Shop",
                "region": "ID",
                "status": "active",
            },
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": {
            "shop_id": 123456789,
            "shop_name": "Test Shopee Shop",
            "region": "ID",
            "status": "active",
        },
    }


def sample_item(item_id: str = "123", sku: str = "SKU-001") -> dict:
    return {
        "item_id": item_id,
        "item_name": "Test Product",
        "item_sku": sku,
        "model_id": "456",
        "model_name": "Default Model",
        "model_sku": f"{sku}-MODEL",
        "quantity": 2,
        "original_price": 125000,
        "paid_price": 125000,
        "seller_discount": 5000,
        "shopee_discount": 0,
    }


def order_detail_with_items_response(order_sn: str = "250101ABC123") -> dict:
    return order_detail_response(order_sn, item_list=[sample_item()])
