import json
from pathlib import Path

import pytest
from PIL import Image

from phone_remote.app_discovery.discovery import ApplicationDiscovery, merge_candidates
from phone_remote.app_discovery.models import appx_candidate, program_candidate
from phone_remote.app_discovery.registry import _is_launchable_registry_entry
from phone_remote.app_discovery.start_menu import _best_name, _is_user_facing_shortcut
from phone_remote.catalog import ApplicationCatalog
from phone_remote.config import ConfigStore


class Provider:
    source = "test"

    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def discover(self):
        self.calls += 1
        return list(self.candidates)


@pytest.fixture()
def catalog_setup(tmp_path: Path):
    browser = tmp_path / "edge.exe"
    browser.touch()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "browsers": {"edge": {"path": str(browser), "args": [], "fullscreenArgs": []}},
                "apps": [],
            }
        ),
        encoding="utf-8",
    )
    default_icon = tmp_path / "bundled-default.svg"
    default_icon.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    return tmp_path, ConfigStore(config_path, tmp_path / "icons"), default_icon


def test_candidate_normalization_rejects_untrusted_paths(tmp_path: Path) -> None:
    executable = tmp_path / "app.exe"
    executable.touch()
    assert program_candidate(name="App", executable=str(executable), source="test") is not None
    assert program_candidate(name="App", executable="relative.exe", source="test") is None
    assert (
        program_candidate(name="App", executable=str(tmp_path / "missing.exe"), source="test")
        is None
    )
    assert (
        program_candidate(name="App", executable=str(tmp_path / "file.cmd"), source="test") is None
    )
    assert appx_candidate(name="Store", app_user_model_id="bad id", source="test") is None


def test_start_menu_filters_non_app_shortcuts_and_repairs_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    windows = tmp_path / "Windows"
    system_tool = windows / "System32" / "control.exe"
    system_tool.parent.mkdir(parents=True)
    system_tool.touch()
    uninstall = tmp_path / "Programs" / "uninstall_complete.exe"
    uninstall.parent.mkdir()
    uninstall.touch()
    app = tmp_path / "Programs" / "Weixin.exe"
    app.touch()
    monkeypatch.setenv("WINDIR", str(windows))

    assert not _is_user_facing_shortcut({"name": "Administrative Tools", "target": system_tool})
    assert not _is_user_facing_shortcut({"name": "WeGame卸载", "target": uninstall})
    assert _is_user_facing_shortcut({"name": "微信", "target": app})
    assert (
        _best_name(
            {"name": "微��", "productName": "微信", "fileDescription": "Weixin"},
            "Weixin",
        )
        == "微信"
    )


def test_duplicate_candidates_merge_and_known_app_matches(tmp_path: Path) -> None:
    steam = tmp_path / "Steam.exe"
    steam.touch()
    low = program_candidate(name="steam", executable=str(steam), source="registry", confidence=50)
    high = program_candidate(
        name="Steam", executable=str(steam), source="start-menu", confidence=90
    )
    result = merge_candidates([low, high])
    assert len(result) == 1
    assert result[0].known_app_id == "steam"
    assert result[0].category == "Games / Launchers"
    assert result[0].launch["args"] == ["steam://open/bigpicture"]
    assert result[0].sources == ["registry", "start-menu"]


def test_steam_uninstaller_is_not_a_known_app_or_registry_launcher(tmp_path: Path) -> None:
    launcher = tmp_path / "Steam.exe"
    uninstaller = tmp_path / "uninstall.exe"
    launcher.touch()
    uninstaller.touch()
    wrong = program_candidate(
        name="Steam", executable=str(uninstaller), source="registry-uninstall", confidence=55
    )
    right = program_candidate(
        name="Steam", executable=str(launcher), source="start-menu", confidence=90
    )

    result = merge_candidates([wrong, right])

    assert len(result) == 2
    assert wrong is not None and wrong.known_app_id is None
    assert right is not None and right.known_app_id == "steam"
    assert not _is_launchable_registry_entry("Steam", str(uninstaller))
    assert not _is_launchable_registry_entry("卸载 Steam", str(launcher))
    assert _is_launchable_registry_entry("Steam", str(launcher))


