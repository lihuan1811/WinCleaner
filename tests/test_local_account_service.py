from datetime import datetime, timezone

import pytest

from local_account_service import AccountError, LocalAccountService


def test_register_login_redeem_card_and_persist_state(tmp_path):
    store_path = tmp_path / "account.json"
    service = LocalAccountService(
        store_path=store_path,
        now=lambda: datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    state = service.register(
        email="Admin@Example.com",
        password="123456",
        display_name="Administrator",
    )

    assert state["user"]["email"] == "admin@example.com"
    assert state["user"]["displayName"] == "Administrator"
    assert state["user"]["subscription"] is None

    result = service.redeem_card("wincleaner-vip-30d")
    assert result["state"]["user"]["subscription"]["planName"] == "专业会员"
    assert result["state"]["user"]["remainingDays"] == 30
    assert "WINCLEANER-VIP-30D" in result["state"]["user"]["redeemedCodes"]

    restored = LocalAccountService(
        store_path=store_path,
        now=lambda: datetime(2026, 6, 30, tzinfo=timezone.utc),
    )
    logged_in = restored.login("admin@example.com", "123456")
    assert logged_in["user"]["subscription"]["planName"] == "专业会员"


def test_reject_duplicate_card_wrong_password_and_guest_redeem(tmp_path):
    service = LocalAccountService(
        store_path=tmp_path / "account.json",
        now=lambda: datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    with pytest.raises(AccountError, match="请先登录或注册账户"):
        service.redeem_card("WINCLEANER-VIP-30D")

    service.register("team@example.com", "123456", "Team")
    service.redeem_card("WINCLEANER-VIP-30D")

    with pytest.raises(AccountError, match="已经兑换过"):
        service.redeem_card("WINCLEANER-VIP-30D")

    service.logout()
    with pytest.raises(AccountError, match="邮箱或密码不正确"):
        service.login("team@example.com", "wrong-password")
