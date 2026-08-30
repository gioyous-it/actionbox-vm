#!/usr/bin/env bash

set -u

while true; do
    clear

    printf '\033[1;36m'
    echo "========================================"
    echo "              ActionBoxVM"
    echo "========================================"
    printf '\033[0m'

    echo
    echo "Environment"
    echo "  OS          Ubuntu"
    echo "  Desktop     Fluxbox"
    echo "  Display     Xvfb :99"
    echo "  Resolution  1280x720"

    echo
    echo "Tools"
    echo "  Git  Python 3  nano  Vim"
    echo "  curl  wget  jq  tree"
    echo "  htop  btop  zip  unzip"

    echo
    echo "Services"
    echo "  noVNC       Online"
    echo "  Cloudflare  Online"

    echo
    printf '\033[1;36m'
    echo "========================================"
    echo "              LIVE STATUS"
    echo "========================================"
    printf '\033[0m'

    echo
    printf "Time          "
    date "+%Y-%m-%d %H:%M:%S %Z" | lolcat

    printf "Repository    "
    echo "${GITHUB_REPOSITORY:-unknown}"

    printf "Workflow      "
    echo "${GITHUB_WORKFLOW:-ActionBoxVM}"

    printf "Run ID        "
    echo "${GITHUB_RUN_ID:-unknown}"

    echo
    echo "Last commit"
    git log -1 \
        --pretty=format:"  %h  %s%n  %ad" \
        --date=local \
        2>/dev/null \
        || echo "  unavailable"

    echo
    printf '\033[1;32m'
    echo "ActionBoxVM ONLINE"
    printf '\033[0m'

    sleep 30
done