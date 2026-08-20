import json
from pathlib import Path

import pytest

from phone_remote.app_discovery.discovery import ApplicationDiscovery, merge_candidates
from phone_remote.app_discovery.models import appx_candidate, program_candidate
from phone_remote.catalog import ApplicationCatalog
from phone_remote.config import ConfigStore


class Provider:
    source = "test"

    def __init__(self, candidates):
        self.candidates = candidates

    def discover(self):
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
    assert (tmp_path / "icons" / "default.svg").exists()


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


def test_manual_catalog_validates_programs_and_websites(catalog_setup) -> None:
    tmp_path, store, default_icon = catalog_setup
    catalog = ApplicationCatalog(store, ApplicationDiscovery([]), default_icon)
    executable = tmp_path / "manual.exe"
    executable.touch()
    program = catalog.add_program("Manual", str(executable), ["--value", "with spaces"])
    website = catalog.add_website("Example", "edge", "https://example.com", fullscreen=True)
    assert program["launch"]["args"] == ["--value", "with spaces"]
    assert website["launch"]["fullscreen"] is True
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
