#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""文件夹用途知识库：为“文件管理”里的目录提供中文名、用途说明与清理建议。

用于鼠标悬停提示，帮助用户判断某个文件夹是做什么的、能不能清理。
"""

from __future__ import annotations


# 清理建议级别 -> 展示文案
ADVICE = {
    "protected": "⛔ 系统关键目录，删除会导致系统或程序无法运行，请勿清理。",
    "component": "⚠️ Windows 组件存储，请勿手动删除；可用系统优化里的 DISM 组件清理安全瘦身。",
    "installer": "⚠️ 存放软件的安装/卸载还原数据，删除后将无法卸载或修复程序，请勿删除。",
    "program": "🧩 程序安装目录，需要卸载请用“软件卸载”，不要直接删除。",
    "user_data": "📁 你的个人数据，删除会丢失文件；如需释放 C 盘可用“文件迁移”移到其它磁盘。",
    "cache": "✅ 缓存 / 临时文件，通常可以安全清理，程序会自动重建。",
    "log": "🧹 日志文件，一般可以清理。",
    "unknown": "❓ 未识别目录，清理前请先确认用途。",
}


# 按目录名（小写）匹配：name -> (中文名, 用途说明, 级别)
KNOWN_FOLDERS = {
    "windows": ("Windows 系统目录", "Windows 操作系统的核心文件都在这里。", "protected"),
    "system32": ("系统核心组件", "64 位系统关键组件、服务与驱动程序。", "protected"),
    "syswow64": ("32 位兼容组件", "供 32 位程序运行的系统文件。", "protected"),
    "winsxs": ("组件存储 (WinSxS)", "Windows 组件与更新的历史版本备份。", "component"),
    "microsoft.net": (".NET 运行库", "Microsoft .NET Framework 框架文件。", "protected"),
    "systemapps": ("系统内置应用", "Windows 自带的系统应用。", "protected"),
    "fonts": ("字体目录", "系统安装的字体文件。", "protected"),
    "boot": ("启动文件", "Windows 启动引导相关文件。", "protected"),
    "drivers": ("驱动程序", "硬件驱动程序文件。", "protected"),
    "installer": ("安装缓存 (Installer)", "已安装程序的卸载/修复还原数据。", "installer"),
    "assembly": ("全局程序集缓存", ".NET 全局程序集缓存 (GAC)。", "protected"),
    "program files": ("程序目录 (64位)", "已安装的 64 位软件。", "program"),
    "program files (x86)": ("程序目录 (32位)", "已安装的 32 位软件。", "program"),
    "programdata": ("程序公共数据", "各软件共享的配置与数据。", "program"),
    "users": ("用户目录", "所有用户的个人文件夹。", "user_data"),
    "appdata": ("应用数据", "各应用的配置、缓存与数据。", "program"),
    "$recycle.bin": ("回收站", "已删除文件的暂存区。", "cache"),
    "recovery": ("恢复分区数据", "系统恢复相关文件。", "protected"),
    "perflogs": ("性能日志", "系统性能与诊断日志。", "log"),
    "temp": ("临时文件", "程序运行产生的临时文件。", "cache"),
    "tmp": ("临时文件", "程序运行产生的临时文件。", "cache"),
    "prefetch": ("预读取缓存", "加速程序启动的预读取数据，删除后会自动重建。", "cache"),
    "softwaredistribution": ("Windows 更新缓存", "Windows 更新下载的临时文件。", "cache"),
    "inetcache": ("IE / 系统网页缓存", "系统与 IE 的网页缓存。", "cache"),
    "inetcookies": ("网络 Cookie", "网站 Cookie 数据。", "cache"),
    "logs": ("日志目录", "系统或程序的日志文件。", "log"),
    "downloaded installations": ("安装包缓存", "安装程序缓存的临时文件。", "cache"),
    # 个人文件夹
    "desktop": ("桌面", "桌面上的文件与快捷方式。", "user_data"),
    "documents": ("我的文档", "文档、资料等个人文件。", "user_data"),
    "downloads": ("下载", "浏览器与软件的下载文件。", "user_data"),
    "pictures": ("我的图片", "图片、照片。", "user_data"),
    "videos": ("我的视频", "视频文件。", "user_data"),
    "music": ("我的音乐", "音乐、音频文件。", "user_data"),
    "favorites": ("收藏夹", "浏览器收藏夹。", "user_data"),
    "contacts": ("联系人", "联系人信息。", "user_data"),
    "links": ("链接", "资源管理器收藏的链接。", "user_data"),
    "searches": ("搜索", "保存的搜索。", "user_data"),
    "saved games": ("保存的游戏", "游戏存档。", "user_data"),
    "onedrive": ("OneDrive", "OneDrive 云同步文件夹。", "user_data"),
}


def _has_chinese(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text or "")


def describe_folder(path: str) -> dict:
    """返回 {cn_name, en_name, description, level, advice}。"""
    path = path or ""
    # 同时兼容 Windows 反斜杠与正斜杠（在非 Windows 上 os.path.basename 不会拆分反斜杠）
    normalized = path.replace("\\", "/").rstrip("/")
    name = normalized.rsplit("/", 1)[-1] if normalized else path
    lower = name.lower()
    path_lower = path.lower().replace("/", "\\")

    # 特殊路径：thumbnails / explorer 缓存
    if "explorer" in path_lower and ("thumbcache" in path_lower or "iconcache" in path_lower):
        cn, desc, level = ("缩略图缓存", "资源管理器缩略图/图标缓存，可安全清理。", "cache")
        return _build(cn, name, desc, level)

    if "softwaredistribution" in path_lower and "download" in path_lower:
        cn, desc, level = ("更新下载缓存", "Windows 更新下载的安装包，可安全清理。", "cache")
        return _build(cn, name, desc, level)

    if path_lower.rstrip("\\").endswith("windows\\temp"):
        cn, desc, level = ("系统临时文件", "系统级临时文件，可安全清理。", "cache")
        return _build(cn, name, desc, level)

    entry = KNOWN_FOLDERS.get(lower)
    if entry:
        cn, desc, level = entry
        return _build(cn, name, desc, level)

    # 未知目录：若名字本身是中文就直接用它做中文名
    cn = name if _has_chinese(name) else ""
    return _build(cn, name, "", "unknown")


def _build(cn_name: str, en_name: str, description: str, level: str) -> dict:
    return {
        "cn_name": cn_name,
        "en_name": en_name,
        "description": description,
        "level": level,
        "advice": ADVICE.get(level, ADVICE["unknown"]),
    }


def folder_tooltip(path: str) -> str:
    """构建鼠标悬停显示的富文本提示。"""
    info = describe_folder(path)
    cn = info["cn_name"]
    en = info["en_name"]
    if cn and cn != en:
        title = f"{cn}（{en}）"
    else:
        title = cn or en

    lines = [f"<b>{_escape(title)}</b>"]
    if info["description"]:
        lines.append(f"用途：{_escape(info['description'])}")
    lines.append(f"清理建议：{_escape(info['advice'])}")
    lines.append(f"<span style='color:#8aa'>{_escape(path)}</span>")
    return "<br>".join(lines)


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
