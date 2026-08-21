# 🔌 API·화면 계약

!!! info "범위"
    최종 FastAPI 앱의 현재 라우트와 권한 경계를 기록한다. 화면은 서버 렌더링 Jinja2이며,
    API 응답 모델의 정본은 `src/quantinue/api/`와 `main.py`다. 이 문서의 라우트를 추가·삭제하면
    관련 route audit 테스트와 이 표를 함께 갱신한다.

## 접근 흐름

| 영역 | 경로 | 권한 | 성격 |
|---|---|---|---|
| 로그인 | `/login` | 비로그인 | GET 폼, POST 인증 |
| 로그아웃 | `/logout` | 로그인 | POST, 세션 삭제 |
| 관리자 관제 | `/admin` | admin | 실행·실패·계좌 관측 |
| 사용자 계좌 | `/me` | user | 본인 계좌·보유·수익률 조회 |
| 일정 | `/schedule`, `/admin/schedule` | 로그인 영역 | JOB 주기·runtime 상태 |
| 운영 로그 | `/admin/logs` | admin | 실행·경고 로그 조회 |
| 관리자 계좌 | `/admin/accounts` | admin | 계좌·사용자 생성 및 상태 변경 |

`GET /`는 세션이 없거나 관리자면 `/admin`, 일반 사용자면 `/me`로 보낸다.
사용자 구역에는 쓰기 라우트를 두지 않는 것이 현재 보안 계약이다.

## 읽기 API

| Method | 경로 | 응답 | 용도 |
|---|---|---|---|
| GET | `/health` | `HealthResponse` | `status`, `broker_mode`, `llm_mode` 확인 |
| GET | `/api/runtime/status` | `RuntimeView` | JOB/WatchRunner 소유권·활성 상태 |
| GET | `/api/accounts` | `AccountRosterView` | 관리자용 계좌 목록 |
| GET | `/api/pipeline/today` | `PipelineDayView` | 거래일별 JOB·판단·주문 관제 데이터 |

예시:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/runtime/status
curl -s 'http://127.0.0.1:8000/api/pipeline/today?slot=2026-07-21'
```

`/health`는 비밀값이나 토큰을 반환하지 않는다. `/api/accounts`와 pipeline API는
인증·권한 guard를 통과해야 하며, 개발 fixture에서도 화면 계약을 유지한다.

## 리뷰 실행 API

```http
POST /api/reviews/{signal_id}/process
X-Quantinue-Control-Token: <configured token>
```

응답 모델 `ReviewProcessResponse`:

```json
{
  "signal_id": 123,
  "status": "completed",
  "captured_offsets": [1, 3, 5]
}
```

이 호출은 T+1~T+5 due 종가를 멱등 처리한다. PostgreSQL 실행에서 control token이
설정된 경우 헤더가 필요하다. 같은 signal을 다시 호출해도 이미 기록된 offset은
중복 생성하지 않는다.

## 관리자 쓰기 API

| Method | 경로 | 입력 | 결과 |
|---|---|---|---|
| POST | `/admin/accounts` | `broker_account_id`, `inv_type`, `opening_cash`, `login_id`, `display_name`, `password` | 계좌·사용자 생성 후 계좌 목록으로 이동 |
| POST | `/admin/accounts/{id}/profile` | `inv_type=aggressive\|conservative` | 성향 변경 |
| POST | `/admin/accounts/{id}/status` | `account_status=active\|paused\|closed` | 계좌 상태 변경 |
| POST | `/admin/jobs/release` | `job_name`, `slot_date` | `running`으로 굳은 슬롯 잠금 해제 |

모든 관리 쓰기는 HTML form + `303 See Other` 방식이다. 알 수 없는 성향·상태는
`422`, 없는 원장 대상은 `404`다. 슬롯 release는 JOB을 직접 실행하지 않고 잠금만
풀어 다음 runner가 재시도하게 한다.

## 로그인 계약

- `POST /login` 입력은 `login_id`, `password`다.
- 존재하지 않는 계정·틀린 비밀번호·정지 계정은 동일한 메시지를 반환해 계정 존재를
  노출하지 않는다.
- 성공 시 admin은 `/`, user는 `/me`로 이동한다.
- 세션 쿠키는 signed cookie이며 `QUANTINUE_SESSION_SECRET`을 지정하지 않으면
  재기동 시 세션이 무효화될 수 있다.
- 비밀번호와 control token은 URL query나 로그에 넣지 않는다.

## 응답과 원장의 책임 경계

화면이나 API의 숫자가 이상하면 프론트 표시부터 고치지 않는다.

1. `/api/pipeline/today`의 slot과 현재 runtime owner를 확인한다.
2. `tb_job_run`, `tb_strategist_signals`, `tb_critic_verdict`, `tb_order`, `tb_fill`의
   원장 계보를 확인한다.
3. read model(`src/quantinue/api/pipeline_day.py`, `pipeline_presentation.py`)이
   원장 값을 올바르게 투영하는지 확인한다.
4. 화면 템플릿을 수정하고 관련 web/API 테스트를 추가한다.

화면 표시를 위해 원장에 없는 값을 임의로 채우지 않는다. 특히 `no_trade`, NULL 증거,
실패 JOB은 각각의 의미를 보존해야 한다.

## API 변경 체크리스트

- [ ] `src/quantinue/api/` 응답 모델 또는 form 입력을 갱신했는가?
- [ ] 권한 guard와 사용자/관리자 경계를 확인했는가?
- [ ] 성공·422·404·인증 실패 테스트가 있는가?
- [ ] 화면이 호출하는 API의 fixture 응답을 갱신했는가?
- [ ] [데이터 사전](데이터사전.md)과 [역할 계약](역할협업계약.md)에 영향이 있는가?
- [ ] `API계약.md`와 결정 로그를 갱신했는가?

