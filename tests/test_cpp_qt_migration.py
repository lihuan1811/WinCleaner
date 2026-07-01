from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CPP_ROOT = ROOT / "cpp_qt"


def read_cpp_file(*parts):
    path = CPP_ROOT.joinpath(*parts)
    assert path.exists(), f"missing C++ Qt migration file: {path}"
    return path.read_text(encoding="utf-8")


def read_repo_file(*parts):
    path = ROOT.joinpath(*parts)
    assert path.exists(), f"missing repository file: {path}"
    return path.read_text(encoding="utf-8")


def joined_cpp_sources():
    assert CPP_ROOT.exists(), "cpp_qt project must live beside the existing Python project"
    texts = []
    for path in sorted((CPP_ROOT / "src").glob("*.cpp")) + sorted((CPP_ROOT / "src").glob("*.h")):
        texts.append(path.read_text(encoding="utf-8"))
    return "\n".join(texts)


def assert_contains_all(source, expected):
    missing = [token for token in expected if token not in source]
    assert not missing, "missing expected migration tokens: " + ", ".join(missing)


def test_cpp_qt_project_has_native_qt_build_and_github_package_workflow():
    cmake = read_cpp_file("CMakeLists.txt")
    workflow = read_repo_file(".github", "workflows", "build-cpp-qt.yml")

    assert_contains_all(
        cmake,
        [
            "find_package(Qt6",
            "Widgets",
            "Concurrent",
            "qt_add_executable",
            "/utf-8",
            "ClearC",
        ],
    )
    assert_contains_all(
        workflow,
        [
            "windows-latest",
            "jurplel/install-qt-action",
            "cmake -S cpp_qt",
            "windeployqt",
            "ClearC-Qt",
            "gh release create",
        ],
    )


def test_cpp_qt_navigation_and_pages_cover_existing_product_modules():
    source = joined_cpp_sources()

    assert_contains_all(
        source,
        [
            "C盘清理",
            "系统优化",
            "BX(优化)",
            "软件卸载",
            "文件管理",
            "系统修复",
            "账号会员",
            "createCleanPage",
            "createOptimizePage",
            "createBxPage",
            "createUninstallPage",
            "createFilePage",
            "createRepairPage",
            "createAccountPage",
        ],
    )


def test_cpp_qt_cleanup_keeps_full_path_catalog_and_three_selection_modes():
    source = joined_cpp_sources()

    assert_contains_all(
        source,
        [
            "推荐",
            "专业",
            "全选",
            "recommendedMode",
            "professionalMode",
            "selectAllMode",
            "allowScanOnly",
            "Prefetch",
            "Panther",
            "DrvPath",
            "Intel\\\\Logs",
            "WindowsApps",
            "SoftwareDistribution",
            "catroot2",
            "Windows Defender",
            "WinSxS",
            "EdgeCore",
            "GameViewer\\\\webviewcache",
            "AppData\\\\Local\\\\Microsoft\\\\Edge",
            "实时扫描",
            "currentScanPath",
        ],
    )


def test_cpp_qt_system_optimizer_bx_and_repair_catalogs_are_ported():
    source = joined_cpp_sources()

    assert_contains_all(
        source,
        [
            "开机加速",
            "运行内存",
            "系统优化",
            "隐私清理",
            "注册表清理",
            "populateStartupItems",
            "populateMemoryItems",
            "populateSystemOptimizationItems",
            "populatePrivacyItems",
            "populateRegistryItems",
            "基本",
            "最佳",
            "BoosterX",
            "自动更新地图",
            "SysMain",
            "OneDrive",
            "HAGS",
            "sfc /scannow",
            "DISM /Online /Cleanup-Image /RestoreHealth",
            "chkdsk C: /scan",
            "netsh winsock reset",
        ],
    )


def test_cpp_qt_file_uninstall_and_account_features_are_native_and_async():
    source = joined_cpp_sources()

    assert_contains_all(
        source,
        [
            "扫描大文件",
            "扫描重复文件",
            "碎片整理",
            "scanLargeFilesAsync",
            "scanDuplicateFilesAsync",
            "deleteSelectedFileItems",
            "scanFragments",
            "optimizeFragments",
            "defrag",
            "UninstallString",
            "QuietUninstallString",
            "refreshInstalledApps",
            "runUninstallCommand",
            "登录",
            "注册",
            "卡密",
            "redeemCard",
            "QtConcurrent::run",
        ],
    )
