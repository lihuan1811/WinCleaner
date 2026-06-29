from pathlib import Path

from cleaner_logic import ProgressAwareList


class Recorder:
    def __init__(self):
        self.events = []

    def emit(self, path, count):
        self.events.append((path, count))


def test_progress_aware_list_emits_paths_as_items_are_found():
    recorder = Recorder()
    items = ProgressAwareList("cache", recorder)

    items.append({"path": r"C:\Users\Administrator\AppData\Local\Temp\a.tmp"})
    items.extend([
        {"path": r"C:\Windows\Prefetch\MSEDGE.EXE-37D25F9A.pf"},
        {"path": ""},
    ])

    assert recorder.events == [
        (r"C:\Users\Administrator\AppData\Local\Temp\a.tmp", 1),
        (r"C:\Windows\Prefetch\MSEDGE.EXE-37D25F9A.pf", 2),
    ]


def test_cleaner_logic_exposes_scan_progress_callback():
    source = Path("cleaner_logic.py").read_text(encoding="utf-8")

    assert "def scan_system(self, progress_callback=None)" in source
    assert "ProgressAwareList(category, progress_callback)" in source
    assert "_run_scan_task" in source


def test_qt_scan_page_shows_current_scanning_path():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "pyqtSignal(str, int)" in source
    assert "self.cleaner.scan_system(self.update_signal)" in source
    assert "current_scan_path_label" in source
    assert "def on_scan_progress" in source
    assert "self.scan_thread.update_signal.connect(self.on_scan_progress)" in source
