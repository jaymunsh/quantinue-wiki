#!/usr/bin/env python3
"""Generate the human-readable schema dictionary from the local canonical SQL copy."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "final/reference/schema.sql"
OUTPUT = ROOT / "documents/데이터사전.md"

TABLES = {
    "tb_universe": ("시장", "거래 대상 유니버스 스냅샷", "universe", "daily_bars·screening"),
    "tb_daily_pick": ("선별", "거래일별 분석 대상과 순위", "screening", "insider_scoring·analysis"),
    "tb_technical": ("선별", "MVP 1차 호환 기술지표 스냅샷", "구 파이프라인", "호환 조회"),
    "tb_macro": ("시장", "시장 국면과 위험 점수", "macro", "analysis·게이트"),
    "tb_disclosure": ("증거", "분석 대상 공시의 채점 결과", "공시 분석", "analysis"),
    "tb_disclosure_signal": ("증거", "슬롯·종목별 공시 집계 신호", "insider_scoring·공시 분석", "analysis"),
    "tb_news": ("증거", "분석 대상 뉴스의 채점 결과", "뉴스 분석", "analysis"),
    "tb_news_signal": ("증거", "슬롯·종목별 뉴스 집계 신호", "뉴스 분석", "analysis"),
    "tb_strategist_signals": ("판단", "성향별 매수·보유·매도 판단과 재현 메타데이터", "analysis:*", "Critic·exits·allocation·회고"),
    "tb_critic_verdict": ("판단", "전략가 판단에 대한 승인·기각·보류 평결", "Critic", "exits·allocation·관제"),
    "tb_user": ("사용자", "로그인 사용자와 권한", "관리자", "인증·계좌 화면"),
    "tb_account": ("집행", "사용자별 모의 계좌·현금·성향", "관리자·배분", "allocation·관제"),
    "tb_order": ("집행", "브래킷 매수와 특정 매수를 닫는 청산 주문", "allocation·exits", "MockBroker·체결·회고"),
    "tb_fill": ("집행", "모의 주문의 체결 사실", "MockBroker", "포지션·손익·관제"),
    "tb_account_equity_daily": ("집행", "일일 손실 한도의 기준이 되는 시작 평가액", "allocation", "위험 한도"),
    "tb_review_price_snapshots": ("회고", "판단 후 T+1~T+5 가격 관측", "Reviewer", "tb_review"),
    "tb_review": ("회고", "판단 적중·낙폭·교훈", "Reviewer", "통계·다음 판단"),
    "tb_order_plan": ("집행", "매수 계획 또는 사지 못한 이유", "allocation", "관제·감사"),
    "pipeline_runs": ("호환", "MVP 1차 11단계 러너 실행 기록", "구 러너", "호환 조회"),
    "pipeline_stage_attempts": ("호환", "MVP 1차 단계별 시도 기록", "구 러너", "호환 조회"),
    "pipeline_checkpoints": ("호환", "MVP 1차 단계 체크포인트", "구 러너", "호환 조회"),
    "order_submissions": ("운영", "불확실한 주문 제출의 소유권·복구 원장", "주문 제출기", "재시도·복구"),
    "tb_llm_usage": ("비용", "LLM 호출별 토큰과 추정 비용", "BudgetedAnalyzer", "예산·관제"),
    "tb_llm_budget_reservation": ("비용", "동시 호출 전 비용 예약과 정산 생명주기", "BudgetedAnalyzer", "예산 펜싱"),
    "tb_daily_bar": ("시장", "종목별 일봉 원장", "daily_bars", "screening·exits·평가"),
    "tb_benchmark_price": ("시장", "SPY 비교 기준 가격", "benchmark_spy", "사용자 수익률 화면"),
    "tb_job_run": ("운영", "JOB별 거래일 슬롯 실행·재시도 원장", "JobRunner", "스케줄러·관제·알림"),
    "tb_watch_sweep": ("장중", "정기 장중 재판단 스윕 원장", "WatchRunner", "재판단 디스패처"),
    "tb_watch_sweep_item": ("장중", "스윕의 종목·성향별 유료 호출 펜싱", "WatchRunner", "재판단 디스패처"),
    "tb_rejudgement_cooldown": ("장중", "종목·성향별 재판단 쿨다운 소유권", "재판단 디스패처", "중복 호출 차단"),
    "tb_disclosure_raw": ("원문", "전 시장 SEC 공시 원시 원장", "disclosures", "공시 분석·사건 라우팅"),
    "tb_news_raw": ("원문", "전 시장 뉴스·보도자료 원시 원장", "news·news_wire", "analysis·사건 라우팅"),
    "tb_event_source_cursor": ("사건", "소스별 증분 수집 체크포인트", "사건 수집기", "다음 수집 범위"),
    "tb_event_raw_document": ("사건", "공급자 사건 문서의 안정 식별자", "사건 수집기", "원문 버전"),
    "tb_event_raw_version": ("사건", "사건 원문·정규화 본문의 불변 버전", "사건 수집기", "정규화·증거·요약"),
    "tb_normalized_event": ("사건", "결정론적으로 정규화한 사건", "사건 정규화기", "라우팅·재판단"),
    "tb_event_evidence_pack": ("사건", "판단이 사용한 불변 원문 구간", "증거 빌더", "재판단·감사"),
    "tb_event_summary_cache": ("사건", "장문 사건 문서의 모델 요약 캐시", "요약기", "재판단"),
    "tb_event_processing_receipt": ("사건", "사건·종목·성향별 처리와 주문 영수증", "사건 실행기", "중복 차단·감사"),
}

DESCRIPTIONS = {
    "id": "테이블 내부 행 식별자",
    "as_of": "시장 국면 관측 UTC 시각",
    "as_of_date": "유니버스 스냅샷 기준일",
    "trade_date": "뉴욕 거래 세션 기준일",
    "ticker": "미국 주식 티커",
    "company_name": "회사명",
    "market_cap": "시가총액",
    "listing_status": "상장 상태 또는 상장폐지 보유 이월 상태",
    "universe_as_of": "참조한 유니버스 스냅샷 날짜",
    "bucket": "선별 전략 버킷",
    "rank": "해당 거래일의 선별 순위",
    "sector": "섹터",
    "score": "선별 종합 점수",
    "vix": "VIX 변동성 지수 값",
    "nasdaq_ret": "NASDAQ 기준 구간 수익률",
    "sp500_ret": "S&P 500 기준 구간 수익률",
    "rate": "거시 판단에 사용한 금리 값",
    "dollar": "달러 지수 또는 달러 강도 값",
    "source": "데이터를 제공하거나 계산한 출처",
    "volume": "거래량(주)",
    "rs_20": "20거래일 상대강도 지표",
    "vol_ratio": "기준 거래량 대비 현재 거래량 비율",
    "ret_1d": "판단 기준 대비 1거래일 수익률",
    "ret_3d": "판단 기준 대비 3거래일 수익률",
    "ret_5d": "판단 기준 대비 5거래일 수익률",
    "ret_20d": "20거래일 수익률",
    "atr_pct": "가격 대비 ATR 비율",
    "high_252_ratio": "52주 고가 대비 현재가 비율",
    "rsi": "상대강도지수(RSI)",
    "macd": "MACD 모멘텀 값",
    "ma20": "20거래일 이동평균",
    "ma50": "50거래일 이동평균",
    "trend": "기술적 추세 분류",
    "ml_probs": "기계학습 분류별 확률 JSON",
    "regime": "시장 국면(risk_on·neutral·risk_off)",
    "risk_score": "0~1 위험 점수",
    "sentiment_score": "0~1 방향성 점수",
    "importance": "0~1 중요도",
    "confidence": "0~1 판단 신뢰도",
    "source_trust": "0~1 출처 신뢰 점수",
    "grade": "뉴스·증거 품질 등급",
    "grade_score": "등급을 수치화한 점수",
    "title": "원문 제목",
    "url": "원문 접근 URL",
    "keywords": "검색·분류에 사용한 키워드 목록",
    "permission": "원문 사용·인용 권한 분류",
    "top_evidence": "판단에 가장 크게 기여한 근거 목록",
    "hard_block_reason": "하드 게이트가 판단을 차단한 이유",
    "parent_evidence_ids": "이 행을 만든 상위 근거 식별자 목록",
    "cycle_ts": "판단 사이클 시각",
    "inv_type": "투자 성향(aggressive·conservative)",
    "side": "판단 또는 체결 방향",
    "conviction": "0~1 전략가 확신도",
    "signal_consensus": "합의한 보조 신호 수",
    "decision": "처리·평결·계획 결과",
    "decided_layer": "평결이 종료된 계층",
    "verdict_source": "새 평결·캐시·쿨다운 중 재사용 구분",
    "signal_id": "전략가 판단 FK",
    "account_id": "모의 계좌 FK",
    "order_id": "주문 FK",
    "closes_order_id": "청산 대상 매수 주문 FK",
    "idempotency_key": "중복 효과를 차단하는 멱등 키",
    "quantity": "주문·체결 수량",
    "cash": "계좌 가용 현금(USD)",
    "equity": "현금과 보유 평가액을 합한 계좌 자산(USD)",
    "currency": "계좌 기준 통화",
    "avg_price": "체결 수량의 가중평균 가격(USD)",
    "filled_at": "체결이 확정된 UTC 시각",
    "entry_price": "진입 또는 판정 기준 가격",
    "stop_price": "매수 시 확정한 손절 가격",
    "take_profit_price": "매수 시 확정한 익절 가격",
    "order_type": "브래킷 매수 또는 청산 구분",
    "skipped_reason": "주문을 만들지 못한 이유",
    "job_name": "등록 JOB 이름",
    "slot_date": "JOB 멱등 기준 뉴욕 거래일",
    "attempts": "현재 슬롯을 집은 누적 시도 횟수",
    "started_at": "실행 시작 UTC 시각",
    "finished_at": "실행 종료 UTC 시각; 실행 중이면 NULL",
    "sweep_at": "예약된 장중 스윕 시각",
    "persona": "재판단 투자 성향",
    "owner_token": "동시 작업 소유권 토큰",
    "source_name": "외부 데이터 공급자 이름",
    "source_document_id": "공급자가 부여한 문서 식별자",
    "raw_version_id": "불변 원문 버전 FK",
    "event_id": "정규화 사건 FK",
    "event_key": "겹친 수집 창에서도 같은 사건을 식별하는 키",
    "source_sequence": "공급자 순서를 보존하는 값",
    "cursor_value": "다음 증분 수집의 시작점으로 사용할 공급자 커서",
    "document_id": "안정적인 원문 문서 식별자 FK",
    "normalized_text": "판단 입력용으로 정규화한 원문 본문",
    "raw_text": "공급자에서 수집한 원문 본문",
    "event_type": "정규화된 사건 종류",
    "start_offset": "근거 구간 시작 위치",
    "end_offset": "근거 구간 끝 위치",
    "quote_hash": "근거 인용문 무결성 해시",
    "content_hash": "원문 내용 해시",
    "input_hash": "LLM 입력 재현용 해시",
    "prompt_version": "사용한 프롬프트 버전",
    "policy_version": "사용한 정책 버전(현재 미배선 가능)",
    "model_provider": "모델 공급자",
    "model_name": "모델 이름",
    "model": "모델 이름",
    "prompt_tokens": "입력 토큰 수",
    "completion_tokens": "출력 토큰 수",
    "est_cost_usd": "추정 호출 비용(USD)",
    "day_offset": "판단일 이후 거래일 오프셋(1~5)",
    "is_hit": "판단 적중 여부",
    "max_drawdown": "관측 구간 최대 낙폭",
    "lesson": "회고에서 남긴 교훈",
    "created_at": "행 생성 UTC 시각",
    "updated_at": "마지막 변경 UTC 시각",
}


def split_items(body: str) -> list[str]:
    items, current, depth, quoted = [], [], 0, False
    for char in body:
        if char == "'":
            quoted = not quoted
        if not quoted:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                items.append(" ".join("".join(current).split()))
                current = []
                continue
        current.append(char)
    if current:
        items.append(" ".join("".join(current).split()))
    return [item for item in items if item]


def column_description(name: str) -> str:
    if name in DESCRIPTIONS:
        return DESCRIPTIONS[name]
    if name.endswith("_at"):
        return "해당 사건이 발생하거나 기록된 UTC 시각"
    if name.endswith("_date"):
        return "업무 기준 날짜"
    if name.endswith("_id"):
        return "행 또는 연결 대상 식별자"
    if name.startswith("is_") or name.startswith("has_"):
        return "조건 충족 여부"
    if name.endswith("_price") or name in {"open", "high", "low", "close"}:
        return "USD 가격 값"
    if name.endswith("_count"):
        return "관련 항목 수"
    if name.endswith("_ref"):
        return "외부 또는 내부 근거 참조"
    if name.endswith("_hash"):
        return "내용 무결성·재현성 해시"
    if name == "status":
        return "처리 생명주기 상태"
    if name in {"payload", "result_payload", "reason", "evidence", "sizing_hint"}:
        return "구조화된 JSON 데이터"
    if name in {"summary", "detail", "objection", "key_risk", "risk_rebuttal", "bull_case"}:
        return "사람이 읽는 설명 또는 판단 근거"
    return "테이블 목적에 따라 저장되는 업무 값"


def parse_schema() -> list[tuple[str, list[dict[str, str]], list[str]]]:
    source = re.sub(r"--.*", "", SCHEMA.read_text(encoding="utf-8"))
    found = []
    pattern = re.compile(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n\);", re.S)
    for match in pattern.finditer(source):
        name, body = match.groups()
        columns, constraints = [], []
        items = split_items(body)
        constraints = [
            item for item in items
            if item.upper().startswith(("PRIMARY ", "FOREIGN ", "UNIQUE ", "CHECK ", "CONSTRAINT "))
        ]
        seen_columns: set[str] = set()
        for item in items:
            upper = item.upper()
            if upper.startswith(("PRIMARY ", "FOREIGN ", "UNIQUE ", "CHECK ", "CONSTRAINT ")):
                continue
            column_match = re.match(r"(\w+)\s+(.+)", item)
            if not column_match:
                continue
            column, rest = column_match.groups()
            if column in seen_columns:
                raise ValueError(f"duplicate column in {name}: {column}")
            seen_columns.add(column)
            type_match = re.match(
                r"(.+?)(?=\s+(?:NOT NULL|NULL|DEFAULT|PRIMARY KEY|UNIQUE|REFERENCES|CHECK)\b|$)", rest, re.I
            )
            data_type = type_match.group(1) if type_match else rest
            key = []
            if "PRIMARY KEY" in upper or any(
                re.search(rf"PRIMARY KEY\s*\([^)]*\b{re.escape(column)}\b", c, re.I)
                for c in constraints
            ):
                key.append("PK")
            if "REFERENCES" in upper or any(
                re.search(rf"FOREIGN KEY\s*\([^)]*\b{re.escape(column)}\b", c, re.I)
                for c in constraints
            ):
                key.append("FK")
            if "UNIQUE" in upper or any(
                re.search(rf"UNIQUE\s*\([^)]*\b{re.escape(column)}\b", c, re.I)
                for c in constraints
            ):
                key.append("UQ")
            default_match = re.search(r"\bDEFAULT\s+(.+?)(?=\s+(?:CHECK|REFERENCES|UNIQUE|PRIMARY KEY)\b|$)", rest, re.I)
            columns.append(
                {
                    "name": column,
                    "type": data_type,
                    "required": "필수" if "NOT NULL" in upper or "PRIMARY KEY" in upper else "선택",
                    "key": "·".join(key) or "—",
                    "default": default_match.group(1) if default_match else "—",
                }
            )
        found.append((name, columns, constraints))
    return found


def render() -> str:
    tables = parse_schema()
    groups: dict[str, list[tuple[str, list[dict[str, str]], list[str]]]] = {}
    for table in tables:
        group = TABLES.get(table[0], ("기타", "스키마 테이블", "코드", "코드"))[0]
        groups.setdefault(group, []).append(table)
    lines = [
        "# 📚 데이터 사전",
        "",
        "!!! info \"생성 기준\"",
        f"    로컬 정본 [`schema.sql`](final/reference/schema.sql)에서 **{len(tables)}개 테이블과 컬럼을 기계 추출**했다. ",
        "    컬럼 추가·삭제는 `python3 tools/generate_schema_dictionary.py`로 다시 반영한다. ",
        "    PK·FK·CHECK의 최종 효력은 SQL 원문이 우선한다.",
        "",
        "## 읽는 법",
        "",
        "- **생산자**는 행을 쓰는 JOB·컴포넌트, **주요 소비자**는 그 행을 읽는 다음 단계다.",
        "- `선택`은 NULL 허용이다. NULL이 결손인지 ‘해당 증거 없음’인지 테이블 설명과 함께 판단한다.",
        "- `pipeline_*`는 MVP 1차 호환 유물이며 최종 일일 실행 원장은 `tb_job_run`이다.",
        "",
        "## 전체 테이블 지도",
        "",
        "| 그룹 | 테이블 | 역할 | 생산자 | 주요 소비자 |",
        "|---|---|---|---|---|",
    ]
    for name, _, _ in tables:
        group, purpose, producer, consumer = TABLES.get(name, ("기타", "스키마 테이블", "코드", "코드"))
        lines.append(f"| {group} | [`{name}`](#{name.replace('_', '-')}) | {purpose} | `{producer}` | {consumer} |")
    for group, group_tables in groups.items():
        lines.extend(["", f"## {group}", ""])
        for name, columns, constraints in group_tables:
            _, purpose, producer, consumer = TABLES.get(name, (group, "스키마 테이블", "코드", "코드"))
            lines.extend(
                [
                    f"<a id=\"{name.replace('_', '-')}\"></a>",
                    f"??? note \"`{name}` — {purpose} · {len(columns)}컬럼\"",
                    f"    **생산자:** `{producer}` · **주요 소비자:** {consumer}",
                    "",
                    "    | 컬럼 | 타입 | 필수 | 키 | 기본값 | 의미 |",
                    "    |---|---|:---:|:---:|---|---|",
                ]
            )
            for col in columns:
                lines.append(
                    "    | `{name}` | `{type}` | {required} | {key} | `{default}` | {description} |".format(
                        **col, description=column_description(col["name"])
                    )
                )
            if constraints:
                compact = "; ".join(constraints)
                lines.extend(["", f"    **테이블 제약:** `{compact}`", ""])
    lines.extend(
        [
            "",
            "## 관련 문서",
            "",
            "- [데이터 모델·ERD](데이터모델.md) — 관계와 핵심 제약을 그림으로 본다.",
            "- [JOB·파이프라인](파이프라인.md) — 어떤 JOB이 언제 행을 생산하는지 본다.",
            "- [데이터·판단 계보](데이터계보.md) — 한 판단을 실제로 역추적하는 방법을 본다.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)}")
