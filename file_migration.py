#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""个人文件夹迁移服务。

把桌面、文档、下载、图片等用户文件夹从 C 盘迁移到其它磁盘：
1. 将原文件夹内容移动到目标磁盘的新位置；
2. 在原位置创建目录连接点（Windows 使用 junction，其它系统用符号链接），
   这样应用与系统仍能通过原路径访问，实际数据却存放在目标磁盘，从而释放 C 盘空间。

同时支持“还原”：删除连接点、把数据移回原位置。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


IS_WINDOWS = os.name == "nt"

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


class MigrationError(Exception):
    """迁移相关错误，消息可直接展示给用户。"""


class FileMigrationService:
    def __init__(self, home=None, local_appdata=None, appdata=None):
        self.home = home or os.environ.get("USERPROFILE") or os.path.expanduser("~")
        self.local_appdata = (
            local_appdata
            or os.environ.get("LOCALAPPDATA")
            or os.path.join(self.home, "AppData", "Local")
        )
        self.appdata = (
            appdata
            or os.environ.get("APPDATA")
            or os.path.join(self.home, "AppData", "Roaming")
        )

    # ----- 目录清单 -----------------------------------------------------
    def catalog(self):
        home = self.home
        local = self.local_appdata
        return [
            {"key": "desktop", "name": "桌面", "subname": "Desktop", "path": os.path.join(home, "Desktop")},
            {"key": "documents", "name": "我的文档", "subname": "Documents", "path": os.path.join(home, "Documents")},
            {"key": "favorites", "name": "收藏夹", "subname": "Favorites", "path": os.path.join(home, "Favorites")},
            {"key": "inetcache", "name": "IE缓存", "subname": "INetCache", "path": os.path.join(local, "Microsoft", "Windows", "INetCache")},
            {"key": "cookies", "name": "Cookies", "subname": "INetCookies", "path": os.path.join(local, "Microsoft", "Windows", "INetCookies")},
            {"key": "temp", "name": "临时文件", "subname": "Temp", "path": os.path.join(local, "Temp")},
            {"key": "contacts", "name": "联系人", "subname": "Contacts", "path": os.path.join(home, "Contacts")},
            {"key": "downloads", "name": "下载", "subname": "Downloads", "path": os.path.join(home, "Downloads")},
            {"key": "links", "name": "链接", "subname": "Links", "path": os.path.join(home, "Links")},
            {"key": "searches", "name": "搜索", "subname": "Searches", "path": os.path.join(home, "Searches")},
            {"key": "videos", "name": "我的视频", "subname": "Videos", "path": os.path.join(home, "Videos")},
            {"key": "pictures", "name": "我的图片", "subname": "Pictures", "path": os.path.join(home, "Pictures")},
            {"key": "music", "name": "我的音乐", "subname": "Music", "path": os.path.join(home, "Music")},
            {"key": "savedgames", "name": "保存的游戏", "subname": "Saved Games", "path": os.path.join(home, "Saved Games")},
        ]

    def _entry(self, key):
        for entry in self.catalog():
            if entry["key"] == key:
                return entry
        raise MigrationError(f"未知的文件夹项: {key}")

    # ----- 状态查询 -----------------------------------------------------
    def list_folders(self, with_size=True):
        results = []
        for entry in self.catalog():
            path = entry["path"]
            exists = os.path.exists(path)
            migrated = exists and self.is_reparse_point(path)
            target = ""
            size = 0
            if migrated:
                try:
                    target = os.path.realpath(path)
                except OSError:
                    target = ""
                # 已迁移目录的体积以目标位置为准，避免跟随连接点重复统计
                if with_size and target and os.path.exists(target):
                    size = self.directory_size(target)
            elif exists and with_size:
                size = self.directory_size(path)
            results.append(
                {
                    "key": entry["key"],
                    "name": entry["name"],
                    "subname": entry["subname"],
                    "path": path,
                    "exists": exists,
                    "migrated": migrated,
                    "target": target,
                    "size": size,
                }
            )
        return results

    @staticmethod
    def directory_size(path):
        total = 0
        for root, dirs, files in os.walk(path):
            # 不跟随连接点，避免死循环与重复计数
            dirs[:] = [
                d
                for d in dirs
                if not FileMigrationService.is_reparse_point(os.path.join(root, d))
            ]
            for name in files:
                try:
                    fp = os.path.join(root, name)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except OSError:
                    continue
        return total

    @staticmethod
    def is_reparse_point(path):
        """判断是否为连接点 / 符号链接（即已迁移状态）。"""
        if IS_WINDOWS:
            try:
                import ctypes

                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs == -1 or attrs == 0xFFFFFFFF:
                    return False
                return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
            except Exception:
                return os.path.islink(path)
        return os.path.islink(path)

    # ----- 迁移 / 还原 --------------------------------------------------
    def migrate_folder(self, key, target_root, move_files=True):
        entry = self._entry(key)
        src = entry["path"]
        if self.is_reparse_point(src):
            raise MigrationError(f"“{entry['name']}”已经迁移过了。")

        target_root = os.path.abspath(target_root)
        dst = os.path.join(target_root, entry["subname"])

        self._validate_target(src, dst)
        os.makedirs(target_root, exist_ok=True)

        if os.path.exists(src):
            if move_files:
                os.makedirs(dst, exist_ok=True)
                self._merge_move(src, dst)
            else:
                if os.path.isdir(src) and os.listdir(src):
                    raise MigrationError(
                        f"“{entry['name']}”内还有文件，请勾选“转移文件”后再迁移。"
                    )
                os.makedirs(dst, exist_ok=True)
            self._remove_dir(src)
        else:
            os.makedirs(dst, exist_ok=True)

        self._create_link(src, dst)
        return {"key": key, "name": entry["name"], "src": src, "dst": dst}

    def restore_folder(self, key):
        entry = self._entry(key)
        src = entry["path"]
        if not self.is_reparse_point(src):
            raise MigrationError(f"“{entry['name']}”未处于迁移状态，无需还原。")

        target = os.path.realpath(src)
        # 删除连接点本身（不会删除目标数据）
        self._remove_link(src)
        os.makedirs(src, exist_ok=True)
        if target and os.path.exists(target) and os.path.abspath(target) != os.path.abspath(src):
            self._merge_move(target, src)
            self._remove_dir(target)
        return {"key": key, "name": entry["name"], "src": src, "restored_from": target}

    # ----- 底层操作 -----------------------------------------------------
    @staticmethod
    def _validate_target(src, dst):
        src_abs = os.path.abspath(src)
        dst_abs = os.path.abspath(dst)
        if dst_abs == src_abs:
            raise MigrationError("目标位置不能与原位置相同。")
        # 目标不能位于源目录内部，否则会形成自引用
        common = os.path.commonpath([src_abs, dst_abs]) if os.path.splitdrive(src_abs)[0] == os.path.splitdrive(dst_abs)[0] else ""
        if common and common == src_abs:
            raise MigrationError("目标位置不能在原文件夹内部。")

    @staticmethod
    def _merge_move(src, dst):
        """把 src 下的所有条目移动到 dst（已存在的同名项做合并/覆盖）。"""
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.exists(d):
                if os.path.isdir(s) and os.path.isdir(d):
                    FileMigrationService._merge_move(s, d)
                    FileMigrationService._remove_dir(s)
                    continue
                # 目标已存在同名文件：加后缀避免覆盖用户数据
                base, ext = os.path.splitext(name)
                index = 1
                while os.path.exists(d):
                    d = os.path.join(dst, f"{base}_{index}{ext}")
                    index += 1
            shutil.move(s, d)

    @staticmethod
    def _remove_dir(path):
        try:
            os.rmdir(path)
        except OSError as exc:
            raise MigrationError(f"无法移除目录 {path}：{exc}")

    @staticmethod
    def _remove_link(path):
        # Windows 上 junction 用 rmdir 删除链接本身；其它系统的符号链接用 unlink
        try:
            if IS_WINDOWS:
                os.rmdir(path)
            elif os.path.islink(path):
                os.unlink(path)
            else:
                os.rmdir(path)
        except OSError as exc:
            raise MigrationError(f"无法删除连接点 {path}：{exc}")

    @staticmethod
    def _create_link(src, dst):
        if IS_WINDOWS:
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", src, dst],
                    capture_output=True,
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                )
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout or b"").decode(
                        "gbk", errors="ignore"
                    ).strip()
                    raise MigrationError(f"创建连接点失败：{detail or '未知错误'}")
            except FileNotFoundError as exc:
                raise MigrationError(f"创建连接点失败：{exc}")
        else:
            # 非 Windows：用符号链接实现等效行为（便于验证逻辑）
            try:
                os.symlink(dst, src, target_is_directory=True)
            except OSError as exc:
                raise MigrationError(f"创建符号链接失败：{exc}")
