#!/usr/bin/env python3

import os
import subprocess
import sys
import time
from pathlib import Path


# ==============================================================
# CONFIGURATION
# ==============================================================

DISPLAY = os.environ.get("DISPLAY", ":99")

ROOT = Path.cwd()

OUTPUT = ROOT / "0.png"
TEMPORARY = ROOT / ".actionboxvm-0.png"

STATE_DIR = Path("/tmp/actionboxvm")
PID_FILE = STATE_DIR / "screenshot-worker.pid"

# Five minutes.
INTERVAL = 300

# Retry the X display every ten seconds if it is temporarily
# unavailable.
RETRY_INTERVAL = 10


# ==============================================================
# HELPERS
# ==============================================================

def log(message: str) -> None:
    print(
        message,
        flush=True,
    )


def write_pid() -> None:
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PID_FILE.write_text(
        str(os.getpid()),
        encoding="utf-8",
    )


def display_available() -> bool:
    result = subprocess.run(
        [
            "xdpyinfo",
            "-display",
            DISPLAY,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def capture() -> None:
    subprocess.run(
        [
            "import",
            "-display",
            DISPLAY,
            "-window",
            "root",
            "-quality",
            "92",
            str(TEMPORARY),
        ],
        check=True,
    )

    if not TEMPORARY.exists():
        raise RuntimeError(
            "ImageMagick did not create the screenshot."
        )

    if TEMPORARY.stat().st_size == 0:
        raise RuntimeError(
            "ImageMagick created an empty screenshot."
        )

    TEMPORARY.replace(OUTPUT)


def git_configure() -> None:
    subprocess.run(
        [
            "git",
            "config",
            "user.name",
            "github-actions[bot]",
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        ],
        check=True,
    )


def publish() -> None:
    subprocess.run(
        [
            "git",
            "add",
            "0.png",
        ],
        check=True,
    )

    unchanged = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--quiet",
        ],
        check=False,
    )

    if unchanged.returncode == 0:
        log("0.png is unchanged.")
        return

    git_configure()

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "chore: refresh ActionBoxVM screenshot",
        ],
        check=True,
    )

    branch = subprocess.check_output(
        [
            "git",
            "branch",
            "--show-current",
        ],
        text=True,
    ).strip()

    if not branch:
        raise RuntimeError(
            "Could not determine the current Git branch."
        )

    # ----------------------------------------------------------
    # Retry pushes in case the repository changed between
    # screenshot updates.
    # ----------------------------------------------------------

    for attempt in range(1, 6):

        result = subprocess.run(
            [
                "git",
                "push",
                "origin",
                branch,
            ],
            check=False,
        )

        if result.returncode == 0:
            log("0.png published successfully.")
            return

        log(
            f"Git push failed "
            f"(attempt {attempt}/5)."
        )

        # Do not allow a failed rebase to destroy the worker.
        subprocess.run(
            [
                "git",
                "pull",
                "--rebase",
                "origin",
                branch,
            ],
            check=False,
        )

        time.sleep(2)

    raise RuntimeError(
        "Unable to publish 0.png after multiple attempts."
    )


# ==============================================================
# START
# ==============================================================

write_pid()

log(
    "ActionBoxVM screenshot worker started."
)

log(
    f"DISPLAY={DISPLAY}"
)

log(
    "Screenshot interval: 300 seconds."
)


# ==============================================================
# MAIN LOOP
# ==============================================================

while True:

    try:

        # ------------------------------------------------------
        # Wait for X.
        #
        # Fluxbox, Xterm, VNC and noVNC are not required for the
        # worker itself. It only requires the X display.
        # ------------------------------------------------------

        if not display_available():

            log(
                "X display is unavailable. "
                "Waiting for DISPLAY to become available."
            )

            time.sleep(RETRY_INTERVAL)

            continue

        # ------------------------------------------------------
        # Capture the SAME desktop exposed through VNC.
        # ------------------------------------------------------

        capture()

        log(
            "Captured 0.png."
        )

        # ------------------------------------------------------
        # Publish the screenshot.
        # ------------------------------------------------------

        publish()

        # ------------------------------------------------------
        # Wait five minutes before the next capture.
        # ------------------------------------------------------

        time.sleep(INTERVAL)

    except KeyboardInterrupt:

        log(
            "Screenshot worker received an interrupt."
        )

        break

    except Exception as exc:

        log(
            f"Screenshot service error: {exc}"
        )

        # Keep the worker alive after an individual failure.
        time.sleep(RETRY_INTERVAL)


# ==============================================================
# CLEANUP
# ==============================================================

try:
    PID_FILE.unlink(
        missing_ok=True,
    )
except Exception:
    pass

sys.exit(0)