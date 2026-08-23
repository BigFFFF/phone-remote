# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


repository_root = Path(SPECPATH).resolve().parents[1]
server_root = repository_root / "server"

hidden_imports = collect_submodules("zeroconf") + ["pystray._win32"]

analysis = Analysis(
    [str(server_root / "run_phone_remote.py")],
    pathex=[str(server_root)],
    binaries=[],
    datas=[
        (str(server_root / "web"), "web"),
        (str(server_root / "resources"), "resources"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="PhoneRemote",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",
    codesign_identity=None,
    entitlements_file=None,
)