def test_provider_failure_does_not_abort_scan(tmp_path: Path) -> None:
    executable = tmp_path / "app.exe"
    executable.touch()

    class BrokenProvider:
        source = "broken"

        def discover(self):
            raise OSError("registry unavailable")

    valid = program_candidate(name="App", executable=str(executable), source="valid")
    discovery = ApplicationDiscovery([BrokenProvider(), Provider([valid])])
    assert [item.name for item in discovery.scan()] == ["App"]


def test_catalog_requires_rescan_before_approval_and_never_auto_configures(
    catalog_setup,
) -> None:
    tmp_path, store, default_icon = catalog_setup
    executable = tmp_path / "Steam.exe"
    executable.touch()
    candidate = program_candidate(
        name="Steam", executable=str(executable), source="start-menu", confidence=90
    )
    catalog = ApplicationCatalog(store, ApplicationDiscovery([Provider([candidate])]), default_icon)
    with pytest.raises(ValueError, match="rescan"):
        catalog.approve(candidate.discovery_id)
    scanned = catalog.rescan()
    assert scanned[0]["configured"] is False
    assert store.get()["apps"] == []
    approved = catalog.approve(candidate.discovery_id)
    assert approved["id"] == "steam"
    assert approved["launch"]["args"] == ["steam://open/bigpicture"]
    assert approved["icon"] == "steam.png"
    assert (tmp_path / "icons" / "steam.png").exists()


def test_initial_discovery_configures_edge_and_steam_once(catalog_setup) -> None:
    tmp_path, store, default_icon = catalog_setup
    edge = tmp_path / "msedge.exe"
    steam = tmp_path / "Steam.exe"
    edge.touch()
    steam.touch()
    candidates = [
        program_candidate(
            name="Microsoft Edge",
            executable=str(edge),
            source="app-paths",
            confidence=90,
        ),
        program_candidate(
            name="Steam",
            executable=str(steam),
            source="start-menu",
            confidence=90,
        ),
    ]
    provider = Provider(candidates)
    catalog = ApplicationCatalog(store, ApplicationDiscovery([provider]), default_icon)

    added = catalog.initialize_known_apps()

    config = store.get()
    assert [item["id"] for item in added] == ["edge", "steam"]
    assert [item["id"] for item in config["apps"]] == ["edge", "steam"]
    assert config["browsers"]["edge"]["path"] == str(edge)
    assert config["apps"][1]["launch"]["args"] == ["steam://open/bigpicture"]
    assert config["initialDiscoveryComplete"] is True
    assert provider.calls == 1
    assert catalog.initialize_known_apps() == []
    assert provider.calls == 1


def test_initial_discovery_prefers_launcher_and_repairs_legacy_steam_uninstaller(
    catalog_setup,
) -> None:
    tmp_path, store, default_icon = catalog_setup
    uninstaller = tmp_path / "uninstall.exe"
    steam = tmp_path / "Steam.exe"
    uninstaller.touch()
    steam.touch()
    config = store.get()
    config["initialDiscoveryComplete"] = True
    config["apps"].append(
        {
            "id": "steam",
            "name": "Steam",
            "enabled": True,
            "available": True,
            "icon": "default.svg",
            "launch": {"type": "program", "path": str(uninstaller), "args": []},
        }
    )
    store.write(config)
    candidates = [
        program_candidate(
            name="Steam", executable=str(uninstaller), source="registry-uninstall", confidence=55
        ),
        program_candidate(name="Steam", executable=str(steam), source="start-menu", confidence=90),
    ]
    catalog = ApplicationCatalog(
        store,
        ApplicationDiscovery([Provider(candidates)]),
        default_icon,
    )

    assert catalog.initialize_known_apps() == []
    repaired = store.get()["apps"][0]
    assert repaired["launch"]["path"] == str(steam)
    assert repaired["launch"]["args"] == ["steam://open/bigpicture"]


