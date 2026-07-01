#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""文件夹用途知识库测试。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from folder_hints import describe_folder, folder_tooltip


def test_system_folder_is_protected():
    info = describe_folder(r"C:\Windows")
    assert info["cn_name"] == "Windows 系统目录"
    assert info["level"] == "protected"
    assert "请勿" in info["advice"]


def test_winsxs_is_component_store():
    info = describe_folder(r"C:\Windows\WinSxS")
    assert info["level"] == "component"
    assert "DISM" in info["advice"]


def test_temp_is_cache_cleanable():
    info = describe_folder(r"C:\Users\me\AppData\Local\Temp")
    assert info["level"] == "cache"
    assert "可以安全清理" in info["advice"]


def test_windows_temp_special():
    info = describe_folder(r"C:\Windows\Temp")
    assert info["cn_name"] == "系统临时文件"
    assert info["level"] == "cache"


def test_update_download_special():
    info = describe_folder(r"C:\Windows\SoftwareDistribution\Download")
    assert info["cn_name"] == "更新下载缓存"
    assert info["level"] == "cache"


def test_user_documents_is_user_data():
    info = describe_folder(r"C:\Users\me\Documents")
    assert info["cn_name"] == "我的文档"
    assert info["level"] == "user_data"


def test_unknown_chinese_folder_uses_own_name():
    info = describe_folder(r"D:\我的项目资料")
    assert info["cn_name"] == "我的项目资料"
    assert info["level"] == "unknown"


def test_tooltip_contains_title_and_advice():
    tip = folder_tooltip(r"C:\Windows")
    assert "Windows 系统目录" in tip
    assert "清理建议" in tip
    assert "C:\\Windows" in tip
