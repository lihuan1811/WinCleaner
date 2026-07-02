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
        try:
            os.makedirs(target_root, exist_ok=True)
        except OSError as exc:
            raise MigrationError(
                f"无法创建目标目录 {target_root}：{self._explain(exc)}"
            )
        # 迁移依赖连接点(junction)，目标磁盘必须为 NTFS 格式
        self._ensure_supports_junction(target_root, entry["name"])

        src_existed = os.path.exists(src)
        moved = False
        if src_existed:
            if move_files:
                os.makedirs(dst, exist_ok=True)
                self._merge_move(src, dst, entry["name"])
                moved = True
            else:
                if os.path.isdir(src) and os.listdir(src):
                    raise MigrationError(
                        f"“{entry['name']}”内还有文件，请勾选“转移文件”后再迁移。"
                    )
                os.makedirs(dst, exist_ok=True)
            try:
                self._remove_dir(src)
            except MigrationError:
                # src 非空通常意味着仍有文件被占用；数据已在目标目录，回滚以避免半迁移状态
                if moved:
                    self._rollback(dst, src)
                raise MigrationError(
                    f"“{entry['name']}”中有文件正被占用，无法完成迁移，"
                    "请关闭相关程序（如资源管理器、微信/QQ 等）后重试。"
                )
        else:
            os.makedirs(dst, exist_ok=True)

        try:
            self._create_link(src, dst)
        except MigrationError:
            # 连接点创建失败时，把数据移回原位置，避免原路径丢失
            if src_existed:
                self._rollback(dst, src)
            raise
        return {"key": key, "name": entry["name"], "src": src, "dst": dst}

    @classmethod
    def _rollback(cls, dst, src):
        """迁移失败时把已移动到 dst 的数据移回 src，尽量恢复原状。"""
        try:
            os.makedirs(src, exist_ok=True)
            if os.path.exists(dst):
                cls._merge_move(dst, src)
        except Exception:
            # 回滚为尽力而为，失败也不再抛出（原始错误更重要）
            pass

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
    def _explain(exc):
        """把系统异常翻译成用户能看懂的中文提示。"""
        winerr = getattr(exc, "winerror", None)
        mapping = {
            5: "拒绝访问，请尝试以管理员身份运行本程序。",
            32: "文件正被其它程序占用，请关闭相关程序后重试。",
            33: "文件正被其它程序占用，请关闭相关程序后重试。",
            145: "目标目录非空。",
            183: "目标位置已存在同名项。",
        }
        if winerr in mapping:
            return mapping[winerr]
        message = getattr(exc, "strerror", None) or str(exc)
        return message

    @staticmethod
    def _ensure_supports_junction(target_root, folder_name):
        """确认目标磁盘支持连接点(NTFS)；U 盘/移动硬盘常为 exFAT/FAT，不支持。"""
        if not IS_WINDOWS:
            return
        try:
            import ctypes

            drive = os.path.splitdrive(os.path.abspath(target_root))[0]
            if not drive:
                return
            root = drive + "\\"
            fs_buf = ctypes.create_unicode_buffer(64)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root),
                None, 0, None, None, None,
                fs_buf, ctypes.sizeof(fs_buf),
            )
            if ok:
                fs = (fs_buf.value or "").upper()
                if fs and fs != "NTFS":
                    raise MigrationError(
                        f"目标磁盘为 {fs} 格式，不支持连接点，无法迁移“{folder_name}”。"
                        "请选择 NTFS 格式的磁盘作为目标。"
                    )
        except MigrationError:
            raise
        except Exception:
            # 检测失败不阻断迁移，交由 mklink 报错
            return

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
    def _merge_move(src, dst, folder_name=""):
        """把 src 下的所有条目移动到 dst（已存在的同名项做合并/覆盖）。"""
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.exists(d):
                if os.path.isdir(s) and os.path.isdir(d):
                    FileMigrationService._merge_move(s, d, folder_name)
                    FileMigrationService._remove_dir(s)
                    continue
                # 目标已存在同名文件：加后缀避免覆盖用户数据
                base, ext = os.path.splitext(name)
                index = 1
                while os.path.exists(d):
                    d = os.path.join(dst, f"{base}_{index}{ext}")
                    index += 1
            try:
                shutil.move(s, d)
            except OSError as exc:
                label = f"“{folder_name}”中的文件 " if folder_name else "文件 "
                raise MigrationError(
                    f"移动{label}{name} 失败：{FileMigrationService._explain(exc)}"
                )

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
                    hint = ""
                    low = detail.lower()
                    if "拒绝访问" in detail or "denied" in low:
                        hint = "（请尝试以管理员身份运行本程序）"
                    elif "已存在" in detail or "exist" in low:
                        hint = "（原位置仍存在同名文件夹，请手动清理后重试）"
                    raise MigrationError(
                        f"创建连接点失败：{detail or '未知错误'}{hint}"
                    )
            except FileNotFoundError as exc:
                raise MigrationError(f"创建连接点失败：{exc}")
        else:
            # 非 Windows：用符号链接实现等效行为（便于验证逻辑）
            try:
                os.symlink(dst, src, target_is_directory=True)
            except OSError as exc:
                raise MigrationError(f"创建符号链接失败：{exc}")
