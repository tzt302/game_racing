"""Safe, release-based automatic updates for the packaged Windows game."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request


REPOSITORY = "tzt302/game_racing"
LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
)
MAX_UPDATE_SIZE = 250 * 1024 * 1024


def version_tuple(value):
    """Return a comparable numeric release tuple, or None for invalid tags."""
    value = value.strip().lower()
    if value.startswith("v"):
        value = value[1:]
    parts = value.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return None
    numbers = tuple(int(part) for part in parts)
    return numbers + (0,) * max(0, 3 - len(numbers))


def select_update(release, current_version):
    """Validate a GitHub release and return its Windows asset metadata."""
    if release.get("draft") or release.get("prerelease"):
        return None
    latest = version_tuple(release.get("tag_name", ""))
    current = version_tuple(current_version)
    if latest is None or current is None or latest <= current:
        return None

    version_text = ".".join(str(part) for part in latest)
    expected_name = f"RacingLinePro-v{version_text}.exe"
    for asset in release.get("assets", []):
        digest = asset.get("digest") or ""
        url = asset.get("browser_download_url") or ""
        size = asset.get("size", 0)
        if (
            asset.get("name") == expected_name
            and isinstance(size, int)
            and 0 < size <= MAX_UPDATE_SIZE
            and digest.startswith("sha256:")
            and url.startswith(
                f"https://github.com/{REPOSITORY}/releases/download/"
            )
        ):
            return {
                "version": version_text,
                "url": url,
                "size": size,
                "sha256": digest.removeprefix("sha256:").lower(),
            }
    return None


class AutoUpdater:
    """Check, download and stage a newer signed-by-digest release asset."""

    def __init__(self, current_version, executable=None, enabled=None):
        self.current_version = current_version
        self.executable = Path(executable or sys.executable).resolve()
        if enabled is None:
            enabled = (
                os.name == "nt"
                and bool(getattr(sys, "frozen", False))
                and self.executable.suffix.lower() == ".exe"
            )
        self.enabled = enabled
        self.status_text = ""
        self.ready_version = None
        self.staged_path = None
        self._thread = None

    def start(self):
        if not self.enabled or self._thread is not None:
            return
        self.status_text = "AUTO UPDATE: CHECKING..."
        self._thread = threading.Thread(
            target=self._check_and_download,
            name="release-updater",
            daemon=True,
        )
        self._thread.start()

    def _check_and_download(self):
        partial = None
        try:
            request = urllib.request.Request(
                LATEST_RELEASE_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"RacingLinePro/{self.current_version}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                release = json.load(response)
            update = select_update(release, self.current_version)
            if update is None:
                self.status_text = (
                    f"AUTO UPDATE: v{self.current_version} IS CURRENT"
                )
                return

            self.status_text = (
                f"AUTO UPDATE: DOWNLOADING v{update['version']}..."
            )
            staged = self.executable.with_suffix(".update.exe")
            partial = staged.with_suffix(".part")
            digest = hashlib.sha256()
            received = 0
            download_request = urllib.request.Request(
                update["url"],
                headers={"User-Agent": f"RacingLinePro/{self.current_version}"},
            )
            with (
                urllib.request.urlopen(download_request, timeout=20) as source,
                partial.open("wb") as destination,
            ):
                while True:
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    received += len(block)
                    if received > update["size"]:
                        raise ValueError("update exceeds declared asset size")
                    digest.update(block)
                    destination.write(block)
            if received != update["size"]:
                raise ValueError("downloaded update has the wrong size")
            if digest.hexdigest().lower() != update["sha256"]:
                raise ValueError("downloaded update failed SHA-256 validation")

            os.replace(partial, staged)
            self.staged_path = staged
            self.ready_version = update["version"]
            self.status_text = (
                f"UPDATE v{update['version']} READY - EXIT TO INSTALL"
            )
        except Exception:
            if partial is not None:
                partial.unlink(missing_ok=True)
            self.status_text = "AUTO UPDATE: CHECK FAILED - RETRY NEXT START"

    def apply_on_exit(self):
        """Launch a hidden helper that replaces this EXE after it exits."""
        if not self.enabled or self.staged_path is None:
            return False
        if not self.staged_path.is_file():
            return False

        source = _powershell_literal(str(self.staged_path))
        target = _powershell_literal(str(self.executable))
        command = (
            f"$pidToWait={os.getpid()};"
            "$process=Get-Process -Id $pidToWait -ErrorAction SilentlyContinue;"
            "if($process){Wait-Process -Id $pidToWait -Timeout 30 "
            "-ErrorAction SilentlyContinue};"
            "for($attempt=0;$attempt -lt 20;$attempt++){"
            "try{"
            f"Copy-Item -LiteralPath '{source}' -Destination '{target}' -Force;"
            f"Remove-Item -LiteralPath '{source}' -Force;"
            f"Start-Process -FilePath '{target}';"
            "exit 0"
            "}catch{Start-Sleep -Milliseconds 500}"
            "};exit 1"
        )
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                command,
            ],
            close_fds=True,
            creationflags=creation_flags,
        )
        return True


def _powershell_literal(value):
    return value.replace("'", "''")
