"""Safe, release-based automatic updates for the packaged Windows game."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import urllib.request


REPOSITORY = "tzt302/game_racing"
LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
)
MAX_UPDATE_SIZE = 250 * 1024 * 1024
UPDATE_HELPER_FLAG = "--apply-update"


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
        """Run the validated staged EXE as a tightly scoped update helper."""
        if not self.enabled or self.staged_path is None:
            return False
        if not self.staged_path.is_file():
            return False

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [
                str(self.staged_path),
                UPDATE_HELPER_FLAG,
                str(self.executable),
                str(os.getpid()),
            ],
            close_fds=True,
            creationflags=creation_flags,
        )
        return True


def run_update_helper(arguments=None):
    """Replace the old executable without invoking a shell or PowerShell."""
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if not arguments or arguments[0] != UPDATE_HELPER_FLAG:
        return None
    if (
        os.name != "nt"
        or not getattr(sys, "frozen", False)
        or len(arguments) != 3
    ):
        return 2

    source = Path(sys.executable).resolve()
    target = Path(arguments[1]).resolve()
    expected_source = target.with_suffix(".update.exe")
    try:
        parent_pid = int(arguments[2])
    except ValueError:
        return 2
    if (
        parent_pid <= 0
        or source != expected_source
        or target.suffix.lower() != ".exe"
        or source.parent != target.parent
    ):
        return 2

    _wait_for_process(parent_pid, 30_000)
    for _ in range(30):
        try:
            shutil.copyfile(source, target)
            break
        except (OSError, PermissionError):
            time.sleep(0.25)
    else:
        _write_update_error(target, "Unable to replace the previous executable.")
        return 1

    try:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [str(target)],
            close_fds=True,
            creationflags=creation_flags,
        )
    except OSError as error:
        _write_update_error(target, f"Unable to restart the game: {error}")
        return 1
    return 0


def _wait_for_process(pid, timeout_ms):
    import ctypes

    synchronize = 0x00100000
    handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
    if handle:
        ctypes.windll.kernel32.WaitForSingleObject(handle, timeout_ms)
        ctypes.windll.kernel32.CloseHandle(handle)


def _write_update_error(target, message):
    try:
        target.with_name("raceline_update_error.log").write_text(
            message,
            encoding="utf-8",
        )
    except OSError:
        pass
