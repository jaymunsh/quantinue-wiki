#!/usr/bin/env python3
"""
DocStill 증류 러너 — LLM 벤더 중립 (claude / codex / ollama / openai_compat)

사용:
    python3 tools/distill.py                       # config.json의 기본 백엔드
    python3 tools/distill.py --backend ollama      # 백엔드 즉석 지정
    python3 tools/distill.py --dry-run             # 새 파일 목록만 (LLM 호출 X)

설계 — 백엔드는 두 종류(type)뿐. 새 LLM 추가는 config.json만 손대면 됨:
    ┌ agent  (claude·codex): CLI 에이전트가 스스로 파일을 읽고 STATUS/질문.md를 씀. 우리는 호출만.
    └ api    (ollama·openai_compat): LLM은 텍스트만 주고받음 → 읽기/쓰기는 파이썬(이 파일)이 대행.
              ├ api_ollama  : ollama 네이티브 /api/generate
              └ api_openai  : OpenAI 호환 /v1/chat/completions (OpenAI·Groq·Together·vLLM·LM Studio…)

    벤더 중립의 핵심 = "무엇을 추출하나"(주장·4분류)는 tools/distill_prompt.md 한 곳에만 있고,
    "어떻게 파일을 읽고 쓰나"만 백엔드별로 여기서 감싼다. → 프롬프트는 어떤 LLM에도 그대로 통한다.
"""
import argparse, hashlib, html.parser, json, os, re, subprocess, sys, urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # mkwiki/
TOOLS = ROOT / "tools"
DOCS = ROOT / "documents"                               # 사이트 노출 문서(SSOT) — STATUS·질문·facts
ARCHIVE = ROOT / "archive"                              # 안 보는 파일 — 증류 백업 등
STATE_FILE = TOOLS / ".state.json"
PROMPT_FILE = TOOLS / "distill_prompt.md"

# ──────────────────────────── 공통: 설정/상태/파일 ────────────────────────────

def load_config() -> dict:
    return json.loads((TOOLS / "config.json").read_text(encoding="utf-8"))

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": {}, "run_count": 0}

def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

def scan_raw() -> list[Path]:
    exts = {".html", ".htm", ".md", ".txt", ".json"}
    return sorted(p for p in (ROOT / "raw").rglob("*")
                  if p.is_file() and p.suffix.lower() in exts and not p.name.startswith("."))

def find_new_files(state: dict) -> list[Path]:
    """해시가 바뀐(또는 처음 보는) 파일만 — 같은 파일 재투입은 자동 무시. 백엔드를 바꿔도 중복 없음."""
    return [p for p in scan_raw()
            if state["processed"].get(str(p.relative_to(ROOT))) != file_hash(p)]

def mark_processed(state: dict, files: list[Path]) -> None:
    for p in files:
        state["processed"][str(p.relative_to(ROOT))] = file_hash(p)
    state["run_count"] += 1
    state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")

def git_commit(msg: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=False)
    r = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, capture_output=True, text=True)
    print("📦 " + ("커밋 완료" if r.returncode == 0 else "변경 없음 (커밋 생략)"))

# ════════════════════ 백엔드 A · 에이전트형 (claude / codex) ════════════════════

def build_agent_prompt(new_files: list[Path], run_no: int) -> str:
    files = "\n".join(f"- {p.relative_to(ROOT)}" for p in new_files)
    return (
        f"tools/distill_prompt.md 를 읽고, 그 지시서대로 증류를 지금 수행하라.\n"
        f"이번 회차: {run_no}회차\n"
        f"이번에 처리할 새 파일 (이것만 처리, 다른 파일 재분석 금지):\n{files}\n"
        f"documents/STATUS.md 와 documents/질문.md 를 지시서 형식대로 갱신하고, "
        f"마지막에 보고(새 주장 N · 충돌 N · 소멸 N · 추천 안건)를 출력하라. "
        f"documents/facts/ 는 절대 직접 수정하지 마라."
    )

def run_agent(cfg: dict, backend: str, new_files: list[Path], run_no: int) -> bool:
    prompt = build_agent_prompt(new_files, run_no)
    cmd = [a.replace("{prompt}", prompt) for a in cfg[backend]["cmd"]]
    print(f"🤖 {backend} 에이전트 실행 중... (수 분 걸릴 수 있음)\n")
    return subprocess.run(cmd, cwd=ROOT).returncode == 0

# ════════════════════ 백엔드 B · API형 (ollama / openai_compat) ════════════════════
# LLM은 텍스트만 주고받음 → 읽기/쓰기는 여기(파이썬)서. 프롬프트·출력처리는 두 API가 공유.

class _TextExtractor(html.parser.HTMLParser):
    SKIP = {"script", "style", "head"}
    def __init__(self):
        super().__init__(); self.parts = []; self._skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP: self._skip += 1
    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip: self._skip -= 1
    def handle_data(self, d):
        if not self._skip and d.strip(): self.parts.append(d.strip())

def extract_text(p: Path, max_chars: int) -> str:
    raw = p.read_text(encoding="utf-8", errors="ignore")
    if p.suffix.lower() in (".html", ".htm"):
        ex = _TextExtractor(); ex.feed(raw); text = "\n".join(ex.parts)
    else:
        text = raw
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n...[잘림: 원문 {len(text)}자 중 {max_chars}자만]"
    return text