def test_rescan_marks_missing_without_overwriting_user_fields(catalog_setup) -> None:
    tmp_path, store, default_icon = catalog_setup
    executable = tmp_path / "player.exe"
    executable.touch()
    candidate = program_candidate(name="Player", executable=str(executable), source="test")
    provider = Provider([candidate])
    catalog = ApplicationCatalog(store, ApplicationDiscovery([provider]), default_icon)
    catalog.rescan()
    catalog.approve(candidate.discovery_id)
    config = store.get()
    config["apps"][0]["name"] = "My Player"
    store.write(config)
    executable.unlink()
    provider.candidates = []
    catalog.rescan()
    app = store.get()["apps"][0]
    assert app["name"] == "My Player"
    assert app["available"] is False


def test_rescan_replaces_existing_metadata_with_discovered_metadata(catalog_setup) -> None:
    tmp_path, store, default_icon = catalog_setup
    executable = tmp_path / "weixin.exe"
    executable.touch()
    source_icon = tmp_path / "weixin-source.png"
    Image.new("RGBA", (32, 32), (27, 198, 95, 255)).save(source_icon)
    config = store.get()
    config["apps"].append(
        {
            "id": "weixin",
            "name": "My old name",
            "enabled": True,
            "available": True,
            "icon": "custom.png",
            "launch": {"type": "program", "path": str(executable), "args": []},
        }
    )
    store.write(config)
    candidate = program_candidate(
        name="微信", executable=str(executable), source="start-menu", icon=str(source_icon)
    )
    catalog = ApplicationCatalog(store, ApplicationDiscovery([Provider([candidate])]), default_icon)

    catalog.rescan()

    app = store.get()["apps"][0]
    assert app["name"] == "微信"
    assert app["icon"] == "weixin.png"
    assert (tmp_path / "icons" / "weixin.png").is_file()


def test_manual_catalog_validates_programs_and_websites(catalog_setup) -> None:
    tmp_path, store, default_icon = catalog_setup
    catalog = ApplicationCatalog(store, ApplicationDiscovery([]), default_icon)
    executable = tmp_path / "manual.exe"
    executable.touch()
    website_icon = tmp_path / "icons" / "example.png"
    catalog.icons.materialize_website = lambda _url, destination: (
        destination.parent.mkdir(parents=True, exist_ok=True),
        Image.new("RGBA", (32, 32), (30, 120, 240, 255)).save(destination),
        True,
    )[-1]
    program = catalog.add_program("Manual", str(executable), ["--value", "with spaces"])
    website = catalog.add_website("Example", "edge", "https://example.com", fullscreen=True)
    assert program["launch"]["args"] == ["--value", "with spaces"]
    assert website["launch"]["fullscreen"] is True
    assert website["icon"] == "example.png"
    assert website_icon.is_file()
    with pytest.raises(ValueError, match="existing absolute"):
        catalog.add_program("Bad", "cmd.exe")
    with pytest.raises(ValueError, match="http or https"):
        catalog.add_website("Bad", "edge", "file:///secret")
    with pytest.raises(ValueError, match="already configured"):
        catalog.add_website("Again", "edge", "https://example.com")


def test_catalog_independent_enable_and_remove(catalog_setup) -> None:
    _, store, default_icon = catalog_setup
    catalog = ApplicationCatalog(store, ApplicationDiscovery([]), default_icon)
    app = catalog.add_website("Example", "edge", "https://example.com")
    assert catalog.set_enabled(app["id"], False)["enabled"] is False
    assert catalog.remove(app["id"])
    assert not catalog.remove(app["id"])
