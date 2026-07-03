#!/bin/zsh
# DocStill 증류 실행 스크립트
# 사용: mkwiki 폴더에서  ./tools/distill.sh   (또는 증류실행.command 더블클릭)
set -e
cd "$(dirname "$0")/.."   # 항상 mkwiki 루트에서 실행

echo "🌀 DocStill 증류 시작 — $(date '+%Y-%m-%d %H:%M')"
echo "   (클로드 코드 헤드리스 모드로 실행됩니다. 수 분 걸릴 수 있어요)"
echo ""

claude -p "tools/distill_prompt.md 를 읽고, 그 지시서대로 증류를 지금 수행해줘.
- raw/ 를 스캔해 지난 회차 이후 새 파일만 처리
- STATUS.md 와 질문.md 를 지시서 형식대로 갱신
- 마지막에 보고 형식(새 주장 N · 충돌 N · 소멸 N · 추천 안건)으로 요약 출력
- facts/ 는 절대 직접 수정 금지" \
  --permission-mode acceptEdits

echo ""
echo "📦 git 기록 중..."
git add -A
git commit -m "증류: $(date '+%Y-%m-%d %H:%M')" >/dev/null 2>&1 && echo "   커밋 완료" || echo "   변경 없음 (커밋 생략)"

echo ""
echo "✅ 끝. STATUS.md 와 질문.md 를 확인하세요."
