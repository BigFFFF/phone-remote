import base64
import copy
import json
from pathlib import Path

import pytest

from phone_remote.app_launcher import AppLauncher
from phone_remote.config import ConfigStore, migrate_config, validate_config
from phone_remote.windows_control import (
    MAX_TEXT_LENGTH,
    ControlService,
    WindowsBackend,
    _windows_sleep_command,
)


@pytest.fixture()
def valid_config(tmp_path: Path) -> dict:
    browser = tmp_path / "browser.exe"
    program = tmp_path / "program.exe"
    browser.touch()
    program.touch()
    return {
        "version": 1,
        "browsers": {
            "edge": {
                "path": str(browser),
                "args": ["--profile", "Phone Remote"],
                "fullscreenArgs": ["--start-fullscreen"],
            }
        },
        "apps": [
            {
                "id": "website",
                "name": "Website",
                "enabled": True,
                "icon": "website.png",
                "launch": {
                    "type": "browser",
                    "browser": "edge",
                    "url": "https://example.com/watch?q=1",
                    "fullscreen": True,
                },
            },
            {
                "id": "player",
                "name": "Player",
                "enabled": True,
                "icon": "player.png",
                "launch": {
                    "type": "program",
                    "path": str(program),
                    "args": ["--safe", "value with spaces"],
                },
            },
        ],
    }


@pytest.fixture()
def store(valid_config: dict, tmp_path: Path) -> ConfigStore:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(valid_config), encoding="utf-8")
    return ConfigStore(path, tmp_path / "icons")


class FakeBackend:
    def __init__(self):
        self.events = []

    def key(self, code):
        self.events.append(("key", code))

    def key_combo(self, *codes):
        self.events.append(("combo", *codes))

    def text(self, value):
        self.events.append(("text", value))

    def mouse_move(self, dx, dy):
        self.events.append(("move", dx, dy))

    def mouse_click(self, button):
        self.events.append(("click", button))

    def mouse_wheel(self, delta):
        self.events.append(("wheel", delta))

    def power(self, action):
        self.events.append(("power", action))


def test_config_and_launch_arguments_are_preserved(store: ConfigStore) -> None:
    launcher = AppLauncher(store)
    assert launcher.launch_args("website")[1:] == [
        "--profile",
        "Phone Remote",
        "--start-fullscreen",
        "https://example.com/watch?q=1",
    ]
    assert launcher.launch_args("player")[1:] == ["--safe", "value with spaces"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(version=2), "unsupported config version"),
        (
            lambda value: value["apps"].append(copy.deepcopy(value["apps"][0])),
            "duplicate app id",
        ),
        (
            lambda value: value["apps"][0]["launch"].update(url="file:///secret"),
            "http or https",
        ),
        (
            lambda value: value["apps"][1]["launch"].update(path="relative.exe"),
            "absolute path",
        ),
        (lambda value: value["apps"][0].update(icon="../secret.png"), "invalid app icon"),
        (lambda value: value["apps"][0].update(available="yes"), "available must"),
    ],
)
def test_invalid_config_is_rejected(valid_config: dict, mutate, message: str) -> None:
    mutate(valid_config)
    with pytest.raises(ValueError, match=message):
        validate_config(valid_config)


def test_flat_version_one_config_is_migrated(valid_config: dict) -> None:
    app = valid_config["apps"][1]
    app.pop("launch")
    app["program"] = str(Path(valid_config["browsers"]["edge"]["path"]).with_name("app.exe"))
    app["args"] = ["--safe"]
    migrated = migrate_config(valid_config)
    assert migrated["apps"][1]["launch"]["type"] == "program"
    assert "program" not in migrated["apps"][1]
    assert "program" in valid_config["apps"][1]


def test_hot_reload_keeps_last_valid_configuration(store: ConfigStore) -> None:
    assert store.get()["apps"][0]["id"] == "website"
    store.path.write_text("{ broken", encoding="utf-8")
    assert store.get()["apps"][0]["id"] == "website"
    assert "Expecting" in store.error


