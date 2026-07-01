#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""个人文件夹迁移服务测试（非 Windows 用符号链接验证等效逻辑）。"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_migration import FileMigrationService, MigrationError


def make_service(tmp_path):
    home = tmp_path / "home"
    local = home / "AppData" / "Local"
    (home).mkdir(parents=True, exist_ok=True)
    (local).mkdir(parents=True, exist_ok=True)
    return FileMigrationService(home=str(home), local_appdata=str(local)), home


def test_catalog_contains_expected_folders(tmp_path):
    service, _ = make_service(tmp_path)
    names = {entry["name"] for entry in service.catalog()}
    for expected in ["桌面", "我的文档", "下载", "我的图片", "临时文件", "保存的游戏"]:
        assert expected in names


def test_directory_size(tmp_path):
    service, home = make_service(tmp_path)
    desktop = home / "Desktop"
    desktop.mkdir()
    (desktop / "a.bin").write_bytes(b"x" * 1000)
    (desktop / "sub").mkdir()
    (desktop / "sub" / "b.bin").write_bytes(b"y" * 500)
    assert service.directory_size(str(desktop)) == 1500


def test_list_folders_reports_state(tmp_path):
    service, home = make_service(tmp_path)
    (home / "Desktop").mkdir()
    (home / "Desktop" / "f.txt").write_text("hello")
    folders = {f["key"]: f for f in service.list_folders()}
    assert folders["desktop"]["exists"] is True
    assert folders["desktop"]["migrated"] is False
    assert folders["desktop"]["size"] == 5
    # 不存在的目录
    assert folders["links"]["exists"] is False


def test_migrate_and_restore_roundtrip(tmp_path):
    service, home = make_service(tmp_path)
    desktop = home / "Desktop"
    desktop.mkdir()
    (desktop / "keep.txt").write_text("data")
    target_root = tmp_path / "target"

    info = service.migrate_folder("desktop", str(target_root), move_files=True)
    dst = info["dst"]

    # 原位置变成连接点，指向目标；数据已在目标位置
    assert service.is_reparse_point(str(desktop))
    assert os.path.exists(os.path.join(dst, "keep.txt"))
    # 通过连接点仍可访问文件
    assert os.path.exists(str(desktop / "keep.txt"))

    # 已迁移状态下再次迁移应报错
    with pytest.raises(MigrationError):
        service.migrate_folder("desktop", str(target_root))

    # 还原：连接点移除，数据移回原处
    service.restore_folder("desktop")
    assert not service.is_reparse_point(str(desktop))
    assert os.path.exists(str(desktop / "keep.txt"))
    assert not os.path.exists(dst)


def test_migrate_rejects_target_inside_source(tmp_path):
    service, home = make_service(tmp_path)
    desktop = home / "Desktop"
    desktop.mkdir()
    with pytest.raises(MigrationError):
        service.migrate_folder("desktop", str(desktop / "inside"))


def test_restore_non_migrated_errors(tmp_path):
    service, home = make_service(tmp_path)
    (home / "Desktop").mkdir()
    with pytest.raises(MigrationError):
        service.restore_folder("desktop")
