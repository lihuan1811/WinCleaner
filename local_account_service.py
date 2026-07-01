#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""本地账号、登录和会员卡密服务。"""

from __future__ import annotations

import json
import os
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


# 会员套餐（卡种）与有效天数
PLAN_TIERS = {
    "体验卡": 3,
    "周卡": 7,
    "月卡": 30,
    "季卡": 90,
    "年卡": 365,
}

# 注册赠送的体验卡
TRIAL_PLAN_NAME = "体验卡"
TRIAL_DAYS = PLAN_TIERS[TRIAL_PLAN_NAME]

# 离线兜底用的演示激活码（真实激活码由服务端管理后台生成）
DEMO_CARD_CODES = {
    "WINCLEANER-WEEK-DEMO": ("周卡", 7),
    "WINCLEANER-MONTH-DEMO": ("月卡", 30),
    "WINCLEANER-QUARTER-DEMO": ("季卡", 90),
    "WINCLEANER-YEAR-DEMO": ("年卡", 365),
}


class AccountError(Exception):
    """账号业务错误，消息可直接展示给用户。"""


class LocalAccountService:
    def __init__(self, store_path=None, now=None):
        self.store_path = Path(store_path) if store_path else self.default_store_path()
        self.now = now or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def default_store_path():
        if os.name == "nt":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            return Path(base) / "WinCleaner" / "account.json"
        return Path.home() / ".wincleaner" / "account.json"

    @staticmethod
    def normalize_email(email):
        return (email or "").strip().lower()

    @staticmethod
    def hash_password(email, password):
        return hashlib.sha256(f"{email}::{password}".encode("utf-8")).hexdigest()

    @staticmethod
    def iso(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @staticmethod
    def parse_dt(value):
        if not value:
            return None
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def validate_email(self, email):
        if "@" not in email or "." not in email:
            raise AccountError("请输入有效邮箱。")

    def validate_password(self, password):
        if len(password or "") < 6:
            raise AccountError("密码至少需要 6 位。")

    def empty_store(self):
        return {
            "deviceId": hashlib.sha256(str(uuid.getnode()).encode("utf-8")).hexdigest()[:12],
            "users": [],
            "currentEmail": "",
        }

    def load_store(self):
        if not self.store_path.exists():
            return self.empty_store()
        try:
            with self.store_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return self.empty_store()
            data.setdefault("deviceId", self.empty_store()["deviceId"])
            data.setdefault("users", [])
            data.setdefault("currentEmail", "")
            return data
        except (OSError, json.JSONDecodeError):
            return self.empty_store()

    def save_store(self, store):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)

    def user_by_email(self, store, email):
        for user in store.get("users", []):
            if user.get("email") == email:
                return user
        return None

    def replace_user(self, store, updated_user):
        users = []
        replaced = False
        for user in store.get("users", []):
            if user.get("email") == updated_user.get("email"):
                users.append(updated_user)
                replaced = True
            else:
                users.append(user)
        if not replaced:
            users.append(updated_user)
        store["users"] = users
        return store

    def current_user(self, store):
        return self.user_by_email(store, store.get("currentEmail", ""))

    def state_from_store(self, store):
        return {
            "deviceId": store.get("deviceId", ""),
            "user": self.user_state(self.current_user(store)),
        }

    def user_state(self, user):
        if not user:
            return None
        subscription = self.subscription_state(user.get("subscription"))
        return {
            "email": user.get("email", ""),
            "displayName": user.get("displayName", ""),
            "subscription": subscription,
            "isPremium": bool(subscription),
            "remainingDays": subscription["remainingDays"] if subscription else 0,
            "redeemedCodes": list(user.get("redeemedCodes", [])),
        }

    def subscription_state(self, subscription):
        if not subscription:
            return None
        expires_at = self.parse_dt(subscription.get("expiresAt"))
        if not expires_at or expires_at <= self.now():
            return None
        remaining = max(0, (expires_at - self.now()).days)
        return {
            "planName": subscription.get("planName", "专业会员"),
            "activatedAt": subscription.get("activatedAt", ""),
            "expiresAt": self.iso(expires_at),
            "remainingDays": remaining,
        }

    def current_state(self):
        return self.state_from_store(self.load_store())

    def register(self, email, password, display_name=""):
        email = self.normalize_email(email)
        display_name = (display_name or "").strip() or email.split("@")[0]
        self.validate_email(email)
        self.validate_password(password)

        store = self.load_store()
        if self.user_by_email(store, email):
            raise AccountError("这个邮箱已经注册，请直接登录。")

        now = self.now()
        user = {
            "email": email,
            "displayName": display_name,
            "passwordHash": self.hash_password(email, password),
            "createdAt": self.iso(now),
            # 新账号赠送一次体验卡
            "subscription": {
                "planName": TRIAL_PLAN_NAME,
                "activatedAt": self.iso(now),
                "expiresAt": self.iso(now + timedelta(days=TRIAL_DAYS)),
            },
            "redeemedCodes": [],
        }
        store["users"].append(user)
        store["currentEmail"] = email
        self.save_store(store)
        return self.state_from_store(store)

    def login(self, email, password):
        email = self.normalize_email(email)
        self.validate_email(email)
        self.validate_password(password)

        store = self.load_store()
        user = self.user_by_email(store, email)
        if not user or user.get("passwordHash") != self.hash_password(email, password):
            raise AccountError("邮箱或密码不正确。")
        store["currentEmail"] = email
        self.save_store(store)
        return self.state_from_store(store)

    def logout(self):
        store = self.load_store()
        store["currentEmail"] = ""
        self.save_store(store)
        return self.state_from_store(store)

    def redeem_card(self, raw_code):
        code = (raw_code or "").strip().upper()
        if not code:
            raise AccountError("卡密不能为空。")
        if code not in DEMO_CARD_CODES:
            raise AccountError("卡密不存在或格式不正确。")

        store = self.load_store()
        user = self.current_user(store)
        if not user:
            raise AccountError("请先登录或注册账户，再兑换会员卡。")
        if code in user.get("redeemedCodes", []):
            raise AccountError("这张会员卡已经兑换过。")

        plan_name, days = DEMO_CARD_CODES[code]
        now = self.now()
        existing = self.subscription_state(user.get("subscription"))
        start_at = self.parse_dt(existing["expiresAt"]) if existing else now
        if start_at < now:
            start_at = now

        user["subscription"] = {
            "planName": plan_name,
            "activatedAt": self.iso(now),
            "expiresAt": self.iso(start_at + timedelta(days=days)),
        }
        user.setdefault("redeemedCodes", []).append(code)
        store = self.replace_user(store, user)
        self.save_store(store)
        return {
            "state": self.state_from_store(store),
            "message": f"{plan_name}已开通，有效期 {days} 天。",
        }
