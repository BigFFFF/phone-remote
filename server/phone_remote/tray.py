from __future__ import annotations

import subprocess
import sys
import webbrowser
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from .api import ApiContext
from .network import set_start_with_windows, start_with_windows_enabled


class PairingDisplay:
    def __init__(self, *, print_codes: bool = False):
        self.print_codes = print_codes
        self.icon: pystray.Icon | None = None

    def attach(self, icon: pystray.Icon) -> None:
        self.icon = icon

    def __call__(self, code: str, lifetime: int) -> None:
        if self.print_codes:
            print(f"Phone Remote pairing code: {code} (valid for {lifetime} seconds)", flush=True)
        if self.icon is not None:
            self.icon.notify(f"配对码：{code}\n{lifetime} 秒内有效，一次性使用。", "Phone Remote")


class TrayApplication:
    def __init__(
        self,
        context: ApiContext,
        pairing_display: PairingDisplay,
        stop: Callable[[], None],
        startup_command,
    ):
        self.context = context
        self.pairing_display = pairing_display
        self.stop_callback = stop
        self.startup_command = startup_command
        self.base_url = f"https://127.0.0.1:{context.port}"
        self.icon = pystray.Icon(
            "Phone Remote",
            _create_icon(),
            "Phone Remote",
            menu=pystray.Menu(
                pystray.MenuItem(
                    lambda _: f"Status: Running · {context.identity.display_name}",
                    None,
                    enabled=False,
                ),
                pystray.MenuItem("Open Phone Remote", self.open_remote, default=True),
                pystray.MenuItem("Pair New Device", self.pair_new_device),
                pystray.MenuItem("Paired Devices", self.open_management),
                pystray.MenuItem("Applications", self.open_management),
                pystray.MenuItem(
                    "Start with Windows",
                    self.toggle_startup,
                    checked=lambda _: start_with_windows_enabled(),
                ),
                pystray.MenuItem("Copy Device Address", self.copy_address),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self.exit),
            ),
        )
        pairing_display.attach(self.icon)

    def run(self) -> None:
        self.icon.run()

    def open_remote(self, *_args) -> None:
        webbrowser.open(self.base_url)

    def open_management(self, *_args) -> None:
        webbrowser.open(f"{self.base_url}/manage/#{self.context.admin_token}")

    def pair_new_device(self, *_args) -> None:
        self.open_management()

    def toggle_startup(self, *_args) -> None:
        set_start_with_windows(self.startup_command, not start_with_windows_enabled())
        self.icon.update_menu()

    def copy_address(self, *_args) -> None:
        from .network import local_ipv4_addresses

        host = next(iter(local_ipv4_addresses()), "127.0.0.1")
        value = f"https://{host}:{self.context.port}"
        if sys.platform == "win32":
            subprocess.run(
                ["clip.exe"], input=value, text=True, timeout=5, check=False, shell=False
            )
        self.icon.notify(value, "Phone Remote address copied")

    def exit(self, *_args) -> None:
        self.stop_callback()
        self.icon.stop()


def _create_icon() -> Image.Image:
    image = Image.new("RGBA", (64, 64), "#162127")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((7, 7, 57, 57), radius=13, fill="#27717a")
    draw.rounded_rectangle((18, 12, 46, 52), radius=6, fill="#edf3f5")
    draw.ellipse((29, 45, 35, 51), fill="#27717a")
    return image
