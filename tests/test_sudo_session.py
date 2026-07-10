from __future__ import annotations

from src.core.cpu import CPUController
from src.core.power import PowerController
from src.core.sensors import Capability


def test_power_controller_checks_sudo_in_current_session(monkeypatch) -> None:
    calls = []

    def fake_run_command(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return True, ""

    monkeypatch.setattr("src.core.power.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("src.core.power.os.path.exists", lambda path: True)
    monkeypatch.setattr("src.core.power.os.geteuid", lambda: 1000)
    monkeypatch.setattr("src.core.power.run_command", fake_run_command)

    controller = PowerController()

    assert controller.capability.available
    assert calls == [(["sudo", "-n", "true"], {"timeout": 2, "start_new_session": False})]


def test_power_controller_runs_ryzenadj_in_current_session(monkeypatch) -> None:
    calls = []
    controller = PowerController.__new__(PowerController)
    controller.ryzenadj_path = "/usr/bin/ryzenadj"
    controller._sudo_prefix = ["sudo", "-n"]
    controller.capability = Capability(True)
    controller.last_error = ""

    def fake_run_command(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return True, "ok"

    monkeypatch.setattr("src.core.power.run_command", fake_run_command)

    assert controller._run_ryzenadj(["-i"]) == (True, "ok")
    assert calls == [
        (
            ["sudo", "-n", "/usr/bin/ryzenadj", "-i"],
            {"timeout": 10, "start_new_session": False},
        )
    ]


def test_power_controller_runs_without_sudo_when_root(monkeypatch) -> None:
    calls = []
    controller = PowerController.__new__(PowerController)
    controller.ryzenadj_path = "/usr/bin/ryzenadj"
    controller._sudo_prefix = []
    controller.capability = Capability(True)
    controller.last_error = ""

    def fake_run_command(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return True, "ok"

    monkeypatch.setattr("src.core.power.run_command", fake_run_command)

    assert controller._run_ryzenadj(["-i"]) == (True, "ok")
    assert calls == [
        (
            ["/usr/bin/ryzenadj", "-i"],
            {"timeout": 10, "start_new_session": False},
        )
    ]


def test_cpu_controller_uses_current_session_for_sudo_writes(monkeypatch) -> None:
    calls = []
    controller = CPUController.__new__(CPUController)
    controller.capability = Capability(True)
    controller.last_error = ""

    def fake_run_command(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return True, "written"

    monkeypatch.setattr("src.core.cpu.run_command", fake_run_command)

    assert controller._write_with_sudo("/sys/example", "123") == (True, "")
    assert calls == [
        (
            ["sudo", "-n", "tee", "/sys/example"],
            {"timeout": 10, "input_data": "123\n", "start_new_session": False},
        )
    ]
