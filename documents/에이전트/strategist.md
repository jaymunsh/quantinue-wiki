# 🧠 Strategist 에이전트 (⑦ 전략 종합)

!!! note "⚪ 설계 예정 · 담당 이은미"
    코드는 아직 스켈레톤(`agents/fundmanager/__init__.py`). 계약(스키마)은 확정 수준 — 아래는 계약 기준 설명. 코드 나오면 이 페이지를 채운다.

## 역할

5개 신호(기술·매크로·공시·뉴스 + 회고 메모리)와 실시간 시세를 종합해 **매수/보류**를 근거와 함께 판단. 파이프라인의 결정 시작점.

- **입력:** `tb_technical`·`tb_macro`·`tb_disclosure`·`tb_news` + 실시간 시세(API 배치) + `tb_review`(최근 교훈)
- **출력:** `tb_strategist_signals` (side·conviction·bull_case·key_risk·evidence·sizing_hint…)
- **판단 방식:** 코드 게이트 샌드위치 — 앞문(hard_block) → GPT 판단 → 뒷문(min_conviction). [파이프라인](../facts/파이프라인.md) 참조.

## 계약·결정

- 스키마: [데이터 계약](../facts/데이터계약.md) `tb_strategist_signals`
- 관련: [회의 안건](../질문.md) B8(리뷰어 소비)·B11·실시간 시세 조율
- 회의: [4차 회의록](../회의록/2026-07-06.md) — 1차 매도 미사용(매수/보류만)·페르소나 2차

> 코드가 생기면: `agents/fundmanager/` 읽어 역할·흐름·코드구조·핵심규칙으로 확장.
