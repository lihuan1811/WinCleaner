from __future__ import annotations

import hashlib
import os
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field


DEFAULT_DATABASE_URL = "postgresql://wincleaner:wincleaner@127.0.0.1:5432/wincleaner"

DEFAULT_CARD_PLANS = {
    "WINCLEANER-VIP-30D": ("专业会员", 30),
    "WINCLEANER-VIP-365D": ("专业会员", 365),
    "WINCLEANER-TEAM-365D": ("企业会员", 365),
}


def default_database_url() -> str:
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("WINCLEANER_DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def row_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    return datetime.fromtimestamp(0, tz=timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> None:
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="请输入有效邮箱。")


def validate_password(password: str) -> None:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少需要 6 位。")


def hash_password(email: str, password: str) -> str:
    raw = f"{email}::{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Database:
    database_url: str
    min_size: int = 1
    max_size: int = 5
    _pool: ConnectionPool | None = None

    def open(self) -> None:
        if self._pool is not None:
            return
        self._pool = ConnectionPool(
            conninfo=self.database_url,
            min_size=self.min_size,
            max_size=self.max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def close(self) -> None:
        if self._pool is None:
            return
        self._pool.close()
        self._pool = None

    @contextmanager
    def connect(self) -> Iterator[Connection[DictRow]]:
        if self._pool is None:
            self.open()
        assert self._pool is not None
        with self._pool.connection() as connection:
            with connection.transaction():
                yield connection


def init_database(database: Database) -> None:
    with database.connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_email TEXT PRIMARY KEY REFERENCES users(email)
                    ON DELETE CASCADE,
                plan_name TEXT NOT NULL,
                activated_at TIMESTAMPTZ NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS card_codes (
                code TEXT PRIMARY KEY,
                plan_name TEXT NOT NULL,
                days INTEGER NOT NULL CHECK (days > 0),
                redeemed_by TEXT REFERENCES users(email) ON DELETE SET NULL,
                redeemed_at TIMESTAMPTZ
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                device_id TEXT PRIMARY KEY,
                current_email TEXT REFERENCES users(email) ON DELETE SET NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS subscriptions_expires_at_idx
            ON subscriptions (expires_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS card_codes_redeemed_by_idx
            ON card_codes (redeemed_by)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS sessions_current_email_idx
            ON sessions (current_email)
            """
        )
        for code, (plan_name, days) in DEFAULT_CARD_PLANS.items():
            connection.execute(
                """
                INSERT INTO card_codes (code, plan_name, days)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                    plan_name = EXCLUDED.plan_name,
                    days = EXCLUDED.days
                """,
                (code, plan_name, days),
            )


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = Field(alias="displayName")
    device_id: str = Field(alias="deviceId")


class LoginRequest(BaseModel):
    email: str
    password: str
    device_id: str = Field(alias="deviceId")


class DeviceRequest(BaseModel):
    device_id: str = Field(alias="deviceId")


class RedeemCardRequest(BaseModel):
    code: str
    device_id: str = Field(alias="deviceId")


def create_app(database_url: str | None = None) -> FastAPI:
    selected_database_url = database_url or default_database_url()
    database = Database(selected_database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.open()
        init_database(database)
        app.state.database = database
        try:
            yield
        finally:
            database.close()

    app = FastAPI(
        title="WinCleaner Account API",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def active_database() -> Database:
        active = getattr(app.state, "database", None)
        if active is None:
            raise HTTPException(status_code=503, detail="数据库尚未连接。")
        return active

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": "postgresql"}

    @app.get("/api/account/state/{device_id}")
    def account_state(device_id: str) -> dict[str, object | None]:
        with active_database().connect() as connection:
            return load_state(connection, device_id)

    @app.post("/api/auth/register")
    def register(request: RegisterRequest) -> dict[str, object | None]:
        email = normalize_email(request.email)
        validate_email(email)
        validate_password(request.password)
        display_name = request.display_name.strip() or email.split("@")[0]
        now = utc_now()
        password_hash = hash_password(email, request.password)

        with active_database().connect() as connection:
            inserted = connection.execute(
                """
                INSERT INTO users (email, display_name, password_hash, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING email
                """,
                (email, display_name, password_hash, now),
            ).fetchone()
            if inserted is None:
                raise HTTPException(status_code=409, detail="这个邮箱已经注册，请直接登录。")
            save_session(connection, request.device_id, email)
            return load_state(connection, request.device_id)

    @app.post("/api/auth/login")
    def login(request: LoginRequest) -> dict[str, object | None]:
        email = normalize_email(request.email)
        validate_email(email)
        validate_password(request.password)

        with active_database().connect() as connection:
            user = connection.execute(
                "SELECT password_hash FROM users WHERE email = %s",
                (email,),
            ).fetchone()
            if user is None or user["password_hash"] != hash_password(
                email,
                request.password,
            ):
                raise HTTPException(status_code=401, detail="邮箱或密码不正确。")
            save_session(connection, request.device_id, email)
            return load_state(connection, request.device_id)

    @app.post("/api/auth/logout")
    def logout(request: DeviceRequest) -> dict[str, object | None]:
        with active_database().connect() as connection:
            save_session(connection, request.device_id, None)
            return load_state(connection, request.device_id)

    @app.post("/api/cards/redeem")
    def redeem_card(request: RedeemCardRequest) -> dict[str, object | None]:
        code = request.code.strip().upper()
        if not code:
            raise HTTPException(status_code=400, detail="卡密不能为空。")

        with active_database().connect() as connection:
            session = connection.execute(
                "SELECT current_email FROM sessions WHERE device_id = %s",
                (request.device_id,),
            ).fetchone()
            email = session["current_email"] if session else None
            if not email:
                raise HTTPException(status_code=401, detail="请先登录或注册账户，再兑换会员卡。")

            card = connection.execute(
                """
                SELECT code, plan_name, days, redeemed_by
                FROM card_codes
                WHERE code = %s
                FOR UPDATE
                """,
                (code,),
            ).fetchone()
            if card is None:
                raise HTTPException(status_code=404, detail="卡密不存在或格式不正确。")
            if card["redeemed_by"]:
                raise HTTPException(status_code=409, detail="这张会员卡已经兑换过。")

            now = utc_now()
            subscription = connection.execute(
                """
                SELECT expires_at
                FROM subscriptions
                WHERE user_email = %s
                FOR UPDATE
                """,
                (email,),
            ).fetchone()
            start_at = now
            if subscription:
                current_expiry = row_datetime(subscription["expires_at"])
                if current_expiry > now:
                    start_at = current_expiry
            expires_at = start_at + timedelta(days=int(card["days"]))

            connection.execute(
                """
                INSERT INTO subscriptions (
                    user_email, plan_name, activated_at, expires_at
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_email) DO UPDATE SET
                    plan_name = EXCLUDED.plan_name,
                    activated_at = EXCLUDED.activated_at,
                    expires_at = EXCLUDED.expires_at
                """,
                (email, card["plan_name"], now, expires_at),
            )
            connection.execute(
                """
                UPDATE card_codes
                SET redeemed_by = %s, redeemed_at = %s
                WHERE code = %s
                """,
                (email, now, code),
            )
            state = load_state(connection, request.device_id)
            state["message"] = f"{card['plan_name']}已开通，有效期 {card['days']} 天。"
            return state

    return app


def save_session(
    connection: Connection[DictRow],
    device_id: str,
    email: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO sessions (device_id, current_email, updated_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (device_id) DO UPDATE SET
            current_email = EXCLUDED.current_email,
            updated_at = EXCLUDED.updated_at
        """,
        (device_id, email, utc_now()),
    )


def load_state(
    connection: Connection[DictRow],
    device_id: str,
) -> dict[str, object | None]:
    session = connection.execute(
        "SELECT current_email FROM sessions WHERE device_id = %s",
        (device_id,),
    ).fetchone()
    email = session["current_email"] if session else None
    if not email:
        return {"deviceId": device_id, "user": None}

    user = connection.execute(
        "SELECT email, display_name, created_at FROM users WHERE email = %s",
        (email,),
    ).fetchone()
    if user is None:
        save_session(connection, device_id, None)
        return {"deviceId": device_id, "user": None}

    subscription = connection.execute(
        """
        SELECT plan_name, activated_at, expires_at
        FROM subscriptions
        WHERE user_email = %s
        """,
        (email,),
    ).fetchone()
    redeemed_codes = connection.execute(
        """
        SELECT code FROM card_codes
        WHERE redeemed_by = %s
        ORDER BY redeemed_at ASC, code ASC
        """,
        (email,),
    ).fetchall()

    return {
        "deviceId": device_id,
        "user": {
            "email": user["email"],
            "displayName": user["display_name"],
            "createdAt": iso(row_datetime(user["created_at"])),
            "subscription": None
            if subscription is None
            else {
                "planName": subscription["plan_name"],
                "activatedAt": iso(row_datetime(subscription["activated_at"])),
                "expiresAt": iso(row_datetime(subscription["expires_at"])),
            },
            "redeemedCodes": [row["code"] for row in redeemed_codes],
        },
    }


app = create_app()
