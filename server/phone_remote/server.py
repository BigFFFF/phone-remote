from __future__ import annotations

import argparse
import ctypes
import os
import sys
import tempfile
import threading
import traceback
from ctypes import wintypes
from pathlib import Path
from typing import Any

from .api import ApiContext, PhoneRemoteServer
from .app_discovery import ApplicationDiscovery
from .app_launcher import AppLauncher
from .auth import CredentialStore
from .catalog import ApplicationCatalog
from .config import DEFAULT_CONFIG, ConfigStore, validate_config
from .discovery import DiscoveryPublisher
from .localization import UiLanguageStore
from .logging_setup import configure_logging
from .network import NetworkDiagnostics, set_start_with_windows
from .pairing import PairingManager
from .paths import RuntimePaths
from .security import IdentityManager
from .state import StateStore
from .tray import PairingDisplay, TrayApplication
from .windows_control import ControlService, WindowsBackend

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_WEB_PORT = 8766
ERROR_ALREADY_EXISTS = 183


class ServerRuntime:
    def __init__(self, args: argparse.Namespace):
        if args.data_dir:
            os.environ["PHONE_REMOTE_DATA_DIR"] = str(Path(args.data_dir).resolve())
        if args.config:
            os.environ["PHONE_REMOTE_CONFIG"] = str(Path(args.config).resolve())
        self.args = args
        self.paths = RuntimePaths.resolve()
        migration_events = self.paths.prepare()
        self.logger = configure_logging(self.paths.log_root, verbose=args.verbose)
        for event in migration_events:
            self.logger.info("data migration: %s", event)
        self.state = StateStore(self.paths.state_path)
        self.identity_manager = IdentityManager(
            self.state,
            self.paths.identity_key_path,
            self.paths.certificate_path,
            self.paths.tls_key_path,
        )
        self.identity = self.identity_manager.ensure(args.name)
        self.config = ConfigStore(self.paths.config_path, self.paths.icon_root)
        self.config.initialize()
        self.config.get()
        self.credentials = CredentialStore(self.state)
        self.ui_language = UiLanguageStore(self.paths.data_root / "ui-language.txt")
        self.pairing_display = PairingDisplay(
            print_codes=args.print_pair_code or args.no_tray,
            ui_language=self.ui_language,
        )
        self.pairing = PairingManager(self.credentials, notifier=self.pairing_display)
        self.launcher = AppLauncher(self.config)
        self.control = ControlService(WindowsBackend(), self.launcher)
        self.app_discovery = ApplicationDiscovery(logger=self.logger)
        self.catalog = ApplicationCatalog(
            self.config,
            self.app_discovery,
            self.paths.bundle_root / "resources" / "icons" / "default.svg",
        )
        self.network = NetworkDiagnostics()
        self.startup_command = tuple(
            [sys.executable]
            if getattr(sys, "frozen", False)
            else [sys.executable, "-m", "phone_remote"]
        )
        self.context = ApiContext(
            identity=self.identity,
            paths=self.paths,
            config=self.config,
            credentials=self.credentials,
            pairing=self.pairing,
            control=self.control,
            catalog=self.catalog,
            network=self.network,
            logger=self.logger,
            port=args.port,
            web_port=args.port if args.insecure_http else args.web_port,
            startup_command=self.startup_command,
            ui_language=self.ui_language,
            catalog_ready=threading.Event(),
        )
        self.context.start_network_monitor()
        self.http = PhoneRemoteServer((args.host, args.port), self.context)
        self.web_http: PhoneRemoteServer | None = None
        if not args.insecure_http:
            ssl_context = self.identity_manager.create_ssl_context()
            self.http.socket = ssl_context.wrap_socket(self.http.socket, server_side=True)
            self.web_http = PhoneRemoteServer(
                (args.host, args.web_port),
                self.context,
                private_lan_only=True,
            )
        self.publisher = DiscoveryPublisher(self.identity, args.port, self.logger)
        self._server_threads: list[threading.Thread] = []
        self._maintenance_threads: list[threading.Thread] = []

    def run(self) -> None:
        scheme = "http" if self.args.insecure_http else "https"
        self.logger.info(
            "server starting address=%s port=%s tls=%s server_id=%s",
            self.args.host,
            self.args.port,
            not self.args.insecure_http,
            self.identity.server_id,
        )
        if self.web_http is not None:
            self.logger.info(
                "Web Remote starting address=%s port=%s tls=False private_lan_only=True",
                self.args.host,
                self.args.web_port,
            )
        self._start_background_server(self.http, "phone-remote-api")
        self._start_background_server(self.web_http, "phone-remote-web")
        self._start_background_maintenance(
            self._initialize_known_apps,
            "phone-remote-initial-app-discovery",
        )
        if not self.args.no_discovery and not self.args.insecure_http:
            self._start_background_maintenance(
                self.publisher.start,
                "phone-remote-discovery-publisher",
            )
        if self.args.no_tray:
            print(
                f"Phone Remote {self.identity.display_name}: {scheme}://127.0.0.1:{self.args.port}",
                flush=True,
            )
            if self.web_http is not None:
                print(
                    f"Web Remote: http://127.0.0.1:{self.args.web_port}",
                    flush=True,
                )
            try:
                while any(thread.is_alive() for thread in self._server_threads):
                    for thread in self._server_threads:
                        thread.join(timeout=0.5)
            finally:
                self.close()
            return

        tray = TrayApplication(
            self.context,
            self.pairing_display,
            self.stop,
            self.startup_command,
            self.ui_language,
        )
        try:
            tray.run()
        finally:
            self.close()

    def stop(self) -> None:
        for server in (self.http, self.web_http):
            if server is not None:
                server.shutdown()

    def close(self) -> None:
        self.stop()
        for thread in self._server_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        self.publisher.close()
        self.http.server_close()
        if self.web_http is not None:
            self.web_http.server_close()
        self.context.stop_network_monitor()
        self.logger.info("server stopped")

    def _start_background_server(self, server: PhoneRemoteServer | None, name: str) -> None:
        if server is None:
            return
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.25},
            name=name,
            daemon=True,
        )
        thread.start()
        self._server_threads.append(thread)

    def _start_background_maintenance(self, target: Any, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        self._maintenance_threads.append(thread)

    def _initialize_known_apps(self) -> None:
        try:
            added_apps = self.catalog.initialize_known_apps()
            if added_apps:
                self.logger.info(
                    "initial application discovery configured apps=%s",
                    ",".join(item["id"] for item in added_apps),
                )
        except Exception:
            self.logger.exception("initial application discovery failed")
        finally:
            self.context.catalog_ready.set()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phone Remote Windows companion")
    parser.add_argument("--host", default=os.environ.get("PHONE_REMOTE_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PHONE_REMOTE_PORT", DEFAULT_PORT))
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=int(os.environ.get("PHONE_REMOTE_WEB_PORT", DEFAULT_WEB_PORT)),
        help="Private-LAN HTTP port for browser-based Web Remote",
    )
    parser.add_argument("--name", help="display name (used only when identity is first created)")
    parser.add_argument("--data-dir", help="override the per-user data directory")
    parser.add_argument("--config", help="override config.json path")
    parser.add_argument("--no-tray", action="store_true", help="run in console mode")
    parser.add_argument("--no-discovery", action="store_true", help="disable mDNS advertisement")
    parser.add_argument(
        "--insecure-http",
        action="store_true",
        help="development only: disable TLS (never use on a LAN)",
    )
    parser.add_argument("--print-pair-code", action="store_true", help="print pairing codes")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--install-startup", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--remove-startup", action="store_true", help=argparse.SUPPRESS)
    return parser


