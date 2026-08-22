# Quantinue Wiki

Quantinue 최종 프로젝트의 설계·구현·운영·협업 지식을 한 곳에서 확인하는 팀 위키입니다.

현재 최종 프로젝트를 기준으로 정리되어 있으며, MVP 1차 자료는 변경하지 않는 동결 아카이브로 분리되어 있습니다.

사이트는 상단 탭 여섯 개로 나뉩니다. 탭 위치가 곧 그 문서의 기준 시점입니다.

| 탭 | 여기 있는 것 |
| --- | --- |
| 🏠 홈 | 프로젝트 요약과 문서 지도 |
| 📘 프로젝트 | 무엇을 만들었고 무엇이 검증됐는지 |
| ⚙️ 시스템 | 구조·판단 계층·데이터 모델·설정 정책 |
| 🛠️ 개발·운영 | 코드를 고치거나 실제로 켜는 방법 |
| 📜 기록 | 결정 로그·논의 기록·회의록 |
| 🧊 아카이브 | MVP 1차 동결 기록과 위키 운영 문서 |

## 바로 보기

- [배포된 위키](https://jaymunsh.github.io/quantinue-wiki/)
- [최종 프로젝트 한눈에 보기](https://jaymunsh.github.io/quantinue-wiki/facts/%EC%B5%9C%EC%A2%85%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8/)
- [핵심 기능 (최종) — Strategist·Critic·감시·재판단·회고](https://jaymunsh.github.io/quantinue-wiki/%ED%95%B5%EC%8B%AC%EA%B8%B0%EB%8A%A5/)
- [개발 시작하기](https://jaymunsh.github.io/quantinue-wiki/%EA%B0%9C%EB%B0%9C%EC%8B%9C%EC%9E%91%ED%95%98%EA%B8%B0/)
- [코드맵](https://jaymunsh.github.io/quantinue-wiki/%EC%BD%94%EB%93%9C%EB%A7%B5/)
- [API·화면 계약](https://jaymunsh.github.io/quantinue-wiki/API%EA%B3%84%EC%95%BD/)
- [데이터 모델·ERD](https://jaymunsh.github.io/quantinue-wiki/%EB%8D%B0%EC%9D%B4%ED%84%B0%EB%AA%A8%EB%8D%B8/)
- [전체 데이터 사전](https://jaymunsh.github.io/quantinue-wiki/%EB%8D%B0%EC%9D%B4%ED%84%B0%EC%82%AC%EC%A0%84/)
- [최종 발표·자료](https://jaymunsh.github.io/quantinue-wiki/%EC%B5%9C%EC%A2%85%EB%B0%9C%ED%91%9C/)

## 이 저장소의 기준

- 위키 정본: [`documents/`](documents/)
- 원본 보관: [`raw/`](raw/)
- 최종 산출물: [`final/`](final/)
- 위키 설정·테마: [`mkdocs.yml`](mkdocs.yml)
- 문서 검증 도구: [`tools/`](tools/)
- 최종 애플리케이션 소스: `quantinue-v2/app-v2` (별도 저장소. 아래 명령의 `<QUANTINUE_V2_ROOT>`는 각자 clone한 경로입니다)

애플리케이션의 실행 기준과 환경 구성은 위키의 [개발 시작하기](documents/개발시작하기.md)에서 확인합니다. 실제 소스 저장소와 위키는 분리되어 있으므로, 구현을 변경할 때는 애플리케이션 저장소와 이 위키의 문서를 함께 갱신합니다.

## 위키 로컬 실행

```bash
git clone https://github.com/jaymunsh/quantinue-wiki.git
cd quantinue-wiki

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 tools/lint.py
mkdocs serve
```

기본 주소는 `http://127.0.0.1:8000/`입니다. 이미 해당 포트를 사용 중이면 `mkdocs serve -a 127.0.0.1:8002`처럼 다른 포트를 지정할 수 있습니다.

## 최종 애플리케이션 로컬 실행

```bash
cd <QUANTINUE_V2_ROOT>/app-v2
cp .env.example .env
uv sync
uv run uvicorn quantinue.main:app --reload
```

Docker Compose로 데이터베이스까지 함께 실행하려면 다음을 사용합니다.

```bash
docker compose up --build --wait
```

상세한 포트, 기본 fixture, 테스트, 관찰 스크립트와 운영 주의사항은 [개발 시작하기](documents/개발시작하기.md)에 정리되어 있습니다. `.env`, API 키, Docker 볼륨과 운영 데이터는 저장소에 커밋하지 않습니다.

## 문서 구조

| 경로 | 역할 |
| --- | --- |
| `documents/` | 사이트에 노출되는 정본 문서. 확정 사실은 `documents/facts/`, MVP 1차 동결 기록도 여기에 보존 |
| `raw/` | 회의록·원문·수집 자료의 원본 보관 |
| `final/` | 최종 발표 HTML, PPT, 발표 관련 산출물 |
| `wiki/` | MkDocs가 문서를 노출하기 위한 연결 경로 |
| `tools/` | 링크·메타데이터·문서 구조 검증 도구 |
| `archive/` | 사이트에 노출하지 않는 보관물(구자료·작업 기록) |

## 배포

`main` 브랜치에 push하면 GitHub Actions가 문서 lint와 `mkdocs build --strict`를 실행한 뒤 GitHub Pages에 배포합니다. 배포 워크플로는 [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)에서 확인할 수 있습니다.

