#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Windows system repair command catalog and runner.
"""

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum


def hidden_windows_subprocess_kwargs():
    if not sys.platform.startswith("win"):
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


class RepairRisk(Enum):
    SAFE = ("安全", "日常维护可执行")
    CAUTION = ("谨慎", "可能耗时较长或需要重启")

    @property
    def label(self):
        return self.value[0]

    @property
    def description(self):
        return self.value[1]


@dataclass(frozen=True)
class SystemRepairAction:
    id: str
    name: str
    description: str
    command: str
    risk: RepairRisk
    recommended: bool = False
    deep: bool = False


@dataclass(frozen=True)
class SystemRepairResult:
    action: SystemRepairAction
    exit_code: int
    output: str
    unsupported: bool = False

    @property
    def success(self):
        return not self.unsupported and self.exit_code == 0


class SystemRepairService:
    def __init__(self, is_windows=None, process_runner=None):
        self.is_windows = sys.platform.startswith("win") if is_windows is None else is_windows
        self.process_runner = process_runner or self._run_process

    @staticmethod
    def _run_process(executable, arguments):
        result = subprocess.run(
            [executable, *arguments],
            capture_output=True,
            text=True,
            errors="replace",
            shell=False,
            stdin=subprocess.DEVNULL,
            **hidden_windows_subprocess_kwargs(),
        )
        output_parts = [
            value.strip()
            for value in (result.stdout, result.stderr)
            if value and value.strip()
        ]
        return result.returncode, "\n".join(output_parts) or "命令无输出"

    def run_action(self, action):
        if not self.is_windows:
            return SystemRepairResult(
                action=action,
                exit_code=-1,
                output="该修复命令仅支持 Windows。",
                unsupported=True,
            )

        exit_code, output = self.process_runner("cmd", ["/C", action.command])
        return SystemRepairResult(
            action=action,
            exit_code=exit_code,
            output=output or "命令无输出",
            unsupported=False,
        )

    @classmethod
    def recommended_preset(cls):
        return [action for action in cls.default_actions() if action.recommended]

    @classmethod
    def deep_preset(cls):
        return [
            action
            for action in cls.default_actions()
            if action.recommended or action.deep
        ]

    @staticmethod
    def default_actions():
        return [
            SystemRepairAction(
                id="sfc_scan",
                name="SFC 系统文件修复",
                description="使用微软 sfc /scannow 检查并修复受保护系统文件。",
                command="sfc /scannow",
                risk=RepairRisk.SAFE,
                recommended=True,
            ),
            SystemRepairAction(
                id="chkdsk_scan",
                name="CHKDSK 磁盘安全扫描",
                description="扫描 C 盘文件系统错误，不强制修复，不要求立即重启。",
                command="chkdsk C: /scan",
                risk=RepairRisk.SAFE,
                recommended=True,
            ),
            SystemRepairAction(
                id="flush_dns",
                name="DNS 刷新",
                description="清空本机 DNS 解析缓存，适合网页打不开或解析异常。",
                command="ipconfig /flushdns",
                risk=RepairRisk.SAFE,
                recommended=True,
            ),
            SystemRepairAction(
                id="winsock_reset",
                name="Winsock 网络重置",
                description="重置 Windows 网络套接字目录，通常需要重启后完全生效。",
                command="netsh winsock reset",
                risk=RepairRisk.SAFE,
                recommended=True,
            ),
            SystemRepairAction(
                id="dism_restore_health",
                name="DISM 系统镜像修复",
                description="使用 DISM 在线修复系统组件仓库，耗时较长。",
                command="DISM /Online /Cleanup-Image /RestoreHealth",
                risk=RepairRisk.CAUTION,
                deep=True,
            ),
            SystemRepairAction(
                id="chkdsk_deep",
                name="磁盘错误深度修复",
                description="安排 C 盘深度修复，可能提示下次重启执行。",
                command="echo Y|chkdsk C: /F /R",
                risk=RepairRisk.CAUTION,
                deep=True,
            ),
            SystemRepairAction(
                id="windows_update_reset",
                name="系统更新组件修复",
                description="停止更新服务并重建 SoftwareDistribution 与 catroot2 缓存。",
                command=(
                    r"net stop wuauserv & net stop bits & net stop cryptsvc & "
                    r"ren %systemroot%\SoftwareDistribution SoftwareDistribution.old & "
                    r"ren %systemroot%\System32\catroot2 catroot2.old & "
                    r"net start cryptsvc & net start bits & net start wuauserv"
                ),
                risk=RepairRisk.CAUTION,
                deep=True,
            ),
            SystemRepairAction(
                id="cache_reset",
                name="缓存重置修复",
                description="重置微软商店缓存，适合商店应用打开异常。",
                command="wsreset.exe",
                risk=RepairRisk.CAUTION,
                deep=True,
            ),
        ]
