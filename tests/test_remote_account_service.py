#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RemoteAccountService 单元测试（用假的 HTTP 传输替代真实网络）。"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib import error as urlerror

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_account_service import AccountError
from remote_account_service import RemoteAccountService


FIXED_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, payload):
        self._data = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_service(monkeypatch, handler):
    service = RemoteAccountService(
        "http://example.test", device_id="dev123", now=lambda: FIXED_NOW
    )

    def fake_urlopen(req, timeout=None):
        return handler(req)

    monkeypatch.setattr(
        "remote_account_service.urlrequest.urlopen", fake_urlopen
    )
    return service


def test_current_state_augments_remaining_days(monkeypatch):
    expires = (FIXED_NOW + timedelta(days=30)).isoformat()
    payload = {
        "deviceId": "dev123",
        "user": {
            "email": "a@b.com",
            "displayName": "A",
            "subscription": {"planName": "专业会员", "expiresAt": expires},
            "redeemedCodes": [],
        },
    }
    service = make_service(monkeypatch, lambda req: FakeResponse(payload))
    state = service.current_state()
    assert state["user"]["isPremium"] is True
    assert state["user"]["remainingDays"] == 30
    assert state["user"]["subscription"]["remainingDays"] == 30


def test_expired_subscription_becomes_free(monkeypatch):
    expires = (FIXED_NOW - timedelta(days=1)).isoformat()
    payload = {
        "deviceId": "dev123",
        "user": {
            "email": "a@b.com",
            "displayName": "A",
            "subscription": {"planName": "专业会员", "expiresAt": expires},
            "redeemedCodes": [],
        },
    }
    service = make_service(monkeypatch, lambda req: FakeResponse(payload))
    state = service.current_state()
    assert state["user"]["isPremium"] is False
    assert state["user"]["subscription"] is None
    assert state["user"]["remainingDays"] == 0


def test_current_state_offline_returns_guest(monkeypatch):
    def boom(req):
        raise urlerror.URLError("connection refused")

    service = make_service(monkeypatch, boom)
    state = service.current_state()
    assert state["user"] is None
    assert state.get("offline") is True


def test_http_error_becomes_account_error(monkeypatch):
    def raise_http(req):
        body = BytesIO(json.dumps({"detail": "邮箱或密码不正确。"}).encode("utf-8"))
        raise urlerror.HTTPError(req.full_url, 401, "Unauthorized", {}, body)

    service = make_service(monkeypatch, raise_http)
    with pytest.raises(AccountError) as exc:
        service.login("a@b.com", "secret1")
    assert "邮箱或密码不正确" in str(exc.value)


def test_redeem_returns_message(monkeypatch):
    payload = {
        "deviceId": "dev123",
        "user": {"email": "a@b.com", "displayName": "A", "subscription": None, "redeemedCodes": ["X"]},
        "message": "专业会员已开通，有效期 365 天。",
    }
    service = make_service(monkeypatch, lambda req: FakeResponse(payload))
    result = service.redeem_card("wincleaner-vip-365d")
    assert result["message"].startswith("专业会员已开通")
    assert result["state"]["user"]["email"] == "a@b.com"


def test_redeem_empty_code_rejected(monkeypatch):
    service = make_service(monkeypatch, lambda req: FakeResponse({}))
    with pytest.raises(AccountError):
        service.redeem_card("   ")
