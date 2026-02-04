from __future__ import annotations

import os
import sys
import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import requests
from packaging import version as packaging_version

from app_info import (
    APP_NAME,
    REPO_NAME,
    REPO_OWNER,
    RELEASE_ASSET_NAME,
    __version__ as CURRENT_VERSION,
)

GITHUB_RELEASES_LATEST = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
REQUEST_TIMEOUT = 10
READ_TIMEOUT = 30

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


class AutoUpdateError(RuntimeError):
    """Wrap failures from the auto-update pipeline."""


@dataclass
class UpdateInfo:
    version: str
    asset_name: str
    download_url: str
    release_notes: str = ""
    size: Optional[int] = None

    @property
    def normalized_version(self) -> packaging_version.Version:
        return packaging_version.parse(self.version)


_session = requests.Session()


def _normalize_version(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.lstrip("vV").strip()


def _fetch_latest_release() -> dict:
    response = _session.get(
        GITHUB_RELEASES_LATEST,
        timeout=REQUEST_TIMEOUT,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": APP_NAME,
        },
    )
    response.raise_for_status()
    return response.json()


def _find_preferred_asset(assets: Iterable[dict]) -> Optional[dict]:
    # Prefer an exact match first, otherwise fall back to any .exe asset.
    preferred = None
    for asset in assets:
        name = asset.get("name", "")
        if not name:
            continue
        if RELEASE_ASSET_NAME and name == RELEASE_ASSET_NAME:
            return asset
        if name.lower().endswith(".exe") and preferred is None:
            preferred = asset
    return preferred


def check_for_update() -> Optional[UpdateInfo]:
    """Return update information if a newer release is available."""
    try:
        release = _fetch_latest_release()
    except requests.RequestException as exc:
        raise AutoUpdateError(f"Unable to contact GitHub: {exc}") from exc

    remote_version_raw = _normalize_version(release.get("tag_name"))
    if not remote_version_raw:
        raise AutoUpdateError("Latest release does not specify a version tag.")

    try:
        remote_version = packaging_version.parse(remote_version_raw)
        current_version = packaging_version.parse(_normalize_version(CURRENT_VERSION))
    except packaging_version.InvalidVersion as exc:
        raise AutoUpdateError(f"Invalid version format: {exc}") from exc

    if remote_version <= current_version:
        return None

    asset = _find_preferred_asset(release.get("assets", []))
    if asset is None:
        raise AutoUpdateError("Latest release does not provide a Windows executable asset.")

    return UpdateInfo(
        version=str(remote_version),
        asset_name=asset.get("name", ""),
        download_url=asset.get("browser_download_url", ""),
        release_notes=release.get("body", ""),
        size=asset.get("size"),
    )


def download_update(info: UpdateInfo, progress_callback=None) -> Path:
    """Download the release asset and return the temporary file path."""
    if not info.download_url:
        raise AutoUpdateError("The selected release asset does not expose a download URL.")

    try:
        with _session.get(
            info.download_url,
            timeout=READ_TIMEOUT,
            stream=True,
        ) as response:
            response.raise_for_status()
            suffix = Path(info.asset_name).suffix or ".exe"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                bytes_downloaded = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    bytes_downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_downloaded, info.size)
            return Path(handle.name)
    except requests.RequestException as exc:
        raise AutoUpdateError(f"Unable to download update: {exc}") from exc


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _current_executable() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve()
    return Path(__file__).resolve()


def schedule_install(downloaded_path: Path) -> Path:
    """Create and run a helper script that swaps the executable after exit."""
    if not downloaded_path.exists():
        raise AutoUpdateError("Downloaded update file no longer exists.")

    if not _is_frozen():
        raise AutoUpdateError("Automatic install is only available for packaged builds.")

    current_exe = _current_executable()
    update_script = current_exe.with_name(f"{current_exe.stem}_update.bat")

    script_contents = f"""@echo off
setlocal
set SOURCE="{downloaded_path}"
set TARGET="{current_exe}"
:waitloop
move /Y %SOURCE% %TARGET% >nul
if %errorlevel% neq 0 (
    timeout /t 1 >nul
    goto waitloop
)
start "" "%TARGET%"
del "%~f0"
"""
    update_script.write_text(script_contents, encoding="utf-8")

    creationflags = 0
    if os.name == "nt":
        creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        ["cmd", "/c", str(update_script)],
        creationflags=creationflags,
        close_fds=True,
    )

    return update_script


def run_auto_update(progress_callback=None) -> Optional[UpdateInfo]:
    """Check, download, and schedule an update. Returns the update info if scheduled."""
    if not _is_frozen():
        return None

    info = check_for_update()
    if info is None:
        return None

    downloaded_path = download_update(info, progress_callback=progress_callback)
    schedule_install(downloaded_path)
    return info
