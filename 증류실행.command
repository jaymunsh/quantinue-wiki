#!/bin/zsh
# 🌀 더블클릭용 — Finder에서 이 파일을 더블클릭하면 터미널이 열리며 증류가 실행됨
cd "$(dirname "$0")"
./tools/distill.sh
echo ""
read "?창을 닫으려면 Enter를 누르세요..."
