"""Fake Shopee ads API responses for unit testing."""


def campaign_list_response(campaign_ids: list[str]) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": {
                "campaign_list": [{"campaign_id": cid} for cid in campaign_ids],
                "total": len(campaign_ids),
            },
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": {
            "campaign_list": [{"campaign_id": cid} for cid in campaign_ids],
            "total": len(campaign_ids),
        },
    }


def campaign_setting_info_response(campaign_id: str) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": {
                "campaign_list": [
                    {
                        "campaign_id": campaign_id,
                        "common_info": {
                            "ad_name": f"Campaign {campaign_id}",
                            "campaign_status": "ongoing",
                            "campaign_budget": 150000,
                            "ad_type": "manual",
                            "bidding_method": "cpc",
                        },
                        "item_list": [
                            {
                                "ad_id": f"ad-{campaign_id}-1",
                                "item_id": "item-1",
                                "ad_name": f"Ad {campaign_id}-1",
                                "ad_status": "ongoing",
                            }
                        ],
                    }
                ]
            },
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": {
            "campaign_list": [
                {
                    "campaign_id": campaign_id,
                    "common_info": {
                        "ad_name": f"Campaign {campaign_id}",
                        "campaign_status": "ongoing",
                        "campaign_budget": 150000,
                        "ad_type": "manual",
                        "bidding_method": "cpc",
                    },
                    "item_list": [
                        {
                            "ad_id": f"ad-{campaign_id}-1",
                            "item_id": "item-1",
                            "ad_name": f"Ad {campaign_id}-1",
                            "ad_status": "ongoing",
                        }
                    ],
                }
            ]
        },
    }


def ads_daily_performance_response(campaign_id: str, ad_id: str) -> dict:
    return {
        "ok": True,
        "status_code": 200,
        "data": {
            "error": "",
            "message": "success",
            "response": [
                {
                    "campaign_id": campaign_id,
                    "ad_id": ad_id,
                    "date": "17-07-2026",
                    "impression": 12500,
                    "clicks": 340,
                    "direct_order": 12,
                    "expense": 150000,
                    "direct_gmv": 480000,
                    "ctr": 2.72,
                    "cpc": 441,
                    "roas": 3.2,
                }
            ],
            "request_id": "fake-request-id",
        },
        "error": "",
        "response": [
            {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "date": "17-07-2026",
                "impression": 12500,
                "clicks": 340,
                "direct_order": 12,
                "expense": 150000,
                "direct_gmv": 480000,
                "ctr": 2.72,
                "cpc": 441,
                "roas": 3.2,
            }
        ],
    }
