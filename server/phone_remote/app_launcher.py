from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .config import ConfigStore

ERROR_ELEVATION_REQUIRED = 740
SW_SHOWNORMAL = 1


class AppLauncher:
    def __init__(
        self,
        config: ConfigStore,
        process_factory: Callable[..., Any] = subprocess.Popen,
        elevation_launcher: Callable[[list[str], str | None], None] | None = None,
    ):
        self.config = config
        self.process_factory = process_factory
        self.elevation_launcher = elevation_launcher or launch_with_uac

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
        try:
            self.process_factory(
                list(args),
                cwd=cwd,
                close_fds=True,
                shell=False,
            )
        except OSError as exc:
            if (
                sys.platform != "win32"
                or getattr(exc, "winerror", None) != ERROR_ELEVATION_REQUIRED
                or not Path(executable).is_absolute()
            ):
                raise
            self.elevation_launcher(list(args), cwd)


def launch_with_uac(args: list[str], cwd: str | None) -> None:
    """Use the Windows Shell so requireAdministrator applications can request consent."""
    if sys.platform != "win32" or not args:
        raise OSError("UAC launch is only available on Windows")
    import ctypes

    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.argtypes = (
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_int,
    )
    shell_execute.restype = ctypes.c_void_p
    parameters = subprocess.list2cmdline(args[1:]) if len(args) > 1 else None
    result = shell_execute(None, "runas", args[0], parameters, cwd, SW_SHOWNORMAL)
    status = int(result or 0)
    if status <= 32:
        raise ValueError("Windows UAC approval was declined or unavailable")


def command_contains_shell_metacharacters(args: Sequence[str]) -> bool:
    """Diagnostic helper; arguments remain safe because no command shell is used."""
    return any(any(character in value for character in "&|<>^") for value in args)
