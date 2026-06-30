from system_repair import RepairRisk, SystemRepairService


def test_default_repair_actions_include_safe_and_deep_groups():
    actions = SystemRepairService.default_actions()
    ids = [action.id for action in actions]

    assert "sfc_scan" in ids
    assert "dism_restore_health" in ids
    assert any(action.recommended for action in actions)
    assert any(action.deep for action in actions)


def test_recommended_repair_preset_selects_only_safe_actions():
    preset = SystemRepairService.recommended_preset()

    assert [action.id for action in preset] == [
        "sfc_scan",
        "chkdsk_scan",
        "flush_dns",
        "winsock_reset",
    ]
    assert all(action.risk == RepairRisk.SAFE for action in preset)


def test_runs_repair_actions_through_cmd_with_expected_command_line():
    calls = []

    def fake_runner(executable, arguments):
        calls.append([executable, *arguments])
        return 0, "ok"

    service = SystemRepairService(is_windows=True, process_runner=fake_runner)
    result = service.run_action(SystemRepairService.default_actions()[0])

    assert result.success is True
    assert calls == [["cmd", "/C", "sfc /scannow"]]


def test_reports_unsupported_outside_windows():
    service = SystemRepairService(is_windows=False)
    result = service.run_action(SystemRepairService.default_actions()[0])

    assert result.unsupported is True
    assert "仅支持 Windows" in result.output
