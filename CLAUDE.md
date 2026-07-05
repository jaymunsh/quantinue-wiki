# quantinue-wiki — 운영 규칙 (모든 세션 공통)

이 저장소 = **DocStill**: 팀 "여름이었다"(5인)의 Quantinue(미국주식 자율 AI 자동매매, 전부 가상) 프로젝트 문서를
raw(원본) → 증류(AI 대조) → 병입(확정) → facts(SSOT) → MkDocs 웹 위키로 관리하는 시스템.
운영자 = 문성혁 (파이프라인 ⑪ Reviewer + schema keeper).

## 세션 시작 시

1. `documents/STATUS.md`(운영 현황)를 읽고 현재 공정 상태를 파악한다.
2. 시스템 동작 원리가 필요하면 `documents/시스템설명서.md`, 운영 절차는 `documents/사용가이드.md`.

## 구조 (핵심만)

```
raw/{이름}/        원본 — 절대 불변. 수정·삭제 금지 (운영자가 직접 지시한 경우만 예외)
documents/         사이트 노출 = SSOT. STATUS·질문·산출물·홈 + facts/(확정 사실)
archive/           사이트에 안 보이는 보관물 (briefings, 구자료)
tools/             증류 엔진. distill_prompt.md = 규칙 소스코드, distill.py = 러너
wiki/              MkDocs docs_dir — documents/로 향하는 심볼릭 링크만 있음
mkdocs.yml         nav 3구역: 프로젝트 / 협업 / 운영
```

- `tools/distill.py`는 `documents/`·`archive/` 경로를 하드코딩(DOCS·ARCHIVE 상수) — 파일을 옮기면 여기도 같이 고칠 것.
- 새 페이지 추가 = ① documents/에 파일 ② wiki/에 심볼릭 ③ mkdocs.yml nav 등록, 3종 세트.

## 불변식 (어기면 시스템이 깨진다)

1. **raw는 불변.** 증류는 raw를 읽기만 한다.
2. **facts/는 병입 명령("~확정, 병입해줘")으로만 수정.** 증류는 STATUS·질문만 갱신.
3. **모든 확정에는 출처와 결정 번호**(`결정 #k`)가 남는다. 뒤집힌 결정은 삭제하지 않고 새 번호로 "변경" 기록.
4. **원문에 없는 내용을 지어내지 않는다.** 출처를 못 대는 주장은 버린다.

## 문서 작성 스타일

`tools/distill_prompt.md`의 "산출물 작성 스타일" + "중복·언어 규칙" 절이 유일한 기준이다. 요지:
- 한 사실은 한 곳에만 (열린 안건=질문.md, 확정 이력=결정로그.md, 나머지는 링크)
- 팀 페이지에 증류·병입 같은 운영 용어 금지, 안건 코드(A1·B8)는 질문.md 안에서만
- 3인칭 중립("성혁 담당"), 페이지 머리는 admonition 박스 1~2개, 벽글 인용문 금지
- 흐름·구조·일정은 Mermaid (flowchart·erDiagram·gantt), 나열은 표

## 검증 루틴 (문서·설정을 고친 뒤 반드시)

```bash
python3 -m mkdocs build          # 에러·링크 경고 0 확인 (Material 팀 공지 경고는 무시)
```
- 렌더 결과는 `site/<페이지>/index.html`을 grep으로 확인 (홈만 예외: `site/index.html`).
- `mkdocs serve`가 백그라운드에 떠 있으면 자동 리로드된다 — 재시작 불필요.
- 한글 파일명 git 명령은 `git -c core.quotepath=false`로 확인 (8진수 이스케이프 오탐 방지).

## git 규칙

- 커밋 메시지는 한글, 논리 단위별로 분리(구조 변경 vs 내용 변경 섞지 않기).
- 커밋·푸시는 운영자가 요청할 때만. `raw/` 파일 삭제가 보이면 커밋 전에 반드시 운영자에게 확인.
- 배포: `python3 -m mkdocs gh-deploy --force` (운영자 확인 후).

## 자주 하는 작업

| 작업 | 방법 |
|---|---|
| 증류 | `/증류` 명령 또는 tools/distill_prompt.md 읽고 지시서대로 수행 |
| 병입 | `/병입 <결정 내용>` — 지시서 "병입 지시를 받았을 때" 절차대로 |
| 사이트 점검 | `/점검` — nav 누락·깨진 링크·낡은 참조 감사 |
| 배포 | `/배포` — build 검증 후 gh-deploy |
