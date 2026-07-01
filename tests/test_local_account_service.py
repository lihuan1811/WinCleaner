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
    # 新账号赠送一次体验卡
    assert state["user"]["subscription"]["planName"] == "体验卡"
    assert state["user"]["remainingDays"] == 3

    # 体验卡未过期时兑换月卡（30天）会在体验到期日基础上续期 -> 3 + 30
    result = service.redeem_card("wincleaner-month-demo")
    assert result["state"]["user"]["subscription"]["planName"] == "月卡"
    assert result["state"]["user"]["remainingDays"] == 33
    assert "WINCLEANER-MONTH-DEMO" in result["state"]["user"]["redeemedCodes"]

    restored = LocalAccountService(
        store_path=store_path,
        now=lambda: datetime(2026, 6, 30, tzinfo=timezone.utc),
    )
    logged_in = restored.login("admin@example.com", "123456")
    assert logged_in["user"]["subscription"]["planName"] == "月卡"


def test_reject_duplicate_card_wrong_password_and_guest_redeem(tmp_path):
    service = LocalAccountService(
        store_path=tmp_path / "account.json",
        now=lambda: datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    with pytest.raises(AccountError, match="请先登录或注册账户"):
        service.redeem_card("WINCLEANER-MONTH-DEMO")

    service.register("team@example.com", "123456", "Team")
    service.redeem_card("WINCLEANER-MONTH-DEMO")

    with pytest.raises(AccountError, match="已经兑换过"):
        service.redeem_card("WINCLEANER-MONTH-DEMO")

    service.logout()
    with pytest.raises(AccountError, match="名称或密码不正确"):
        service.login("team@example.com", "wrong-password")


def test_register_name_rules(tmp_path):
    service = LocalAccountService(
        store_path=tmp_path / "account.json",
        now=lambda: datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    # 少于 6 位
    with pytest.raises(AccountError, match="至少需要 6 位"):
        service.register("abc", "123456")

    # 含中文
    with pytest.raises(AccountError, match="不能包含中文"):
        service.register("张三abcdef", "123456")

    # 正常注册
    service.register("username1", "123456")
    # 名称不能重复（大小写不敏感）
    with pytest.raises(AccountError, match="已被注册"):
        service.register("UserName1", "123456")
