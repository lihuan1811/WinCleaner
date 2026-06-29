from pathlib import Path

from cleaner_logic import CleanerLogic


class Recorder:
    def __init__(self):
        self.events = []

    def emit(self, path, count):
        self.events.append((path, count))


def test_scan_progress_since_emits_paths_from_regular_lists():
    recorder = Recorder()
    results = {
        "cache": [
            {"path": r"C:\Users\Administrator\AppData\Local\Temp\a.tmp"},
        ],
        "prefetch": [],
    }
    seen_counts = {"cache": 0, "prefetch": 0}

    CleanerLogic._emit_scan_progress_since(results, recorder, seen_counts)
    results["cache"].append({"path": r"C:\Windows\Prefetch\MSEDGE.EXE-37D25F9A.pf"})
    results["cache"].append({"path": ""})
    CleanerLogic._emit_scan_progress_since(results, recorder, seen_counts)

    assert recorder.events == [
        (r"C:\Users\Administrator\AppData\Local\Temp\a.tmp", 1),
        (r"C:\Windows\Prefetch\MSEDGE.EXE-37D25F9A.pf", 3),
    ]
    assert type(results["cache"]) is list


def test_cleaner_logic_exposes_scan_progress_callback():
    source = Path("cleaner_logic.py").read_text(encoding="utf-8")

    assert "def scan_system(self, progress_callback=None)" in source
    assert "_emit_scan_progress_since" in source
    assert "_run_scan_task" in source
    assert "ProgressAwareList" not in source


def test_scan_system_progress_callback_does_not_replace_result_lists():
    source = Path("cleaner_logic.py").read_text(encoding="utf-8")

    assert "ProgressAwareList" not in source
    assert "ProgressAwareList(category" not in source


def test_qt_scan_page_shows_current_scanning_path():
    source = Path("cleaner_ui.py").read_text(encoding="utf-8")

    assert "pyqtSignal(str, int)" in source
    assert "self.cleaner.scan_system(self.update_signal)" in source
    assert "current_scan_path_label" in source
    assert "def on_scan_progress" in source
    assert "self.scan_thread.update_signal.connect(self.on_scan_progress)" in source
