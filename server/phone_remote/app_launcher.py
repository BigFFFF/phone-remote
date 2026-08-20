from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .config import ConfigStore


class AppLauncher:
    def __init__(
        self,
        config: ConfigStore,
        process_factory: Callable[..., Any] = subprocess.Popen,
    ):
        self.config = config
        self.process_factory = process_factory

    def launch_args(self, app_id: str) -> list[str]:
        config = self.config.get()
        app = next(
            (item for item in config["apps"] if item["enabled"] and item["id"] == app_id),
            None,
        )
        if app is None:
            raise ValueError("unknown app")
        if not app.get("available", True):
            raise ValueError("app is unavailable")
        launch = app["launch"]
        if launch["type"] == "program":
            return [os.path.expandvars(launch["path"]), *launch["args"]]
        if launch["type"] == "appx":
            return ["explorer.exe", f"shell:AppsFolder\\{launch['appUserModelId']}"]
        browser = config["browsers"][launch["browser"]]
        args = [os.path.expandvars(browser["path"]), *browser["args"]]
        if launch["fullscreen"]:
            args.extend(browser["fullscreenArgs"])
        if launch["url"]:
            args.append(launch["url"])
        return args

    def launch(self, app_id: str) -> None:
        args = self.launch_args(app_id)
        executable = args[0]
        if Path(executable).is_absolute():
            if not Path(executable).is_file():
                raise ValueError("app executable is unavailable")
            cwd: str | None = str(Path(executable).parent)
        elif executable.lower() == "explorer.exe":
            cwd = None
        else:
            raise ValueError("launch executable is not approved")
        self.process_factory(
            list(args),
            cwd=cwd,
            close_fds=True,
            shell=False,
        )


def command_contains_shell_metacharacters(args: Sequence[str]) -> bool:
    """Diagnostic helper; arguments remain safe because no command shell is used."""
    return any(any(character in value for character in "&|<>^") for value in args)
