#!/bin/zsh
# 🌐 더블클릭용 — 위키를 로컬 웹서버로 띄우고 브라우저를 자동으로 엶
# 끄는 법: 이 터미널 창에서 Ctrl+C (또는 창 닫기)
cd "$(dirname "$0")"
echo "🌐 위키 서버 시작 중... 잠시 후 브라우저가 열립니다"
echo "   주소: http://localhost:8000  ·  종료: Ctrl+C"
( sleep 2 && open "http://localhost:8000" ) &
python3 -m mkdocs serve
