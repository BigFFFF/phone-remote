from __future__ import annotations

import subprocess
import sys
import webbrowser
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from .api import ApiContext
from .localization import UiLanguageStore
from .network import is_private_lan, set_start_with_windows, start_with_windows_enabled
from .subprocess_utils import hidden_window_kwargs

_TRAY_TEXT = {
    "zh": {
        "running": "运行中",
        "applications": "应用",
        "open_remote": "打开遥控器",
        "pair": "配对新设备",
        "devices": "已配对设备",
        "startup": "开机启动",
        "copy": "复制设备地址",
        "language": "语言",
        "exit": "退出",
        "pairing_code": "配对码",
        "valid": "秒内有效，一次性使用。",
        "copied": "地址已复制",
    },
    "en": {
        "running": "Running",
        "applications": "Applications",
        "open_remote": "Open Remote",
        "pair": "Pair New Device",
        "devices": "Paired Devices",
        "startup": "Start with Windows",
        "copy": "Copy Device Address",
        "language": "Language",
        "exit": "Exit",
        "pairing_code": "Pairing code",
        "valid": "seconds, one-time use.",
        "copied": "Address copied",
    },
}


class PairingDisplay:
    def __init__(self, *, print_codes: bool = False, ui_language: UiLanguageStore | None = None):
        self.print_codes = print_codes
        self.ui_language = ui_language
        self.icon: pystray.Icon | None = None

    def attach(self, icon: pystray.Icon) -> None:
        self.icon = icon

    def __call__(self, code: str, lifetime: int) -> None:
        if self.print_codes:
            print(f"Phone Remote pairing code: {code} (valid for {lifetime} seconds)", flush=True)
        if self.icon is not None:
            language = self.ui_language.get() if self.ui_language else "en"
            text = _TRAY_TEXT[language]
            self.icon.notify(
                f"{text['pairing_code']}: {code}\n{lifetime} {text['valid']}", "Phone Remote"
            )


class TrayApplication:
    def __init__(
        self,
        context: ApiContext,
        pairing_display: PairingDisplay,
        stop: Callable[[], None],
        startup_command,
        ui_language: UiLanguageStore,
    ):
        self.context = context
        self.pairing_display = pairing_display
        self.stop_callback = stop
        self.startup_command = startup_command
        self.ui_language = ui_language
        self.remote_url = f"http://127.0.0.1:{context.web_port or context.port}"
        self.base_url = self.remote_url
        self.icon = pystray.Icon(
            "Phone Remote",
            _create_icon(),
            "Phone Remote",
            menu=pystray.Menu(
                pystray.MenuItem(
                    lambda _: f"{self._text('running')} · {context.identity.display_name}",
                    None,
                    enabled=False,
                ),
                pystray.MenuItem(
                    lambda _: self._text("applications"), self.open_applications, default=True
                ),
                pystray.MenuItem(lambda _: self._text("open_remote"), self.open_remote),
                pystray.MenuItem(lambda _: self._text("pair"), self.pair_new_device),
                pystray.MenuItem(lambda _: self._text("devices"), self.open_paired_devices),
                pystray.MenuItem(
                    lambda _: self._text("startup"),
                    self.toggle_startup,
                    checked=lambda _: start_with_windows_enabled(),
                ),
                pystray.MenuItem(lambda _: self._text("copy"), self.copy_address),
                pystray.MenuItem(
                    lambda _: self._text("language"),
                    pystray.Menu(
                        pystray.MenuItem(
                            "中文",
                            self.use_chinese,
                            checked=lambda _: self.ui_language.get() == "zh",
                            radio=True,
                        ),
                        pystray.MenuItem(
                            "English",
                            self.use_english,
                            checked=lambda _: self.ui_language.get() == "en",
                            radio=True,
                        ),
                    ),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(lambda _: self._text("exit"), self.exit),
            ),
        )
        pairing_display.attach(self.icon)

    def run(self) -> None:
        self.icon.run()

    def _text(self, key: str) -> str:
        return _TRAY_TEXT[self.ui_language.get()][key]

    def _set_language(self, language: str) -> None:
        self.ui_language.set(language)
        self.icon.update_menu()

    def use_chinese(self, *_args) -> None:
        self._set_language("zh")

    def use_english(self, *_args) -> None:
        self._set_language("en")

    def open_remote(self, *_args) -> None:
        webbrowser.open(self.remote_url)

    def open_management(self, *_args) -> None:
        webbrowser.open(f"{self.base_url}/manage/#{self.context.admin_token}")

    def open_applications(self, *_args) -> None:
        webbrowser.open(f"{self.base_url}/manage/?section=applications#{self.context.admin_token}")

    def open_paired_devices(self, *_args) -> None:
        webbrowser.open(f"{self.base_url}/manage/?section=devices#{self.context.admin_token}")

    def pair_new_device(self, *_args) -> None:
        webbrowser.open(f"{self.base_url}/manage/?section=pairing#{self.context.admin_token}")

    def toggle_startup(self, *_args) -> None:
        set_start_with_windows(self.startup_command, not start_with_windows_enabled())
        self.icon.update_menu()

    def copy_address(self, *_args) -> None:
        from .network import local_ipv4_addresses

        addresses = local_ipv4_addresses()
        host = next((value for value in addresses if is_private_lan(value)), "127.0.0.1")
        value = f"http://{host}:{self.context.web_port or self.context.port}"
        if sys.platform == "win32":
            subprocess.run(
                ["clip.exe"],
                input=value,
                text=True,
                timeout=5,
                check=False,
                shell=False,
                **hidden_window_kwargs(),
            )
        self.icon.notify(value, self._text("copied"))

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
