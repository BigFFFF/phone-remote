import copy
import json
from pathlib import Path

import pytest

from src import server


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


def test_config_and_launch_arguments_are_preserved(valid_config: dict, tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(valid_config), encoding="utf-8")
    store = server.ConfigStore(path)

    browser_args = store.launch_args("website")
    program_args = store.launch_args("player")

    assert browser_args[1:] == [
        "--profile",
        "Phone Remote",
        "--start-fullscreen",
        "https://example.com/watch?q=1",
    ]
    assert program_args[1:] == ["--safe", "value with spaces"]


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
    ],
)
def test_invalid_config_is_rejected(valid_config: dict, mutate, message: str) -> None:
    mutate(valid_config)
    with pytest.raises(ValueError, match=message):
        server.validate_config(valid_config)


def test_unknown_and_oversized_actions_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown action"):
        server.perform("run:arbitrary-command")
    with pytest.raises(ValueError, match="too long"):
        server.send_text("x" * (server.MAX_TEXT_LENGTH + 1))


def test_mouse_values_are_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    received = []
    monkeypatch.setattr(server, "mouse_move", lambda dx, dy: received.append((dx, dy)))

    assert server.perform_mouse({"type": "move", "dx": 999, "dy": -999})["ok"]
    assert received == [(120.0, -120.0)]


def test_unknown_app_is_rejected(valid_config: dict, tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(valid_config), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown app"):
        server.ConfigStore(path).launch_args("missing")
