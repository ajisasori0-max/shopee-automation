"""Unit tests for the Shopee API client."""

import pytest

from commerceos.connectors.shopee.client import ShopeeApiClient, generate_shopee_sign


class FakeResponse:
    def __init__(self, status_code, body, text=None):
        self.status_code = status_code
        self._body = body
        self.text = text or str(body)

    def json(self):
        return self._body


@pytest.fixture
def fake_transport():
    responses = []

    def request_fn(method, url, params, body):
        if not responses:
            raise RuntimeError("No more fake responses queued")
        return responses.pop(0)

    def enqueue(response):
        responses.append(response)

    return request_fn, enqueue


@pytest.fixture
def client(fake_transport):
    request_fn, _ = fake_transport
    return ShopeeApiClient(
        partner_id=123456,
        partner_key="fake-partner-key",
        shop_id=789012,
        access_token="fake-access-token",
        sandbox=True,
        request_fn=request_fn,
    )


def test_generate_shopee_sign_for_public_api():
    sign = generate_shopee_sign(
        partner_id=123,
        partner_key="secret",
        path="/api/v2/auth/access_token/get",
        timestamp=1000,
    )
    assert sign and len(sign) == 64


def test_generate_shopee_sign_for_shop_api():
    sign = generate_shopee_sign(
        partner_id=123,
        partner_key="secret",
        path="/api/v2/shop/get_shop_info",
        timestamp=1000,
        access_token="token",
        shop_id=456,
    )
    assert sign and len(sign) == 64


def test_get_shop_info(client, fake_transport):
    request_fn, enqueue = fake_transport
    enqueue(FakeResponse(200, {"error": "", "response": {"shop_name": "Test"}}))

    result = client.get_shop_info()

    assert result["ok"] is True
    assert result["response"]["shop_name"] == "Test"


def test_get_order_list(client, fake_transport):
    request_fn, enqueue = fake_transport
    enqueue(FakeResponse(200, {
        "error": "",
        "response": {
            "order_sn_list": ["ORDER-1"],
            "next_cursor": "cursor-1",
            "more": True,
        },
    }))

    result = client.get_order_list(
        time_from=1700000000,
        time_to=1700003600,
        cursor="cursor-0",
    )

    assert result["ok"] is True
    assert result["response"]["order_sn_list"] == ["ORDER-1"]


def test_parse_response_handles_non_json():
    # _parse_response is private; exercise it through a request that returns bad JSON
    def transport(method, url, params, body):
        class BadResponse:
            status_code = 200
            text = "not-json"
            def json(self):
                raise ValueError("bad json")
        return BadResponse()

    client = ShopeeApiClient(
        partner_id=1,
        partner_key="k",
        shop_id=1,
        request_fn=transport,
    )
    result = client.get_shop_info()
    assert result["ok"] is True
    assert result["response"] == {}


def test_api_error_returns_not_ok(client, fake_transport):
    request_fn, enqueue = fake_transport
    enqueue(FakeResponse(200, {"error": "invalid_params", "message": "bad request"}))

    result = client.get_shop_info()

    assert result["ok"] is False
    assert result["error"] == "invalid_params"