def build_api_prompt(new_files: list[Path], run_no: int, max_chars: int) -> str:
    instructions = PROMPT_FILE.read_text(encoding="utf-8")
    status = (DOCS / "STATUS.md").read_text(encoding="utf-8")
    questions = (DOCS / "질문.md").read_text(encoding="utf-8")
    facts = "\n\n".join(f"### documents/facts/{f.name}\n{f.read_text(encoding='utf-8')}"
                        for f in sorted((DOCS / "facts").glob("*.md")))
    docs = "\n\n".join(
        f"### 문서: {p.relative_to(ROOT)} (작성자: {p.parent.name})\n{extract_text(p, max_chars)}"
        for p in new_files)
    return f"""너는 팀 문서 증류기다. 아래 [지시서]대로 [새 문서들]을 증류하라.
파일을 직접 수정할 수 없으므로, 결과를 반드시 아래 3개 마커 형식 "만" 출력하라. 다른 말 금지.

===STATUS===
(STATUS.md 전체 새 내용 — 이번 {run_no}회차 기준 재작성)
===QUESTIONS===
(질문.md 전체 새 내용 — 기존 안건 유지 + 새 안건 추가)
===REPORT===
(보고: 새 주장 N건 · 충돌 N건 · 중복 소멸 N건 · 추천 안건 순위)

[지시서]
{instructions}

[현재 STATUS.md]
{status}

[현재 질문.md]
{questions}

[현재 facts (확정 사실 — 대조 기준)]
{facts}

[새 문서들]
{docs}
"""

def call_ollama(cfg: dict, prompt: str) -> str:
    o = cfg["ollama"]
    print(f"🦙 ollama({o['model']}) 호출 중...")
    req = urllib.request.Request(
        o["url"],
        data=json.dumps({"model": o["model"], "prompt": prompt, "stream": False}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=o.get("timeout_sec", 600)) as resp:
        return json.loads(resp.read())["response"]

def call_openai_compat(cfg: dict, prompt: str) -> str:
    o = cfg["openai_compat"]
    print(f"🔌 openai-compat({o['model']} @ {o['url']}) 호출 중...")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(o.get("api_key_env", ""), "") if o.get("api_key_env") else ""
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"model": o["model"], "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, "stream": False}
    req = urllib.request.Request(o["url"], data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=o.get("timeout_sec", 600)) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]

def apply_api_output(out: str, run_no: int) -> bool:
    """마커로 분리해 파일 기록. 마커가 깨지면 파일은 안 건드리고 원문만 보관(안전)."""
    m = re.search(r"===STATUS===\s*(.*?)\s*===QUESTIONS===\s*(.*?)\s*===REPORT===\s*(.*)", out, re.S)
    (ARCHIVE / "briefings").mkdir(parents=True, exist_ok=True)
    backup = ARCHIVE / "briefings" / f"api_{run_no}회차_{datetime.now():%m%d_%H%M}.txt"
    backup.write_text(out, encoding="utf-8")
    if not m:
        print("⚠️ 출력 마커를 못 찾음 — 파일 미수정, 원문만 보관:", backup.name); return False
    (DOCS / "STATUS.md").write_text(m.group(1).strip() + "\n", encoding="utf-8")
    (DOCS / "질문.md").write_text(m.group(2).strip() + "\n", encoding="utf-8")
    print("\n────── 보고 ──────\n" + m.group(3).strip())
    return True

def run_api(cfg: dict, backend: str, new_files: list[Path], run_no: int) -> bool:
    o = cfg[backend]
    prompt = build_api_prompt(new_files, run_no, o.get("max_chars_per_doc", 60000))
    caller = call_ollama if o["type"] == "api_ollama" else call_openai_compat
    # api형 백엔드는 config 키 이름이 caller 안에서 고정('ollama'/'openai_compat')이므로
    # 별칭 백엔드를 쓰려면 config에 같은 키로 두거나 caller를 일반화하면 됨.
    return apply_api_output(caller(cfg, prompt), run_no)

# ──────────────────────────── 메인 ────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="DocStill 증류 러너 (벤더 중립)")
    ap.add_argument("--backend", default=None, help="claude|codex|ollama|openai_compat (config의 키)")
    ap.add_argument("--dry-run", action="store_true", help="새 파일 목록만 보고 종료")
    ap.add_argument("--no-commit", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    backend = args.backend or cfg["backend"]
    if backend not in cfg or not isinstance(cfg[backend], dict) or "type" not in cfg[backend]:
        sys.exit(f"❌ 알 수 없는 백엔드: {backend} (config.json 확인)")
    btype = cfg[backend]["type"]

    state = load_state()
    new_files = find_new_files(state)
    run_no = state["run_count"] + 1

    print(f"🌀 DocStill 증류 {run_no}회차 · 백엔드={backend} (type={btype})")
    if not new_files:
        print("변경된 파일 없음 — 종료"); return
    print(f"새 파일 {len(new_files)}개:")
    for p in new_files: print("  •", p.relative_to(ROOT))
    if args.dry_run:
        print("(dry-run — 여기서 종료)"); return

    if btype == "agent":
        ok = run_agent(cfg, backend, new_files, run_no)
    elif btype in ("api_ollama", "api_openai"):
        ok = run_api(cfg, backend, new_files, run_no)
    else:
        sys.exit(f"❌ 지원하지 않는 type: {btype}")

    if ok:
        mark_processed(state, new_files); save_state(state)
        if cfg.get("auto_git_commit", True) and not args.no_commit:
            git_commit(f"증류 {run_no}회차 ({backend})")
        print("\n✅ 끝. STATUS.md 와 질문.md 를 확인하세요.")
    else:
        print("\n⚠️ 증류 실패 — 상태 기록 안 함 (다음 실행 때 같은 파일 재시도)")
        sys.exit(1)

if __name__ == "__main__":
    main()
