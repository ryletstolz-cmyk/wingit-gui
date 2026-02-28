"""Helpers to query and install packages through winget."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable


class WingetError(RuntimeError):
    """Raised when winget commands fail."""


@dataclass(frozen=True)
class WingetPackage:
    """A package returned from `winget search`."""

    name: str
    package_id: str
    version: str
    source: str


def ensure_winget_available() -> None:
    """Fail fast if winget is not available in PATH."""
    if shutil.which("winget") is None:
        raise WingetError(
            "winget is not available in PATH. Install App Installer from Microsoft Store first."
        )


def _run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise WingetError(stderr)
    return result.stdout


def _split_row(line: str) -> list[str]:
    # winget prints table columns separated by at least 2 spaces.
    return [segment.strip() for segment in line.strip().split("  ") if segment.strip()]


def parse_search_output(raw_output: str) -> list[WingetPackage]:
    """Parse the text output from `winget search` into package records."""
    lines = [line.rstrip("\n") for line in raw_output.splitlines()]
    package_lines: list[str] = []

    separator_found = False
    for line in lines:
        if not separator_found:
            if line.strip() and set(line.strip()) == {"-"}:
                separator_found = True
            continue
        if not line.strip():
            continue
        if line.lower().startswith("no package found"):
            break
        package_lines.append(line)

    packages: list[WingetPackage] = []
    for line in package_lines:
        cols = _split_row(line)
        if len(cols) < 2:
            continue

        name = cols[0]
        package_id = cols[1]
        version = cols[2] if len(cols) > 2 else "-"
        source = cols[-1] if len(cols) > 3 else "winget"
        packages.append(
            WingetPackage(
                name=name,
                package_id=package_id,
                version=version,
                source=source,
            )
        )

    return packages


def fetch_all_packages(limit: int | None = None) -> list[WingetPackage]:
    """Query winget packages from the default source."""
    ensure_winget_available()
    output = _run(
        [
            "winget",
            "search",
            "--source",
            "winget",
            "--accept-source-agreements",
        ]
    )
    packages = parse_search_output(output)
    if limit is not None:
        return packages[:limit]
    return packages


def install_package(package_id: str) -> str:
    """Install a package by ID and return command output."""
    ensure_winget_available()
    return _run(
        [
            "winget",
            "install",
            "--id",
            package_id,
            "--exact",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
    )


def filter_packages(packages: Iterable[WingetPackage], text: str) -> list[WingetPackage]:
    """Simple case-insensitive filter over name and package id."""
    needle = text.strip().lower()
    if not needle:
        return list(packages)

    return [
        package
        for package in packages
        if needle in package.name.lower() or needle in package.package_id.lower()
    ]
