from __future__ import annotations

import argparse
import ctypes
import json
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
from .config import ConfigStore, validate_config
from .discovery import DiscoveryPublisher
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
        self.config.get()
        self.credentials = CredentialStore(self.state)
        self.pairing_display = PairingDisplay(print_codes=args.print_pair_code or args.no_tray)
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
        )
        self.http = PhoneRemoteServer((args.host, args.port), self.context)
        if not args.insecure_http:
            ssl_context = self.identity_manager.create_ssl_context()
            self.http.socket = ssl_context.wrap_socket(self.http.socket, server_side=True)
        self.publisher = DiscoveryPublisher(self.identity, args.port, self.logger)
        self._server_thread: threading.Thread | None = None

    def run(self) -> None:
        scheme = "http" if self.args.insecure_http else "https"
        self.logger.info(
            "server starting address=%s port=%s tls=%s server_id=%s",
            self.args.host,
            self.args.port,
            not self.args.insecure_http,
            self.identity.server_id,
        )
        if not self.args.no_discovery and not self.args.insecure_http:
            self.publisher.start()
        if self.args.no_tray:
            print(
                f"Phone Remote {self.identity.display_name}: {scheme}://127.0.0.1:{self.args.port}",
                flush=True,
            )
            try:
                self.http.serve_forever(poll_interval=0.25)
            finally:
                self.close()
            return

        self._server_thread = threading.Thread(
            target=self.http.serve_forever,
            kwargs={"poll_interval": 0.25},
            name="phone-remote-http",
            daemon=True,
        )
        self._server_thread.start()
        tray = TrayApplication(
            self.context,
            self.pairing_display,
            self.stop,
            [sys.executable]
            if getattr(sys, "frozen", False)
            else [sys.executable, "-m", "phone_remote"],
        )
        try:
            tray.run()
        finally:
            self.stop()
            self.close()

    def stop(self) -> None:
        threading.Thread(target=self.http.shutdown, daemon=True).start()

    def close(self) -> None:
        self.publisher.close()
        self.http.server_close()
        if self._server_thread is not None and self._server_thread.is_alive():
            self._server_thread.join(timeout=5)
        self.logger.info("server stopped")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phone Remote Windows companion")
    parser.add_argument("--host", default=os.environ.get("PHONE_REMOTE_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PHONE_REMOTE_PORT", DEFAULT_PORT))
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
        config_example = next(
            path
            for path in (
                paths.bundle_root / "config.example.json",
                paths.executable_root / "config.example.json",
            )
            if path.is_file()
        )
        validate_config(json.loads(config_example.read_text(encoding="utf-8")))
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
