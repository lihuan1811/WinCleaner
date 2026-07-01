#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""远程账号服务：调用服务器 API 完成登录/注册/兑换，接口与本地服务保持一致。"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from urllib import error as urlerror
from urllib import request as urlrequest

from local_account_service import AccountError


class RemoteAccountService:
    """与 LocalAccountService 暴露相同的方法，但请求真实后端接口。

    服务器通过 deviceId 维护登录会话，因此本地无需保存密码，只需保存稳定的
    设备标识。业务错误（400/401/404/409 等）会转换成 AccountError，方便 UI 直接展示。
    """

    def __init__(self, base_url, device_id=None, timeout=10, now=None):
        self.base_url = (base_url or "").rstrip("/")
        self.device_id = device_id or self.default_device_id()
        self.timeout = timeout
        self.now = now or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def default_device_id():
        return hashlib.sha256(str(uuid.getnode()).encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def parse_dt(value):
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _request(self, method, path, payload=None):
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urlrequest.Request(url, data=data, headers=headers, method=method)
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urlerror.HTTPError as exc:
            detail = None
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("detail")
            except Exception:
                detail = None
            raise AccountError(detail or f"服务器返回错误（{exc.code}）。")
        except urlerror.URLError:
            raise AccountError("无法连接服务器，请检查网络后重试。")
        except (TimeoutError, OSError):
            raise AccountError("网络请求超时，请稍后重试。")
        except json.JSONDecodeError:
            raise AccountError("服务器返回数据异常。")

    def _augment_state(self, state):
        """补齐 UI 需要的 isPremium / remainingDays 字段。"""
        if not isinstance(state, dict):
            return {"deviceId": self.device_id, "user": None}
        user = state.get("user")
        if not user:
            return state
        subscription = user.get("subscription")
        remaining = 0
        if subscription:
            expires_at = self.parse_dt(subscription.get("expiresAt"))
            if expires_at and expires_at > self.now():
                remaining = max(0, (expires_at - self.now()).days)
                subscription["remainingDays"] = remaining
            else:
                user["subscription"] = None
                subscription = None
        user["isPremium"] = bool(subscription)
        user["remainingDays"] = remaining
        return state

    def current_state(self):
        """读取当前设备的登录状态；网络异常时返回游客状态，避免启动崩溃。"""
        try:
            state = self._request("GET", f"/api/account/state/{self.device_id}")
            return self._augment_state(state)
        except AccountError:
            return {"deviceId": self.device_id, "user": None, "offline": True}

    def register(self, email, password, display_name=""):
        payload = {
            "email": email,
            "password": password,
            "displayName": display_name,
            "deviceId": self.device_id,
        }
        return self._augment_state(self._request("POST", "/api/auth/register", payload))

    def login(self, email, password):
        payload = {
            "email": email,
            "password": password,
            "deviceId": self.device_id,
        }
        return self._augment_state(self._request("POST", "/api/auth/login", payload))

    def logout(self):
        payload = {"deviceId": self.device_id}
        return self._augment_state(self._request("POST", "/api/auth/logout", payload))

    def redeem_card(self, raw_code):
        code = (raw_code or "").strip().upper()
        if not code:
            raise AccountError("卡密不能为空。")
        payload = {"code": code, "deviceId": self.device_id}
        result = self._request("POST", "/api/cards/redeem", payload)
        message = result.pop("message", "兑换成功。") if isinstance(result, dict) else "兑换成功。"
        state = self._augment_state(result)
        return {"state": state, "message": message}
