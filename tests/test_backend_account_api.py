import os
from urllib.parse import urlparse

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="set TEST_DATABASE_URL to run PostgreSQL backend integration tests",
)


def reset_database() -> None:
    assert TEST_DATABASE_URL is not None
    database_name = urlparse(TEST_DATABASE_URL).path.rsplit("/", maxsplit=1)[-1]
    if not database_name.endswith("_test"):
        pytest.skip("TEST_DATABASE_URL database name must end with _test")
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DROP TABLE IF EXISTS sessions, subscriptions, card_codes, users CASCADE"
            )


def test_register_login_and_redeem_card_persist_to_postgresql() -> None:
    assert TEST_DATABASE_URL is not None
    reset_database()

    with TestClient(create_app(TEST_DATABASE_URL)) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "email": "Admin@Example.com",
                "password": "123456",
                "displayName": "Administrator",
                "deviceId": "device-a",
            },
        )

        assert registered.status_code == 200
        state = registered.json()
        assert state["deviceId"] == "device-a"
        assert state["user"]["email"] == "admin@example.com"
        assert state["user"]["displayName"] == "Administrator"
        assert state["user"]["subscription"] is None

        redeemed = client.post(
            "/api/cards/redeem",
            json={"deviceId": "device-a", "code": "wincleaner-vip-30d"},
        )

        assert redeemed.status_code == 200
        member_state = redeemed.json()
        assert member_state["user"]["subscription"]["planName"] == "专业会员"
        assert "WINCLEANER-VIP-30D" in member_state["user"]["redeemedCodes"]

        logged_out = client.post("/api/auth/logout", json={"deviceId": "device-a"})
        assert logged_out.status_code == 200
        assert logged_out.json()["user"] is None

        logged_in = client.post(
            "/api/auth/login",
            json={
                "email": "admin@example.com",
                "password": "123456",
                "deviceId": "device-a",
            },
        )

        assert logged_in.status_code == 200
        restored = logged_in.json()
        assert restored["user"]["email"] == "admin@example.com"
        assert restored["user"]["subscription"]["planName"] == "专业会员"


def test_reject_duplicate_card_and_wrong_password() -> None:
    assert TEST_DATABASE_URL is not None
    reset_database()

    with TestClient(create_app(TEST_DATABASE_URL)) as client:
        response = client.post(
            "/api/cards/redeem",
            json={"deviceId": "device-b", "code": "WINCLEANER-VIP-30D"},
        )
        assert response.status_code == 401

        client.post(
            "/api/auth/register",
            json={
                "email": "team@example.com",
                "password": "123456",
                "displayName": "Team",
                "deviceId": "device-b",
            },
        )

        first = client.post(
            "/api/cards/redeem",
            json={"deviceId": "device-b", "code": "WINCLEANER-VIP-30D"},
        )
        duplicate = client.post(
            "/api/cards/redeem",
            json={"deviceId": "device-b", "code": "WINCLEANER-VIP-30D"},
        )

        assert first.status_code == 200
        assert duplicate.status_code == 409

        bad_login = client.post(
            "/api/auth/login",
            json={
                "email": "team@example.com",
                "password": "wrong-password",
                "deviceId": "device-b",
            },
        )
        assert bad_login.status_code == 401
