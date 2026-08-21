from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image

from .app_discovery.powershell import run_powershell_json

if TYPE_CHECKING:
    from .app_discovery.models import DiscoveredApp


_RASTER_SUFFIXES = {".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".webp"}
_RESOURCE_SUFFIXES = {".dll", ".exe"}
_MAX_HTML_BYTES = 1_000_000
_MAX_ICON_BYTES = 2_000_000
_WEB_TIMEOUT_SECONDS = 4


class IconMaterializer:
    """Turn Windows icon resources and package assets into browser-safe PNG files."""

    def __init__(self, icon_root: Path):
        self.icon_root = icon_root

    def populate_candidates(self, candidates: list[DiscoveredApp]) -> None:
        self.icon_root.mkdir(parents=True, exist_ok=True)
        resource_requests: list[dict[str, object]] = []
        pending: list[tuple[DiscoveredApp, Path]] = []
        for candidate in candidates:
            source_value = candidate.icon
            if not source_value and candidate.launch.get("type") == "program":
                source_value = str(candidate.launch.get("path", ""))
            source, index = _parse_icon_source(source_value)
            destination = self.icon_root / f"discovered-{candidate.discovery_id}.png"
            if (
                source
                and source.suffix.lower() in _RASTER_SUFFIXES
                and _convert_image(source, destination)
            ):
                candidate.icon = str(destination)
                continue
            if source and source.suffix.lower() in _RESOURCE_SUFFIXES:
                resource_requests.append(
                    {"source": str(source), "index": index, "destination": str(destination)}
                )
                pending.append((candidate, destination))
                continue
            candidate.icon = None

        _extract_windows_resources(resource_requests)
        for candidate, destination in pending:
            candidate.icon = str(destination) if destination.is_file() else None

    def materialize(self, source_value: str | None, destination: Path) -> bool:
        source, index = _parse_icon_source(source_value)
        if not source:
            return False
        if source.suffix.lower() in _RASTER_SUFFIXES:
            return _convert_image(source, destination)
        if source.suffix.lower() not in _RESOURCE_SUFFIXES:
            return False
        _extract_windows_resources(
            [{"source": str(source), "index": index, "destination": str(destination)}]
        )
        return destination.is_file()

    def materialize_website(self, url: str, destination: Path) -> bool:
        try:
            page_data, final_url, content_type = _download(
                url,
                accept="text/html,application/xhtml+xml",
                maximum_bytes=_MAX_HTML_BYTES,
            )
        except (HTTPError, URLError, OSError, ValueError):
            page_data, final_url, content_type = b"", url, ""

        candidates: list[str] = []
        if "html" in content_type.casefold() or page_data.lstrip().startswith(b"<"):
            parser = _IconLinkParser()
            parser.feed(page_data.decode("utf-8", errors="replace"))
            candidates.extend(urljoin(final_url, value) for value in parser.icon_urls())
        parsed = urlsplit(final_url)
        candidates.append(urlunsplit((parsed.scheme, parsed.netloc, "/favicon.ico", "", "")))

        seen: set[str] = set()
        for candidate in candidates[:6]:
            if candidate in seen or urlsplit(candidate).scheme.lower() not in {"http", "https"}:
                continue
            seen.add(candidate)
            try:
                icon_data, _, _ = _download(
                    candidate,
                    accept="image/avif,image/webp,image/png,image/*,*/*;q=0.5",
                    maximum_bytes=_MAX_ICON_BYTES,
                )
            except (HTTPError, URLError, OSError, ValueError):
                continue
            if _convert_image_bytes(icon_data, destination):
                return True
        return False


def _parse_icon_source(value: str | None) -> tuple[Path | None, int]:
    if not value:
        return None, 0
    expanded = os.path.expandvars(value.strip())
    match = re.fullmatch(r'"?(.*?)"?\s*(?:,\s*(-?\d+))?', expanded)
    if not match:
        return None, 0
    source = Path(match.group(1))
    if not source.is_file():
        return None, 0
    return source, int(match.group(2) or 0)


def _convert_image(source: Path, destination: Path) -> bool:
    temporary = destination.with_suffix(".tmp.png")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            if source.suffix.lower() == ".ico" and getattr(image, "ico", None):
                sizes = image.ico.sizes()
                if sizes:
                    image.size = max(sizes, key=lambda value: value[0] * value[1])
            converted = image.convert("RGBA")
            converted.thumbnail((256, 256), Image.Resampling.LANCZOS)
            converted.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, destination)
        return True
    except (OSError, ValueError):
        with suppress(OSError):
            temporary.unlink()
        return False


