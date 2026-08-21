from __future__ import annotations

import subprocess
import sys


def hidden_window_kwargs() -> dict[str, int]:
    """Keep companion-owned child processes invisible in windowed builds."""
    if sys.platform != "win32":
        return {}
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    }