def acquire_single_instance(port: int) -> Any:
    if sys.platform != "win32":
        return object()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.CreateMutexW(None, False, f"Local\\PhoneRemote-{port}")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_single_instance(handle: Any) -> None:
    if sys.platform == "win32" and handle:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(handle)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.port <= 65535:
        raise SystemExit("port must be between 1 and 65535")
    if not 1 <= args.web_port <= 65535:
        raise SystemExit("web port must be between 1 and 65535")
    if not args.insecure_http and args.web_port == args.port:
        raise SystemExit("web port must differ from the HTTPS API port")
    if args.smoke_test:
        return run_smoke_test()
    if args.install_startup or args.remove_startup:
        command = (
            [sys.executable]
            if getattr(sys, "frozen", False)
            else [sys.executable, "-m", "phone_remote"]
        )
        set_start_with_windows(command, args.install_startup)
        return 0
    mutex = acquire_single_instance(args.port)
    if mutex is None:
        return 0
    try:
        ServerRuntime(args).run()
    except KeyboardInterrupt:
        return 0
    finally:
        release_single_instance(mutex)
    return 0


def run_smoke_test() -> int:
    """Exercise packaged resources and crypto without user-data or system mutations."""
    try:
        paths = RuntimePaths.resolve()
        validate_config(DEFAULT_CONFIG)
        for required in (
            paths.web_root / "index.html",
            paths.web_root / "manage.html",
            paths.bundle_root / "resources" / "icons" / "default.svg",
        ):
            if not required.is_file():
                return 1
        with tempfile.TemporaryDirectory(prefix="phone-remote-smoke-") as directory:
            root = Path(directory)
            manager = IdentityManager(
                StateStore(root / "state.json"),
                root / "identity.key",
                root / "server.crt",
                root / "server.key",
            )
            manager.ensure("Smoke Test")
            manager.create_ssl_context()
        WindowsBackend()
    except Exception:
        report = os.environ.get("PHONE_REMOTE_SMOKE_REPORT")
        if report:
            Path(report).write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    return 0
