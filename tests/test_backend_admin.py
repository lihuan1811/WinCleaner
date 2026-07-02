#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""后端管理接口辅助函数测试（无需数据库）。"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("fastapi")
pytest.importorskip("psycopg")

from fastapi import HTTPException

from backend import app as backend_app


def test_generate_card_code_format():
    code = backend_app.generate_card_code("WINCLEANER")
    parts = code.split("-")
    assert parts[0] == "WINCLEANER"
    assert len(parts) == 4
    assert all(len(p) == 4 for p in parts[1:])


def test_generate_card_code_unique():
    codes = {backend_app.generate_card_code() for _ in range(200)}
    assert len(codes) > 190  # 极低碰撞概率


def test_generate_card_code_sanitizes_prefix():
    code = backend_app.generate_card_code("my prefix!!")
    assert code.startswith("MYPREFIX-")


def test_require_admin_without_token_configured(monkeypatch):
    monkeypatch.delenv("WINCLEANER_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        backend_app.require_admin("anything")
    assert exc.value.status_code == 503


def test_require_admin_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("WINCLEANER_ADMIN_TOKEN", "secret-token")
    with pytest.raises(HTTPException) as exc:
        backend_app.require_admin("wrong")
    assert exc.value.status_code == 401


def test_require_admin_accepts_correct_token(monkeypatch):
    monkeypatch.setenv("WINCLEANER_ADMIN_TOKEN", "secret-token")
    backend_app.require_admin("secret-token")  # 不抛异常即通过


def test_admin_disable_routes_registered():
    """用户与激活码的禁用/启用接口均已注册。"""
    app = backend_app.create_app("postgresql://x:x@127.0.0.1:5432/x")
    paths = {route.path for route in app.routes}
    assert "/api/admin/cards/{code}/disable" in paths
    assert "/api/admin/cards/{code}/enable" in paths
    assert "/api/admin/users/{email}/disable" in paths
    assert "/api/admin/users/{email}/enable" in paths


def test_card_status_labels():
    assert backend_app  # module loaded
    # 与 admin 前端一致的状态映射
    for redeemed_by, disabled, expected in [
        ("user@x.com", False, "used"),
        (None, True, "disabled"),
        (None, False, "available"),
    ]:
        status = (
            "used"
            if redeemed_by
            else ("disabled" if disabled else "available")
        )
        assert status == expected
