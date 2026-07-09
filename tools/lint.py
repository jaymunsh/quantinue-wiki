#!/usr/bin/env python3
"""위키 정적 점검기 — /점검의 '기계 검사' 절반 (LLM 없이 몇 초 안에 끝나는 결정적 검사).

사용:
    python3 tools/lint.py            # 전체 검사
    python3 tools/lint.py --only nav_coverage,symlinks
    python3 tools/lint.py --list     # 검사 목록

설계 — [엔진]과 [프로젝트 설정]의 분리:
    · 엔진   = Finding / @check 레지스트리 / 리포터. 어떤 MkDocs 위키에도 그대로 재사용.
    · 설정   = CONFIG 딕셔너리 하나. 다른 프로젝트로 가져가면 여기만 고친다.
      (프로젝트 고유 검사는 CONFIG 키가 비어 있으면 자동 skip — 설정 없이도 엔진은 돈다)
    · 검사 추가 = @check("이름", "설명") 함수 하나. Finding을 yield.

종료 코드: ERROR ≥ 1 → 1 (CI 게이트용), WARN만 있으면 0.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import yaml

ROOT = Path(__file__).resolve().parent.parent

# ═══════════════════════ 프로젝트 설정 (재사용 시 여기만 수정) ═══════════════════════

CONFIG = {
    # ── 공통 (모든 MkDocs 위키) ──
    "mkdocs_yml": "mkdocs.yml",
    "content_dir": "documents",            # 문서 원본 디렉터리 (docs_dir가 심볼릭으로 가리키는 곳)
    "nav_exclude": [],                      # nav에 없어도 되는 md (content_dir 기준 상대경로 glob)

    # ── 프로젝트 고유 (없는 프로젝트는 값을 비우면 해당 검사 skip) ──
    # 결정 번호 연속성: 결정로그 표의 행 번호(| N |)가 1..N 빠짐없이 존재하는지
    "decision_log": "documents/facts/결정로그.md",
    "decision_pattern": r"(?m)^\|\s*(\d+)\s*\|",
    # 안건 코드 정합: 문서 전체에서 참조된 코드가 안건 파일에 실존하는지
    "agenda_file": "documents/질문.md",
    "agenda_pattern": r"\b([ABC]\d{1,2})\b",
    "agenda_allow": ["facts/결정로그.md", "업데이트로그.md", "회의록/*.md", "STATUS.md"],  # 이력 페이지의 '해결됨' 기록은 정당
    # 운영 용어 금지: 팀 페이지에 나오면 안 되는 낱말 (distill_prompt.md 언어 규칙)
    "team_pages": ["홈.md", "facts/*.md", "질문.md", "산출물_현황판.md"],
    "forbidden_terms": ["증류", "병입"],
    # 낡은 경로: 어디에도 있으면 안 되는 죽은 참조 패턴
    "stale_patterns": ["mkwiki/", "briefings/", "정보분석.md", "코어인프라.md", "tb_memory_entries"],
    "stale_allow": ["업데이트로그.md", "STATUS.md", "회의록/*.md", "질문.md", "facts/결정로그.md",
                    "사용가이드.md", "시스템설명서.md"],  # 이력·안건·운영 문서의 언급은 정당
}

# ═══════════════════════════════ 엔진 (재사용부) ═══════════════════════════════

@dataclass
class Finding:
    level: str      # "ERROR" | "WARN"
    where: str      # 파일 경로 등
    msg: str

CheckFn = Callable[[], Iterator[Finding]]
_REGISTRY: list[tuple[str, str, CheckFn]] = []

def check(name: str, desc: str):
    def deco(fn: CheckFn):
        _REGISTRY.append((name, desc, fn))
        return fn
    return deco

def nfc(s: str) -> str:
    """macOS 파일시스템은 NFD를 돌려주므로 모든 경로 비교는 NFC로 통일한다."""
    return unicodedata.normalize("NFC", s)

def load_mkdocs() -> dict:
    """mkdocs.yml 로드 — `!!python/name:` 같은 커스텀 태그는 무시하고 구조만 읽는다."""
    class Loader(yaml.SafeLoader):
        pass
    Loader.add_multi_constructor("tag:yaml.org,2002:python/name", lambda *_: None)
    Loader.add_multi_constructor("!", lambda *_: None)
    return yaml.load((ROOT / CONFIG["mkdocs_yml"]).read_text(encoding="utf-8"), Loader)

def nav_paths(nav) -> Iterator[str]:
    """nav 트리에서 md 경로 문자열만 재귀 추출."""
    if isinstance(nav, str):
        if nav.endswith(".md"):
            yield nav
    elif isinstance(nav, list):
        for item in nav:
            yield from nav_paths(item)
    elif isinstance(nav, dict):
        for v in nav.values():
            yield from nav_paths(v)

def content_md_files() -> list[Path]:
    """content_dir 아래 모든 md (심볼릭 아님 — 원본 기준)."""
    base = ROOT / CONFIG["content_dir"]
    return sorted(p for p in base.rglob("*.md") if p.is_file())

def rel_content(p: Path) -> str:
    return nfc(str(p.relative_to(ROOT / CONFIG["content_dir"])))

def docs_dir() -> Path:
    return ROOT / load_mkdocs().get("docs_dir", "docs")

def matches_any(rel: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, g) for g in globs)

# ═══════════════════════════════ 공통 검사 ═══════════════════════════════

@check("nav_targets", "nav의 모든 항목이 docs_dir에 실존하는가")
def check_nav_targets() -> Iterator[Finding]:
    dd = docs_dir()
    for path in nav_paths(load_mkdocs().get("nav", [])):
        if not (dd / path).exists():        # exists()는 심볼릭을 따라감
            yield Finding("ERROR", f"mkdocs.yml → {path}", "nav 항목이 가리키는 파일 없음")

@check("nav_coverage", "content_dir의 모든 md가 nav에 있는가")
def check_nav_coverage() -> Iterator[Finding]:
    in_nav = {nfc(p) for p in nav_paths(load_mkdocs().get("nav", []))}
    # 홈 특례: nav의 index.md ↔ content의 홈.md 같은 개명 심볼릭은 docs_dir 쪽 이름으로 비교
    dd = docs_dir()
    served: set[str] = set()
    for dirpath, _dirs, files in os.walk(dd, followlinks=True):
        for f in files:
            if f.endswith(".md"):
                served.add(nfc(os.path.relpath(os.path.join(dirpath, f), dd)))
    for path in sorted(served):
        if path in in_nav or matches_any(path, CONFIG["nav_exclude"]):
            continue
        yield Finding("WARN", path, "사이트에 노출되지만 nav에 없음 (검색으로만 접근 가능)")

@check("symlinks", "docs_dir의 심볼릭 링크가 전부 살아있는가")
def check_symlinks() -> Iterator[Finding]:
    dd = docs_dir()
    for p in dd.rglob("*"):
        if p.is_symlink() and not p.exists():
            yield Finding("ERROR", str(p.relative_to(ROOT)), f"깨진 심볼릭 → {os.readlink(p)}")

@check("internal_links", "md 내부 상대 링크가 실존 파일을 가리키는가")
def check_internal_links() -> Iterator[Finding]:
    # 원본(content_dir) ∪ 서빙(docs_dir, 개명 심볼릭 포함) — index.md ↔ 홈.md 같은 개명 링크도 유효
    existing = {rel_content(p) for p in content_md_files()}
    dd = docs_dir()
    for dirpath, _dirs, files in os.walk(dd, followlinks=True):
        for f in files:
            if f.endswith(".md"):
                existing.add(nfc(os.path.relpath(os.path.join(dirpath, f), dd)))
    link_re = re.compile(r"\]\(([^)#\s]+\.md)(#[^)]*)?\)")
    for p in content_md_files():
        base = p.parent.relative_to(ROOT / CONFIG["content_dir"])
        for m in link_re.finditer(p.read_text(encoding="utf-8")):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = nfc(os.path.normpath(str(base / target)))
            if resolved.startswith(".."):    # content_dir 밖 — docs_dir 특수 링크는 별도
                continue
            if resolved not in existing:
                yield Finding("ERROR", rel_content(p), f"깨진 링크 → {target}")

@check("unicode_collision", "NFC/NFD 정규화가 다른 동명 파일이 있는가")
def check_unicode_collision() -> Iterator[Finding]:
    seen: dict[str, str] = {}
    for p in content_md_files():
        raw = str(p.relative_to(ROOT))
        key = nfc(raw)
        if key in seen and seen[key] != raw:
            yield Finding("ERROR", raw, f"NFC 정규화 시 {seen[key]} 와 충돌 (같은 이름 두 파일)")
        seen[key] = raw

# ═══════════════════════════ 프로젝트 고유 검사 ═══════════════════════════

@check("decision_continuity", "결정 번호 #1..#N 연속성 (결정로그)")
def check_decision_continuity() -> Iterator[Finding]:
    log = CONFIG.get("decision_log")
    if not log or not (ROOT / log).exists():
        return
    text = (ROOT / log).read_text(encoding="utf-8")
    nums = sorted({int(g) for m in re.finditer(CONFIG["decision_pattern"], text)
                   for g in m.groups() if g})
    if not nums:
        return
    missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
    if missing:
        yield Finding("ERROR", log, f"결정 번호 누락: {missing} (최대 #{max(nums)})")

@check("agenda_refs", "문서에서 참조된 안건 코드가 안건 파일에 실존하는가")
def check_agenda_refs() -> Iterator[Finding]:
    agenda = CONFIG.get("agenda_file")
    if not agenda or not (ROOT / agenda).exists():
        return
    pat = re.compile(CONFIG["agenda_pattern"])
    defined = set(pat.findall((ROOT / agenda).read_text(encoding="utf-8")))
    allow = CONFIG.get("agenda_allow") or []
    for p in content_md_files():
        rel = rel_content(p)
        if nfc(str(p.relative_to(ROOT))) == nfc(agenda) or matches_any(rel, allow):
            continue
        used = set(pat.findall(p.read_text(encoding="utf-8")))
        for code in sorted(used - defined):
            yield Finding("WARN", rel, f"안건 코드 {code} 가 {Path(agenda).name} 에 없음 (해결됐으면 참조 제거)")

@check("forbidden_terms", "팀 페이지에 운영 용어가 있는가")
def check_forbidden_terms() -> Iterator[Finding]:
    terms = CONFIG.get("forbidden_terms") or []
    pages = CONFIG.get("team_pages") or []
    if not terms or not pages:
        return
    for p in content_md_files():
        rel = rel_content(p)
        if not matches_any(rel, pages):
            continue
        text = p.read_text(encoding="utf-8")
        for t in terms:
            if t in text:
                line = next(i for i, l in enumerate(text.splitlines(), 1) if t in l)
                yield Finding("WARN", f"{rel}:{line}", f"팀 페이지에 운영 용어 '{t}' 잔존")

@check("stale_patterns", "죽은 경로·낡은 참조 패턴이 남아있는가")
def check_stale_patterns() -> Iterator[Finding]:
    pats = CONFIG.get("stale_patterns") or []
    allow = CONFIG.get("stale_allow") or []
    for p in content_md_files():
        rel = rel_content(p)
        if matches_any(rel, allow):
            continue
        text = p.read_text(encoding="utf-8")
        for pat in pats:
            if pat in text:
                line = next(i for i, l in enumerate(text.splitlines(), 1) if pat in l)
                yield Finding("WARN", f"{rel}:{line}", f"낡은 참조 '{pat}'")

# ═══════════════════════════════ 리포터 ═══════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description="위키 정적 점검기")
    ap.add_argument("--only", help="쉼표로 구분한 검사 이름 (기본: 전체)")
    ap.add_argument("--list", action="store_true", help="검사 목록 출력")
    args = ap.parse_args()

    if args.list:
        for name, desc, _ in _REGISTRY:
            print(f"  {name:22s} {desc}")
        return 0

    selected = set(args.only.split(",")) if args.only else None
    errors = warns = 0
    for name, desc, fn in _REGISTRY:
        if selected and name not in selected:
            continue
        findings = list(fn())
        mark = "✅" if not findings else ("❌" if any(f.level == "ERROR" for f in findings) else "⚠️")
        print(f"{mark} {name} — {desc}")
        for f in findings:
            print(f"    [{f.level}] {f.where} — {f.msg}")
            errors += f.level == "ERROR"
            warns += f.level == "WARN"

    print(f"\n결과: ERROR {errors} · WARN {warns}")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
