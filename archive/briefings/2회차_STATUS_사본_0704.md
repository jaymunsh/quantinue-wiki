# 📊 팀 현황판 (STATUS)

> 기준: **2026-07-04 · 증류 2회차** · 이번 처리 3개 — 은미 Strategist 진행상황 · 창욱 정보분석 개발보고서 · 창욱 전달예시 10건
> ✅ 병입 확정 **0** · 🟢 확정후보 **26** · ❓ 미정 **13** · ⚠️ 충돌 **8**
> 🔥 이번 회차 핵심: **각 파트가 실제 인터페이스 계약·스키마를 만들기 시작 → 서로 안 맞는 지점이 대거 드러남.** "데이터 계약"을 맞추는 게 지금 최우선.

---

## ⚠️ 충돌 8건 (증류 1회차 4건 + 이번에 4건 추가·심화)

| # | 충돌 | 실태 | 왜 중요 |
|---|---|---|---|
| 1 | **투자유형 (3자 불일치)** 🔴 | 설계서 7/3=**공격형 1종** · 은미=**안정형+공격형 2개** · solutions=**균형형** | 문턱값·스크리너·PM·POLICY가 전부 유형에 종속. 셋이 다 다름 — **제일 급함** |
| 2 | **저장소 DB** 🔴 | 설계서=Postgres+Timescale · 은미=PostgreSQL · **창욱=SQLite(이미 코드 구현됨)** | 창욱은 실제로 SQLite로 돌아가는 코드 보유. "로컬 SQLite → 통합 Postgres" 시점/방식 합의 필요 |
| 3 | **테이블명 규칙** | 은미=`tb_` 접두사(tb_news_signals…) · 창욱=접두사 없음(news_signals…) | 같은 테이블을 다르게 부름 → SELECT 깨짐 |
| 4 | **필드명: category vs sector** | 창욱 전송=`category` · 은미 요청=`sector`(v1.3에서 변경) | 이름 하나 안 맞으면 조인/파싱 실패 |
| 5 | **cross_source_confirmed 필드** | 은미 필수 요청 · 창욱 NewsBundle에 명시 없음(news_confirmed/rumor·confirmed_score만) | 은미 교차확인 로직이 이 필드에 의존 — 창욱이 만들어줘야 |
| 6 | **cycle_id vs run_id** | 은미=`cycle_id`(사이클 키) · solutions=`run_id` · 창욱=accession/news_key(사이클 개념 없음) | 신호 매칭 열쇠. 이름·생성 주체 통일 필요 |
| 7 | **LLM 모델 (3자)** | 설계서=GPT-5.4mini/5.5 · 은미=GPT-4o · 창욱=gpt-4o-mini | 비용·품질·프롬프트가 갈림. 모델명 확정 필요 |
| 8 | **데이터 흐름 아키텍처** | 은미=**Pull**(각 팀 DB 저장→Strategist가 SELECT) · solutions=**Context Builder가 조립(push)** | 파이프라인 배관 방식 자체가 다름 |

## 🔄 이번에 새로 드러난 것 (은미·창욱 실제 구현 수준)

**이은미(Strategist) — 인터페이스 계약을 매우 상세히 확정**
- 담당 = STEP 2~7 · 실행 08:30 AM ET (APScheduler)
- **판단 = 코드 게이트 샌드위치**: 앞문(hard_block·macro_veto) → GPT-4o(맥락 판단·계산 안 함) → 뒷문(min_conviction). 강제 규칙 3개(🔒), 나머진 힌트
- **문턱 POLICY 이원화**(안정형/공격형): 공시·뉴스·기술 문턱, 필요 합의 수(3/2), 매크로 거부권(risk_score 6/8), min_conviction(8.0/5.0)
- **출력 tb_strategist_signals** 컬럼 확정: side·conviction·signal_consensus·bull_case·key_risk·risk_rebuttal·counter_scenarios·evidence·sizing_hint(PM용 제안)·persona_notes(MVP2)
- **Critic 전달 = 요약+설득 payload만**(원본 4신호 안 보냄, cycle_id로 조회)

**정창욱(정보분석) — 이미 코드 구현 + 산출물 계약 확정**
- 산출물 = **DisclosureBundle(24필드)·NewsBundle(31필드)** JSON
- **매매권한 6단계**(BLOCK_ALL→TRADE_ELIGIBLE) · 가장 보수적 채택 · MVP는 스스로 매수확정 안 함
- **하드리스크 키워드→권한 강제**(거래정지/파산/상폐/회계문제/희석 = hard_block)
- **출처 등급 3단계**(ALLOW1.0/GRAY0.6/BLOCK0.0) + 키워드 화이트/블랙 사전필터 → LLM 전에 노이즈 컷
- **event_type 11종 온톨로지**(공시·뉴스 공유) · **0~1 지표 산출 공식**(신뢰가중 집계·비대칭 감쇠) 단일 진실원천
- 코드=사실/LLM=해석만 · 증분(processed_filings.accession) · 전방수익률 백테스트(+1/3/5d)
- ⚠️ 알려진 갭: hard_risk 플래그 미소비(2.06 자동차단 안 됨) · event_type=other 빈발 · sector 미채움

**🔗 나(성혁·Reviewer)와 직접 연결된 발견:** 은미가 **tb_memory_entries**(내 회고 출력)를 소비하는 스펙을 확정함 — `ticker·cycle_id·side·conviction·outcome·lesson·created_at` → Strategist가 ticker별 최근 5개를 GPT 프롬프트에 주입. **내 Reviewer 초안(review_note)을 이 스키마에 맞춰야 함.**

## 🟢 확정후보 (1회차 15 + 이번 11 = 26) — 상세는 병입 시 facts로
1회차 15건 + 신규: Strategist 코드게이트 샌드위치 · 문턱 POLICY 이원화 · tb_strategist_signals 컬럼 · Critic payload=요약만 · 정보분석 6단계 권한 · 하드리스크 키워드 · 출처 3등급 · event_type 11종 · 0~1 지표 공식 · 증분 수집 · tb_memory_entries 스키마

## ❓ 미정 13 — 회의 안건 (상세 질문.md)
기존 7건 + 인터페이스 계약 6건: 기술 trend 값형태 · 매크로 risk_score 범위(0~10 vs 0~1) · cycle_id 생성주체 · category→sector 확정 · cross_source_confirmed 생성책임 · 테이블명 tb_ 규칙

## 👥 파트별 한 줄
| 파트 | 근황 |
|---|---|
| 지현(코어) | 설계서 7/3 구체화(5버킷·매크로식·ERD) — 단 은미·창욱 인터페이스와 정합 확인 필요 |
| 창욱(뉴스공시) | **코드 구현 상당 진척**(collector·analyzer·policy·storage/SQLite). 산출물 계약 확정 |
| 은미(전략가) | **인터페이스 계약 v1.8까지 매우 상세**. 팀에 6건 확인 요청 중 |
| 미연(크리틱) | 아직 자료 없음 — 은미가 Critic payload 구조 합의 대기 |
| 성혁(리뷰어) | tb_memory_entries 스키마가 은미 쪽에서 확정됨 → 내 review_note 정합 필요 |
