#!/usr/bin/env bash

set -u

export DISPLAY="${DISPLAY:-:99}"

STATE_DIR="/tmp/actionboxvm"
PID_FILE="$STATE_DIR/screenshot-worker.pid"
LOG_FILE="$STATE_DIR/screenshot-worker.log"

mkdir -p "$STATE_DIR"

# Do not start duplicate workers.
if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"

    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "ActionBoxVM screenshot worker is already running."
        exit 0
    fi

    rm -f "$PID_FILE"
fi

# Start the actual worker independently from this launcher.
#
# The worker:
#   - uses the same DISPLAY as ActionBoxVM
#   - refreshes 0.png every 300 seconds
#   - waits for X to become available
#   - does not depend on Fluxbox
#   - does not depend on Xterm
#   - does not depend on VNC
#   - continues until the Actions runner/job ends

nohup setsid python3 - <<'PY' \
    </dev/null \
    >>"/tmp/actionboxvm/screenshot-worker.log" 2>&1 &

import os
import subprocess
import time
from pathlib import Path

DISPLAY = os.environ.get("DISPLAY", ":99")

ROOT = Path.cwd()
OUTPUT = ROOT / "0.png"
TEMPORARY = ROOT / ".actionboxvm-0.png"

STATE_DIR = Path("/tmp/actionboxvm")
PID_FILE = STATE_DIR / "screenshot-worker.pid"

INTERVAL = 300
RETRY_INTERVAL = 10


def write_pid():
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


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

    if not TEMPORARY.exists() or TEMPORARY.stat().st_size == 0:
        raise RuntimeError("ImageMagick produced an empty screenshot.")

    TEMPORARY.replace(OUTPUT)


def git_commit_and_push():
    subprocess.run(
        ["git", "add", "0.png"],
        check=True,
    )

    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        check=False,
    )

    if status.returncode == 0:
        return

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

    for attempt in range(5):
        push = subprocess.run(
            ["git", "push", "origin", branch],
            check=False,
        )

        if push.returncode == 0:
            return

        print(
            "Screenshot push failed; synchronizing with remote.",
            flush=True,
        )

        pull = subprocess.run(
            [
                "git",
                "pull",
                "--rebase",
                "origin",
                branch,
            ],
            check=False,
        )

        if pull.returncode == 0:
            continue

        print(
            "Remote synchronization failed.",
            flush=True,
        )

        time.sleep(2)

    raise RuntimeError("Unable to publish screenshot after multiple attempts.")


write_pid()

print(
    f"ActionBoxVM screenshot worker started on DISPLAY={DISPLAY}.",
    flush=True,
)

while True:
    try:
        if not display_available():
            print(
                "X display is currently unavailable. Waiting.",
                flush=True,
            )
            time.sleep(RETRY_INTERVAL)
            continue

        capture()

        print(
            f"Screenshot captured: {OUTPUT}",
            flush=True,
        )

        git_commit_and_push()

        print(
            "Screenshot published successfully.",
            flush=True,
        )

        time.sleep(INTERVAL)

    except Exception as exc:
        print(
            f"Screenshot service error: {exc}",
            flush=True,
        )

        time.sleep(RETRY_INTERVAL)
PY

WORKER_PID=$!

echo "$WORKER_PID" > "$PID_FILE"

echo "ActionBoxVM screenshot worker started."
echo "PID: $WORKER_PID"
echo "DISPLAY: $DISPLAY"