def test_unknown_app_and_shell_style_id_are_rejected(store: ConfigStore) -> None:
    launcher = AppLauncher(store)
    with pytest.raises(ValueError, match="unknown app"):
        launcher.launch_args("missing")
    with pytest.raises(ValueError, match="unknown app"):
        launcher.launch_args("x & shutdown")


def test_control_validation_and_mouse_clamps(store: ConfigStore) -> None:
    backend = FakeBackend()
    control = ControlService(backend, AppLauncher(store))
    control.mouse({"type": "move", "dx": 999, "dy": -999})
    control.mouse({"type": "wheel", "delta": 9999})
    assert backend.events == [("move", 120.0, -120.0), ("wheel", 480)]
    with pytest.raises(ValueError, match="unknown action"):
        control.action("run:arbitrary-command")
    with pytest.raises(ValueError, match="too long"):
        control.text("x" * (MAX_TEXT_LENGTH + 1))
    with pytest.raises(ValueError, match="invalid mouse button"):
        control.mouse({"type": "click", "button": "middle"})
    with pytest.raises(ValueError, match="unknown power action"):
        control.power("hybrid arbitrary command")
    with pytest.raises(ValueError, match="numeric"):
        control.mouse({"type": "move", "dx": "NaN", "dy": 0})


def test_sleep_command_requests_suspend_without_disabling_wake_events() -> None:
    command = _windows_sleep_command()
    script = base64.b64decode(command[-1]).decode("utf-16-le")

    assert command[:3] == ["powershell.exe", "-NoProfile", "-NonInteractive"]
    assert "PowerState]::Suspend,$false,$false" in script
    assert "SetSuspendState" in script


def test_windows_mouse_move_preserves_fractional_deltas() -> None:
    events = []

    class User32:
        def SendInput(self, count, inputs, _size):
            events.extend(
                (inputs[index].mi.dwFlags, inputs[index].mi.dx, inputs[index].mi.dy)
                for index in range(count)
            )
            return count

    backend = WindowsBackend.__new__(WindowsBackend)
    backend.user32 = User32()
    backend._mouse_remainder_x = 0.0
    backend._mouse_remainder_y = 0.0

    backend.mouse_move(0.4, -0.4)
    backend.mouse_move(0.4, -0.4)
    assert events == []

    backend.mouse_move(0.4, -0.4)
    assert events == [(WindowsBackend.MOUSEEVENTF_MOVE, 1, -1)]
    assert backend._mouse_remainder_x == pytest.approx(0.2)
    assert backend._mouse_remainder_y == pytest.approx(-0.2)


def test_process_launch_uses_argument_array_without_shell(store: ConfigStore) -> None:
    calls = []
    launcher = AppLauncher(store, lambda *args, **kwargs: calls.append((args, kwargs)))
    launcher.launch("player")
    args, kwargs = calls[0]
    assert args[0][1:] == ["--safe", "value with spaces"]
    assert kwargs["shell"] is False
    assert kwargs["close_fds"] is True


def test_elevation_required_falls_back_to_uac_shell_launch(
    store: ConfigStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr("phone_remote.app_launcher.sys.platform", "win32")

    def requires_elevation(*_args, **_kwargs):
        error = OSError("elevation required")
        error.winerror = 740
        raise error

    launcher = AppLauncher(
        store,
        requires_elevation,
        elevation_launcher=lambda args, cwd: calls.append((args, cwd)),
    )
    launcher.launch("player")

    assert calls == [
        (
            [
                str(Path(store.get()["apps"][1]["launch"]["path"])),
                "--safe",
                "value with spaces",
            ],
            str(Path(store.get()["apps"][1]["launch"]["path"]).parent),
        )
    ]


def test_public_apps_report_missing_program(store: ConfigStore) -> None:
    program = Path(store.get()["apps"][1]["launch"]["path"])
    program.unlink()
    apps = {item["id"]: item for item in store.public_apps()}
    assert apps["player"]["available"] is False
