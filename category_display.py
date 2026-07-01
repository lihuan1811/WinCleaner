#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Shared cleanup category names and tree labels for desktop UIs."""

CATEGORY_NAMES = {
    # 基本清理
    "temp": "临时文件",
    "recycle": "回收站",
    "cache": "浏览器缓存",
    "logs": "系统日志",
    "updates": "Windows更新缓存",
    "thumbnails": "缩略图缓存",
    # 扩展清理
    "prefetch": "预读取文件",
    "old_windows": "旧Windows文件",
    "error_reports": "错误报告",
    "service_packs": "服务包备份",
    "memory_dumps": "内存转储文件",
    "font_cache": "字体缓存",
    "disk_cleanup": "磁盘清理备份",
    # 安全清理项
    "app_cache": "应用程序缓存",
    "media_cache": "媒体播放器缓存",
    "search_index": "搜索索引临时文件",
    "backup_temp": "备份临时文件",
    "update_temp": "更新临时文件",
    "driver_backup": "驱动备份",
    "app_crash": "应用程序崩溃转储",
    "app_logs": "应用程序日志",
    "recent_items": "最近使用的文件列表",
    "notification": "Windows通知缓存",
    "dns_cache": "DNS缓存",
    "network_cache": "网络缓存",
    "printer_temp": "打印机临时文件",
    "device_temp": "设备临时文件",
    "windows_defender": "Windows Defender缓存",
    "store_cache": "Windows Store缓存",
    "onedrive_cache": "OneDrive缓存",
    # 用户请求的清理项
    "downloads": "下载文件夹(立即清理)",
    "installer_cache": "安装程序缓存(30天前)",
    "delivery_opt": "Windows传递优化缓存(立即清理)",
    "dismpp_rules": "Dism++规则",
    # 截图补充路径项
    "edge_webview_cache": "Edge/WebView内核缓存",
    "edge_profile_state": "Edge用户状态文件",
    "edge_component_updates": "Edge组件旧版本",
    "edgecore_old_versions": "EdgeCore旧版本更新",
    "panther_setup_logs": "安装过程日志",
    "service_profile_temp": "系统服务临时文件",
    "drvpath_driver_packages": "DrvPath驱动残留",
    "intel_logs": "Intel残留日志",
    "explorer_runtime_cache": "Explorer运行缓存",
    "legacy_ie_cache": "IE/系统Web缓存",
    "appx_package_cache": "AppData Packages缓存",
    "third_party_app_logs": "第三方组件日志",
    "windows_extra_logs": "Windows扩展日志",
    "sleepstudy_wdi_traces": "SleepStudy/WDI事件跟踪",
    "windowsapps_cleanup_candidates": "WindowsApps精简候选",
    "windows_update_lcu_backup": "Windows更新备份",
    "windows_update_signature_cache": "Windows Update签名缓存",
    "windows_search_index_cache": "Windows搜索索引缓存",
    "defender_definition_backup": "Defender更新备份",
    "defender_support_logs": "Defender Support",
    "defender_history": "Defender保护历史",
    "defender_quarantine": "Defender隔离区",
    "winsxs_backup": "WinSxS Backup",
    "winsxs_catalogs": "WinSxS Catalogs",
    "winsxs_onedrive_setup": "WinSxS OneDrive安装程序",
    "winsxs_component_store": "WinSxS组件存储",
    # 专项清理
    "wechat_special_clean": "微信专清",
    "qq_special_clean": "QQ专清",
    # 大文件扫描
    "large_files": "大文件 (>100MB)",
}


def category_display_name(category):
    return CATEGORY_NAMES.get(category, category)


def category_badge(category):
    category_text = category.lower()
    if "edge" in category_text or "webview" in category_text:
        return "[Edge]"
    if "chrome" in category_text or category_text == "cache":
        return "[Chrome]"
    if "defender" in category_text or category_text == "windows_defender":
        return "[Def]"
    if "winsxs" in category_text:
        return "[WinSxS]"
    if "drvpath" in category_text or "driver" in category_text:
        return "[Drv]"
    if "intel" in category_text:
        return "[Intel]"
    if "ie" in category_text or "legacy_ie" in category_text:
        return "[IE]"
    if "explorer" in category_text:
        return "[Exp]"
    if "windowsapps" in category_text or "appx" in category_text:
        return "[Apps]"
    if "update" in category_text or "catroot" in category_text:
        return "[WU]"
    if "windows" in category_text or "panther" in category_text:
        return "[Win]"
    return ""


def category_tree_label(category):
    badge = category_badge(category)
    name = category_display_name(category)
    return f"{badge} {name}" if badge else name


def strip_category_badge(label):
    if label.startswith("[") and "] " in label:
        return label.split("] ", 1)[1]
    return label


def category_key_from_tree_tags(tags):
    for tag in tags:
        if tag.startswith("category:"):
            return tag.split(":", 1)[1]
    return None
