#!/bin/zsh
# DocStill 증류 실행 (얇은 래퍼) — 실제 로직은 tools/distill.py
# 사용: ./tools/distill.sh [--backend claude|codex|ollama] [--dry-run]
cd "$(dirname "$0")/.."
python3 tools/distill.py "$@"
