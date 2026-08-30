#!/usr/bin/env python3

import json
import os
import subprocess
import time
from pathlib import Path


DISPLAY = os.environ.get("DISPLAY", ":99")

ROOT = Path.cwd()

OUTPUT = ROOT / "0.png"
TEMPORARY = ROOT / ".actionboxvm-0.png"
STATUS = ROOT / "status.json"

STATE_DIR = Path("/tmp/actionboxvm")
PID_FILE = STATE_DIR / "screenshot-worker.pid"

INTERVAL = 300
RETRY_INTERVAL = 10


def log(message):
    print(message, flush=True)


def write_pid():
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PID_FILE.write_text(
        str(os.getpid()),
        encoding="utf-8",
    )


def display_available():
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


def capture():
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
            "Screenshot is empty."
        )

    TEMPORARY.replace(OUTPUT)


def create_status():
    repository = os.environ.get(
        "GITHUB_REPOSITORY",
        "unknown",
    )

    branch = os.environ.get(
        "GITHUB_REF_NAME",
        "unknown",
    )

    workflow = os.environ.get(
        "GITHUB_WORKFLOW",
        "ActionBoxVM",
    )

    run_id = os.environ.get(
        "GITHUB_RUN_ID",
        "unknown",
    )

    tunnel = os.environ.get(
        "TUNNEL_NOVNC",
        "",
    )

    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S UTC",
        time.gmtime(),
    )

    data = {
        "project": "ActionBoxVM",
        "status": "online",

        "environment": {
            "os": "Ubuntu",
            "desktop": "Fluxbox",
            "display": "Xvfb :99",
            "resolution": "1280x720",
            "terminal": "Xterm",
        },

        "tools": [
            "Git",
            "Python 3",
            "nano",
            "Vim",
            "curl",
            "wget",
            "jq",
            "tree",
            "htop",
            "btop",
            "zip",
            "unzip",
        ],

        "services": {
            "vnc": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 5900,
                "public": False,
            },

            "noVNC": {
                "enabled": bool(tunnel),
                "url": tunnel,
            },

            "cloudflare": {
                "enabled": bool(tunnel),
                "type": "Quick Tunnel",
            },
        },

        "github": {
            "repository": repository,
            "branch": branch,
            "workflow": workflow,
            "run_id": run_id,
            "run_url": (
                f"https://github.com/"
                f"{repository}/actions/runs/{run_id}"
            ),
        },

        "files": {
            "screenshot": {
                "path": "0.png",
                "raw_url": (
                    f"https://raw.githubusercontent.com/"
                    f"{repository}/{branch}/0.png"
                ),
                "refresh_seconds": INTERVAL,
            },

            "status": {
                "path": "status.json",
                "refresh_seconds": INTERVAL,
            },

            "desktop_entry": {
                "path": "actionbox.desktop",
            },
        },

        "lifetime": {
            "vm_refresh_hours": 12,
            "screenshot_refresh_minutes": 5,
        },

        "updated": timestamp,
    }

    STATUS.write_text(
        json.dumps(
            data,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def configure_git():
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


def publish():
    configure_git()

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
            "Could not determine Git branch."
        )

    for attempt in range(1, 6):

        log(
            f"Publishing ActionBoxVM state "
            f"(attempt {attempt}/5)."
        )

        subprocess.run(
            [
                "git",
                "fetch",
                "origin",
                branch,
            ],
            check=True,
        )

        subprocess.run(
            [
                "git",
                "rebase",
                f"origin/{branch}",
            ],
            check=True,
        )

        subprocess.run(
            [
                "git",
                "add",
                "0.png",
                "status.json",
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
            log(
                "0.png and status.json are unchanged."
            )
            return

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "chore: refresh ActionBoxVM status",
            ],
            check=True,
        )

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
            log(
                "0.png and status.json published."
            )
            return

        log(
            f"Git push failed "
            f"(attempt {attempt}/5)."
        )

        time.sleep(2)

    raise RuntimeError(
        "Unable to publish ActionBoxVM state "
        "after multiple attempts."
    )


write_pid()

log("ActionBoxVM screenshot worker started.")
log(f"DISPLAY={DISPLAY}")
log("Refresh interval: 300 seconds.")


while True:

    try:

        if not display_available():
            log(
                "X display unavailable. Retrying."
            )

            time.sleep(RETRY_INTERVAL)
            continue

        capture()

        log("Captured 0.png.")

        create_status()

        log("Updated status.json.")

        publish()

        time.sleep(INTERVAL)

    except KeyboardInterrupt:
        break

    except Exception as exc:
        log(
            f"Screenshot service error: {exc}"
        )

        time.sleep(RETRY_INTERVAL)


try:
    PID_FILE.unlink(
        missing_ok=True,
    )
except Exception:
    pass