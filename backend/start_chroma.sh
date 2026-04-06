#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROMA_PORT="${CHROMA_PORT:-8001}"

exec chroma run --path "$SCRIPT_DIR/chroma_db" --host 0.0.0.0 --port "$CHROMA_PORT"
