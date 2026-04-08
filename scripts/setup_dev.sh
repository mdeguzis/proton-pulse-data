#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

git submodule update --init --recursive

if ! command -v shellcheck >/dev/null 2>&1; then
  echo "[setup] shellcheck not found; installing via apt"
  sudo apt install -y shellcheck
fi

UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync --group dev