def _convert_image_bytes(data: bytes, destination: Path) -> bool:
    temporary = destination.with_suffix(".tmp.png")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(BytesIO(data)) as image:
            if image.format == "ICO" and getattr(image, "ico", None):
                sizes = image.ico.sizes()
                if sizes:
                    image.size = max(sizes, key=lambda value: value[0] * value[1])
            converted = image.convert("RGBA")
            converted.thumbnail((256, 256), Image.Resampling.LANCZOS)
            converted.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, destination)
        return True
    except (OSError, ValueError):
        with suppress(OSError):
            temporary.unlink()
        return False


def _download(url: str, *, accept: str, maximum_bytes: int) -> tuple[bytes, str, str]:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "PhoneRemote/1.1 (+favicon discovery)",
        },
    )
    with urlopen(request, timeout=_WEB_TIMEOUT_SECONDS) as response:  # noqa: S310
        final_url = response.geturl()
        if urlsplit(final_url).scheme.lower() not in {"http", "https"}:
            raise ValueError("website icon redirect used an unsupported scheme")
        data = response.read(maximum_bytes + 1)
        if len(data) > maximum_bytes:
            raise ValueError("website icon response is too large")
        return data, final_url, response.headers.get_content_type()


class _IconLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._icons: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "link":
            return
        values = {key.casefold(): value or "" for key, value in attrs}
        rel = {value.casefold() for value in values.get("rel", "").split()}
        href = values.get("href", "").strip()
        if "icon" not in rel and "apple-touch-icon" not in rel:
            return
        if not href:
            return
        sizes = [int(value) for value in re.findall(r"\d+", values.get("sizes", ""))]
        score = max(sizes, default=0) + (1000 if "apple-touch-icon" in rel else 0)
        self._icons.append((score, href))

    def icon_urls(self) -> list[str]:
        return [value for _, value in sorted(self._icons, reverse=True)]


def _extract_windows_resources(requests: list[dict[str, object]]) -> None:
    if not requests or os.name != "nt":
        return
    script = r"""
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class PhoneRemoteIconExtractor {
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern uint PrivateExtractIcons(
    string fileName, int iconIndex, int width, int height,
    IntPtr[] icons, uint[] iconIds, uint iconCount, uint flags);
  [DllImport("user32.dll")]
  [return: MarshalAs(UnmanagedType.Bool)]
  public static extern bool DestroyIcon(IntPtr icon);
}
'@
$requests = ConvertFrom-Json $env:PHONE_REMOTE_ICON_REQUESTS
$result = foreach ($request in $requests) {
  $ok = $false
  $handle = [IntPtr]::Zero
  $icon = $null
  $clone = $null
  $bitmap = $null
  try {
    $handles = New-Object IntPtr[] 1
    $ids = New-Object UInt32[] 1
    $count = [PhoneRemoteIconExtractor]::PrivateExtractIcons(
      $request.source, [int]$request.index, 256, 256, $handles, $ids, 1, 0)
    if ($count -gt 0 -and $handles[0] -ne [IntPtr]::Zero) {
      $handle = $handles[0]
      $icon = [System.Drawing.Icon]::FromHandle($handle)
      $clone = $icon.Clone()
    } else {
      $clone = [System.Drawing.Icon]::ExtractAssociatedIcon($request.source)
    }
    if ($clone) {
      $bitmap = $clone.ToBitmap()
      $bitmap.Save($request.destination, [System.Drawing.Imaging.ImageFormat]::Png)
      $ok = Test-Path -LiteralPath $request.destination -PathType Leaf
    }
  } catch {
    $ok = $false
  } finally {
    if ($bitmap) { $bitmap.Dispose() }
    if ($clone) { $clone.Dispose() }
    if ($icon) { $icon.Dispose() }
    if ($handle -ne [IntPtr]::Zero) {
      [void][PhoneRemoteIconExtractor]::DestroyIcon($handle)
    }
  }
  [pscustomobject]@{ destination = $request.destination; ok = $ok }
}
$result | ConvertTo-Json -Compress
"""
    try:
        run_powershell_json(
            script,
            environment={"PHONE_REMOTE_ICON_REQUESTS": json.dumps(requests)},
            timeout=max(30, len(requests) * 2),
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
