"""Helpers to query and install packages through winget."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INTERNAL_WINGET_CALL_ENV = "WINGIT_GUI_INTERNAL_WINGET_CALL"


class WingetError(RuntimeError):
    """Raised when winget commands fail."""


@dataclass(frozen=True)
class WingetPackage:
    """A package returned from `winget search`."""

    name: str
    package_id: str
    version: str
    source: str


def _find_winget_candidates() -> list[Path]:
    """Return possible winget executables from PATH/where."""
    candidates: list[Path] = []

    for command_name in ("winget.exe", "winget"):
        resolved = shutil.which(command_name)
        if resolved:
            candidates.append(Path(resolved).resolve())

    if sys.platform.startswith("win"):
        where_result = subprocess.run(
            ["where", "winget.exe"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if where_result.returncode == 0:
            for line in where_result.stdout.splitlines():
                candidate = line.strip()
                if candidate:
                    candidates.append(Path(candidate).resolve())

    # De-duplicate while preserving order.
    unique_candidates: list[Path] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    return unique_candidates


def _resolve_real_winget() -> str:
    """Resolve the system winget executable and avoid this package's launcher."""
    candidates = _find_winget_candidates()
    if not candidates:
        raise WingetError(
            "winget is not available in PATH. Install App Installer from Microsoft Store first."
        )

    current_launcher = Path(sys.argv[0]).resolve() if sys.argv else None

    filtered = [
        path
        for path in candidates
        if current_launcher is None or path != current_launcher
    ]

    if not filtered:
        raise WingetError(
            "Could not locate the system winget executable. This command appears to resolve "
            "to the GUI launcher itself. Make sure Microsoft App Installer is installed and "
            "available in PATH."
        )

    preferred = next((path for path in filtered if "WindowsApps" in str(path)), filtered[0])
    return str(preferred)


def ensure_winget_available() -> None:
    """Fail fast if the real system winget is not available."""
    _resolve_real_winget()


def _run(command: list[str]) -> str:
    run_env = dict(os.environ)
    run_env[INTERNAL_WINGET_CALL_ENV] = "1"

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=run_env,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise WingetError(stderr)
    return result.stdout



def _try_run(command: list[str]) -> tuple[bool, str]:
    """Run a command and return (ok, output_or_error)."""
    try:
        return True, _run(command)
    except WingetError as error:
        return False, str(error)

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
    winget_command = _resolve_real_winget()

    base = [
        winget_command,
        "search",
        "--source",
        "winget",
        "--accept-source-agreements",
    ]

    # Some winget versions require an explicit query argument for `search`.
    attempts = [
        base,
        [*base, "--query", "*"],
        [*base, "-q", "*"],
    ]

    last_error = "Unknown error"
    output = ""
    for command in attempts:
        ok, result = _try_run(command)
        if ok:
            output = result
            break
        last_error = result
    else:
        raise WingetError(last_error)

    packages = parse_search_output(output)
    if limit is not None:
        return packages[:limit]
    return packages


def install_package(package_id: str) -> str:
    """Install a package by ID and return command output."""
    winget_command = _resolve_real_winget()
    return _run(
        [
            winget_command,
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
