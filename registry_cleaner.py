#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Windows 注册表安全清理服务。

只扫描可以明确判定为“无效引用”的两类条目：
  1. 缺失的共享 DLL —— SharedDLLs 中指向已不存在文件的记录。
  2. 应用程序卸载残留 —— 安装目录已删除、且卸载命令/图标目标也不存在的卸载项。

删除前会用 ``reg export`` 把对应的注册表键导出为 .reg 备份，便于随时还原。
其余高风险类别（CLSID、默认图标等）不在此自动删除，交由界面用“检查”方式
打开注册表编辑器人工处理。
"""

import os
import sys
import subprocess
from datetime import datetime

try:
    import winreg
except ImportError:  # pragma: no cover - 非 Windows 平台
    winreg = None


def _hidden_kwargs():
    if not sys.platform.startswith("win"):
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


HIVE_HANDLES = {}
if winreg is not None:
    HIVE_HANDLES = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKU": winreg.HKEY_USERS,
    }

HIVE_FULL_NAMES = {
    "HKLM": "HKEY_LOCAL_MACHINE",
    "HKCU": "HKEY_CURRENT_USER",
    "HKCR": "HKEY_CLASSES_ROOT",
    "HKU": "HKEY_USERS",
}

CATEGORY_SHARED_DLL = "缺失的共享 DLL"
CATEGORY_UNINSTALL = "应用程序卸载残留"
CATEGORY_APP_PATHS = "无效的应用程序路径"


def first_path_token(command):
    """从卸载命令/图标字符串里提取出第一个文件路径。"""
    if not command:
        return ""
    text = os.path.expandvars(str(command)).strip()
    if not text:
        return ""
    if text.startswith('"'):
        path = text[1:].split('"', 1)[0]
    else:
        path = text.split(" ", 1)[0]
    # DisplayIcon 常见形如 "C:\\app\\a.exe,0"，去掉图标索引
    path = path.split(",", 1)[0]
    return path.strip()


def target_exists(command):
    path = first_path_token(command)
    return bool(path) and os.path.exists(path)


class RegistryCleanerService:
    """扫描并清理无效的注册表引用（仅 Windows 生效）。"""

    def __init__(self, is_windows=None):
        if is_windows is None:
            is_windows = sys.platform.startswith("win")
        self.is_windows = is_windows

    def available(self):
        return bool(self.is_windows and winreg is not None)

    # ------------------------------------------------------------------ 扫描
    def scan(self, limit_per_category=200):
        if not self.available():
            return []
        issues = []
        issues.extend(self._scan_shared_dlls(limit_per_category))
        issues.extend(self._scan_uninstall_residue(limit_per_category))
        issues.extend(self._scan_app_paths(limit_per_category))
        return issues

    def _scan_shared_dlls(self, limit):
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\SharedDLLs"
        issues = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
                _sub, value_count, _modified = winreg.QueryInfoKey(key)
                for index in range(value_count):
                    if len(issues) >= limit:
                        break
                    try:
                        name, _data, _vtype = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    if not name:
                        continue
                    if os.path.exists(os.path.expandvars(name)):
                        continue
                    issues.append({
                        "category": CATEGORY_SHARED_DLL,
                        "hive": "HKLM",
                        "subkey": subkey,
                        "value_name": name,
                        "kind": "value",
                        "detail": name,
                    })
        except OSError:
            return []
        return issues

    def _scan_uninstall_residue(self, limit):
        locations = [
            ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        issues = []
        for hive_name, base in locations:
            root = HIVE_HANDLES[hive_name]
            try:
                with winreg.OpenKey(root, base) as parent:
                    sub_count, _values, _modified = winreg.QueryInfoKey(parent)
                    for index in range(sub_count):
                        if len(issues) >= limit:
                            break
                        try:
                            child = winreg.EnumKey(parent, index)
                            with winreg.OpenKey(parent, child) as child_key:
                                display = self._read_value(child_key, "DisplayName")
                                install_loc = self._read_value(child_key, "InstallLocation")
                                uninstall = self._read_value(child_key, "UninstallString")
                                icon = self._read_value(child_key, "DisplayIcon")
                        except OSError:
                            continue

                        if not install_loc:
                            continue
                        location = os.path.expandvars(str(install_loc).strip().strip('"'))
                        if not location or os.path.isdir(location):
                            continue
                        # 安装目录已不存在，但仍有有效卸载命令/图标时不算残留
                        if uninstall and target_exists(uninstall):
                            continue
                        if icon and target_exists(icon):
                            continue
                        issues.append({
                            "category": CATEGORY_UNINSTALL,
                            "hive": hive_name,
                            "subkey": f"{base}\\{child}",
                            "value_name": None,
                            "kind": "key",
                            "detail": display or child,
                        })
            except OSError:
                continue
        return issues

    def _scan_app_paths(self, limit):
        locations = [
            ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        issues = []
        for hive_name, base in locations:
            root = HIVE_HANDLES[hive_name]
            try:
                with winreg.OpenKey(root, base) as parent:
                    sub_count, _values, _modified = winreg.QueryInfoKey(parent)
                    for index in range(sub_count):
                        if len(issues) >= limit:
                            break
                        try:
                            child = winreg.EnumKey(parent, index)
                            with winreg.OpenKey(parent, child) as child_key:
                                target = self._read_value(child_key, "")
                        except OSError:
                            continue
                        if not target:
                            continue
                        path = os.path.expandvars(str(target).strip().strip('"'))
                        if not path or os.path.exists(path):
                            continue
                        issues.append({
                            "category": CATEGORY_APP_PATHS,
                            "hive": hive_name,
                            "subkey": f"{base}\\{child}",
                            "value_name": None,
                            "kind": "key",
                            "detail": child,
                        })
            except OSError:
                continue
        return issues

    @staticmethod
    def _read_value(key, name):
        try:
            value, _vtype = winreg.QueryValueEx(key, name or "")
            return value
        except OSError:
            return None

    # ------------------------------------------------------------ 备份 + 删除
    def issue_location(self, issue):
        location = f"{issue.get('hive', '')}\\{issue.get('subkey', '')}"
        if issue.get("value_name"):
            location += f"  ::  {issue['value_name']}"
        return location

    def export_backup(self, issue, backup_dir):
        """删除前导出整棵注册表键作为 .reg 备份，返回备份文件路径。"""
        if not self.available():
            return None
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except OSError:
            return None
        full_key = f"{HIVE_FULL_NAMES[issue['hive']]}\\{issue['subkey']}"
        safe_name = "".join(c if c.isalnum() else "_" for c in issue["subkey"])[-80:]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"reg_{stamp}_{safe_name}.reg")
        try:
            subprocess.run(
                ["reg", "export", full_key, backup_path, "/y"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **_hidden_kwargs(),
            )
        except Exception:  # pragma: no cover - 取决于系统环境
            return None
        return backup_path if os.path.exists(backup_path) else None

    def delete_issue(self, issue):
        if not self.available():
            return False
        root = HIVE_HANDLES.get(issue.get("hive"))
        if root is None:
            return False
        try:
            if issue.get("kind") == "value":
                with winreg.OpenKey(root, issue["subkey"], 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, issue["value_name"])
            else:
                self._delete_tree(root, issue["subkey"])
            return True
        except OSError:
            return False

    def _delete_tree(self, root, subkey):
        """递归删除子键，再删除自身（DeleteKey 不能删非空键）。"""
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                    except OSError:
                        break
                    self._delete_tree(root, f"{subkey}\\{child}")
        except OSError:
            pass
        winreg.DeleteKey(root, subkey)
