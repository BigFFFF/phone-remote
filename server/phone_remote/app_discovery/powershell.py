from __future__ import annotations

import base64
import json
import os
import subprocess
from typing import Any

from ..subprocess_utils import hidden_window_kwargs

_UTF8_PREAMBLE = r"""
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
"""


def run_powershell_json(
    script: str,
    *,
    environment: dict[str, str] | None = None,
    timeout: int = 60,
) -> Any:
    """Run Windows PowerShell with deterministic UTF-8 JSON output."""
    encoded = base64.b64encode((_UTF8_PREAMBLE + script).encode("utf-16-le")).decode("ascii")
    process_environment = os.environ.copy()
    if environment:
        process_environment.update(environment)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        env=process_environment,
        capture_output=True,
        timeout=timeout,
        check=False,
        shell=False,
        **hidden_window_kwargs(),
    )
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(error or f"PowerShell exited with status {result.returncode}")
    output = result.stdout.decode("utf-8-sig", errors="strict").strip()
    return json.loads(output) if output else []
