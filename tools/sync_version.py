from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


@dataclass(frozen=True)
class VersionTarget:
    path: str
    pattern: str
    replacement: str
    expected_matches: int = 1


TARGETS = (
    VersionTarget(
        "server/pyproject.toml",
        r'(?m)^(version = ")[^"]+("\s*)$',
        r"\g<1>{version}\g<2>",
    ),
    VersionTarget(
        "server/phone_remote/__init__.py",
        r'(?m)^(__version__ = ")[^"]+("\s*)$',
        r"\g<1>{version}\g<2>",
    ),
    VersionTarget(
        "mobile/pubspec.yaml",
        r"(?m)^(version:\s*)[0-9]+\.[0-9]+\.[0-9]+(\+[0-9]+\s*)$",
        r"\g<1>{version}\g<2>",
    ),
    VersionTarget(
        "packaging/windows/installer.iss",
        r'(?m)^(#define MyAppVersion ")[^"]+("\s*)$',
        r"\g<1>{version}\g<2>",
    ),
    VersionTarget(
        "mobile/lib/ui/remote_shell.dart",
        r"Phone Remote [0-9]+\.[0-9]+\.[0-9]+",
        "Phone Remote {version}",
    ),
    VersionTarget(
        "README.md",
        r"v[0-9]+\.[0-9]+\.[0-9]+",
        "v{version}",
        expected_matches=2,
    ),
    VersionTarget(
        "README_EN.md",
        r"v[0-9]+\.[0-9]+\.[0-9]+",
        "v{version}",
        expected_matches=2,
    ),
)


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def _write_text(path: Path, value: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or update release version references."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Update version references instead of only checking them.",
    )
    args = parser.parse_args()

    version = _read_text(ROOT / "VERSION").strip()
    if VERSION_PATTERN.fullmatch(version) is None:
        parser.error("VERSION must contain exactly MAJOR.MINOR.PATCH")

    stale: list[str] = []
    invalid: list[str] = []
    for target in TARGETS:
        path = ROOT / target.path
        contents = _read_text(path)
        updated, count = re.subn(
            target.pattern,
            target.replacement.format(version=version),
            contents,
        )
        if count != target.expected_matches:
            invalid.append(
                f"{target.path}: expected {target.expected_matches} version references, found {count}"
            )
            continue
        if updated == contents:
            continue
        stale.append(target.path)
        if args.write:
            _write_text(path, updated)

    if invalid:
        print("\n".join(invalid))
        return 1
    if stale and not args.write:
        print("Version references do not match VERSION:")
        print("\n".join(f"- {path}" for path in stale))
        print("Run: python tools/sync_version.py --write")
        return 1
    if stale:
        print(f"Updated {len(stale)} files to {version}.")
    else:
        print(f"All version references match {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
