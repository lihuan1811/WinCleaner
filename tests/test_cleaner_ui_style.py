from pathlib import Path


def test_qt_ui_uses_cleaner_spirit_layout():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "APP_QSS" in source
    assert "sidebar" in source
    assert "heroPanel" in source
    assert "resultCard" in source
    assert "resultTree" in source
    assert "scanPrimaryButton" in source


def test_qt_ui_keeps_screenshot_like_green_shell():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "#35C878" in source
    assert "一键扫描" in source
    assert "一键清理" in source
    assert "扫描结果" in source
    assert "C盘清理精灵" in source
