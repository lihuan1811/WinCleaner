#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from registry_cleaner import (
    RegistryCleanerService,
    first_path_token,
    target_exists,
)


def test_scan_returns_empty_when_not_windows():
    service = RegistryCleanerService(is_windows=False)
    assert service.available() is False
    assert service.scan() == []


def test_delete_and_backup_noop_when_unavailable():
    service = RegistryCleanerService(is_windows=False)
    issue = {"hive": "HKLM", "subkey": "Software\\Foo", "kind": "key"}
    assert service.delete_issue(issue) is False
    assert service.export_backup(issue, "/tmp/none") is None


def test_first_path_token_handles_quotes_and_icon_index():
    assert first_path_token('"C:\\App\\a.exe" /x') == "C:\\App\\a.exe"
    assert first_path_token("C:\\App\\a.exe,0") == "C:\\App\\a.exe"
    assert first_path_token("") == ""


def test_target_exists_for_real_and_missing_paths():
    assert target_exists(f'"{os.path.abspath(__file__)}"') is True
    assert target_exists("C:\\definitely\\missing\\nope.exe") is False


def test_issue_location_includes_value_name():
    service = RegistryCleanerService(is_windows=False)
    issue = {"hive": "HKLM", "subkey": "Software\\Foo", "value_name": "bar"}
    location = service.issue_location(issue)
    assert "HKLM" in location and "bar" in location
