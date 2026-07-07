"""Phase 2 자동 스모크 테스트.

[1-A §4 체크리스트 7항목 유지 — 셀렉터만 새 내비 구조에 맞게 갱신]
+ [Phase 2 §6-2 신규 6항목: 오늘 뷰/빠른 추가/카드 액션/탭 전환/사이드바 부재/CSS]

전 시나리오 UI(streamlit.testing.v1.AppTest) 경유. DB는 conftest 의 FakeSupabase.
골든(분류) 테스트는 core.models 를 시각 고정(monkeypatch)으로 검증 — 1-A와 동일.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import DUMMY_SECRETS

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = json.loads((ROOT / "tests" / "golden_classification.json").read_text(encoding="utf-8"))


def _make_apptest() -> AppTest:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    for k, v in DUMMY_SECRETS.items():
        at.secrets[k] = v
    return at


def _login(at: AppTest) -> AppTest:
    at.run()
    at.text_input(key="pwd_input").input(DUMMY_SECRETS["APP_PASSWORD"])
    next(b for b in at.button if "로그인" in (b.label or "")).click()
    at.run()
    assert at.session_state["authenticated"] is True
    return at


def _goto(at: AppTest, tab: str) -> AppTest:
    at.segmented_control(key="nav").set_value(tab)
    at.run()
    return at


def _all_markdown(at: AppTest) -> str:
    return "\n".join(str(m.value) for m in at.markdown)


# ── [1-A 1] 앱 부팅: 예외 없이 렌더 + 인증 게이트 ─────────────────
def test_boot_shows_auth_gate(fake_db):
    at = _make_apptest()
    at.run()
    assert not at.exception
    assert at.text_input(key="pwd_input") is not None
    assert "My AI Desk" in _all_markdown(at)
    assert "기한초과 업무" not in _all_markdown(at)


def test_wrong_password_rejected(fake_db):
    at = _make_apptest()
    at.run()
    at.text_input(key="pwd_input").input("wrong")
    next(b for b in at.button if "로그인" in (b.label or "")).click()
    at.run()
    assert at.session_state["authenticated"] is False
    assert len(at.error) >= 1


# ── [1-A 2] 인증 통과 → 태스크 목록 렌더 (전체 탭) ────────────────
def test_task_list_renders(fake_db):
    fake, seed = fake_db
    at = _login(_make_apptest())
    _goto(at, "전체")
    assert not at.exception
    body = _all_markdown(at)
    for t in seed["tasks"]:
        if not t["is_completed"]:
            assert t["title"] in body, f"'{t['title']}' 미렌더"


# ── [1-A 3] 폼 등록 → insert 호출 (source='form' 유지) ────────────
def test_add_task_calls_insert(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    _goto(at, "전체")
    title_box = next(w for w in at.text_input if (w.label or "").startswith("업무명"))
    title_box.input("새 스모크 업무")
    next(b for b in at.button if "업무 등록" in (b.label or "")).click()
    at.run()
    assert not at.exception
    inserts = fake.calls_of("tasks", "insert")
    assert len(inserts) == 1
    payload = inserts[0]["payload"]
    assert payload["title"] == "새 스모크 업무"
    assert payload["is_completed"] is False
    assert payload["priority"] == "중간"
    assert payload["timer_started_at"]
    assert payload["source"] == "form"  # 기존 폼 경로는 'form' 유지 (§4)


# ── [1-A 4] 완료 → update 호출 (전체 탭 경로) ─────────────────────
def test_complete_task_calls_update(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    _goto(at, "전체")
    at.button(key="quick_전체_1").click()
    at.run()
    assert not at.exception
    updates = [c for c in fake.calls_of("tasks", "update")
               if c["payload"].get("is_completed") is True]
    assert len(updates) == 1
    assert updates[0]["payload"]["completed_at"]
    assert ("eq", "id", 1) in updates[0]["filters"]
    assert not fake.calls_of("tasks", "insert")


# ── [1-A 5] 삭제 → delete 호출 ────────────────────────────────────
def test_delete_task_calls_delete(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    _goto(at, "전체")
    at.button(key="del_전체_1").click()
    at.run()
    assert not at.exception
    deletes = fake.calls_of("tasks", "delete")
    assert len(deletes) == 1
    assert ("eq", "id", 1) in deletes[0]["filters"]


# ── [1-A 6] 메모 CRUD (메모 탭) ───────────────────────────────────
def test_memo_crud(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    _goto(at, "메모")
    body = _all_markdown(at)
    assert "고정된 메모" in body and "일반 메모" in body  # Read

    memo_box = at.text_area(key="memo_input")
    memo_box.input("스모크 메모")
    next(b for b in at.button if "저장" in (b.label or "")).click()
    at.run()
    assert not at.exception
    inserts = fake.calls_of("memos", "insert")
    assert len(inserts) == 1 and inserts[0]["payload"]["content"] == "스모크 메모"

    at.button(key="pin_12").click()
    at.run()
    ups = fake.calls_of("memos", "update")
    assert len(ups) == 1 and ups[0]["payload"] == {"pinned": True}

    at.button(key="del_memo_11").click()
    at.run()
    dels = fake.calls_of("memos", "delete")
    assert len(dels) == 1 and ("eq", "id", 11) in dels[0]["filters"]


# ── [1-A 7] 분류 로직 골든 (core.models — 무손상 확인) ────────────
def test_classification_golden(fake_db):
    import core.models as m
    frozen = datetime.fromisoformat(GOLDEN["frozen_now"])
    m_now, m.now_kst = m.now_kst, (lambda: frozen)
    try:
        fns = {name: getattr(m, name) for name in (
            "get_urgency", "calc_checklist_progress", "parse_tags",
            "get_next_recurrence_date", "format_minutes", "calc_duration",
            "calc_duration_minutes", "build_task_date_map",
            "build_weekly_report", "build_monthly_report")}
        for case in GOLDEN["get_urgency"]:
            assert list(fns["get_urgency"](case["input"])) == case["output"], case
        for case in GOLDEN["calc_checklist_progress"]:
            got = fns["calc_checklist_progress"](case["input"])
            assert (list(got) if got else None) == case["output"], case
        for case in GOLDEN["parse_tags"]:
            assert sorted(fns["parse_tags"](case["input"])) == sorted(case["output"]), case
        for case in GOLDEN["get_next_recurrence_date"]:
            d = datetime.fromisoformat(case["input"][0])
            assert fns["get_next_recurrence_date"](d, case["input"][1]).isoformat() == case["output"], case
        for case in GOLDEN["format_minutes"]:
            assert fns["format_minutes"](case["input"]) == case["output"], case
        for case in GOLDEN["calc_duration"]:
            assert fns["calc_duration"](*case["input"]) == case["output"], case
        for case in GOLDEN["calc_duration_minutes"]:
            assert fns["calc_duration_minutes"](*case["input"]) == case["output"], case
        g = GOLDEN["build_task_date_map"]
        got_map = fns["build_task_date_map"](g["input"])
        assert {k: [t["id"] for t in v] for k, v in got_map.items()} == g["output"]
        completed = [t for t in GOLDEN["sample_tasks"] if t["is_completed"]]
        assert fns["build_weekly_report"](completed, GOLDEN["sample_tasks"]) == GOLDEN["build_weekly_report"]["output"]
        assert fns["build_monthly_report"](completed, GOLDEN["sample_tasks"]) == GOLDEN["build_monthly_report"]["output"]
    finally:
        m.now_kst = m_now


# ══ Phase 2 신규 (§6-2) ══════════════════════════════════════════

# ── ① 오늘 뷰 렌더 + 분류 섹션 표시 (기본 랜딩) ───────────────────
def test_today_view_sections(fake_db):
    from core.models import split_today_sections
    fake, seed = fake_db
    at = _login(_make_apptest())  # 기본 랜딩 = 오늘
    assert not at.exception
    body = _all_markdown(at)
    active = [t for t in seed["tasks"] if not t["is_completed"]]
    expected = split_today_sections(active)
    labels = {"overdue": "기한 초과", "today": "오늘 마감", "soon": "3일 이내"}
    for key, label in labels.items():
        if expected[key]:
            assert label in body, f"섹션 '{label}' 미표시"
            for t in expected[key]:
                assert t["title"] in body
    # 무기한 등 나머지는 expander 로
    if expected["rest"]:
        assert any("나머지 업무" in (e.label or "") for e in at.expander)
    # 통계 카드(구 dashboard 흡수) 표시
    for stat_label in ("진행 중", "기한 초과", "오늘 마감", "오늘 완료"):
        assert stat_label in body


# ── ② 빠른 추가 → source='quick' + 오늘 23:59 기본 기한 ──────────
def test_quick_add_source_quick(fake_db):
    from core.models import now_kst
    fake, _ = fake_db
    at = _login(_make_apptest())
    at.text_input(key="quick_add_input").input("빠른 스모크 업무")
    next(b for b in at.button if (b.label or "").strip() == "추가").click()
    at.run()
    assert not at.exception
    inserts = fake.calls_of("tasks", "insert")
    assert len(inserts) == 1
    payload = inserts[0]["payload"]
    assert payload["title"] == "빠른 스모크 업무"
    assert payload["source"] == "quick"
    dl = datetime.fromisoformat(payload["deadline"])
    assert dl.strftime("%H:%M") == "23:59"
    assert dl.date() == now_kst().date()
    assert payload["category"] == "기타" and payload["priority"] == "중간"


# ── ③ 오늘 뷰 카드 액션: [완료 ✓] / [내일로 →] ───────────────────
def test_today_complete_action(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    at.button(key="today_done_1").click()
    at.run()
    assert not at.exception
    updates = [c for c in fake.calls_of("tasks", "update")
               if c["payload"].get("is_completed") is True]
    assert len(updates) == 1
    assert ("eq", "id", 1) in updates[0]["filters"]


def test_today_postpone_action(fake_db):
    fake, seed = fake_db
    at = _login(_make_apptest())
    orig = datetime.fromisoformat(seed["tasks"][1]["deadline"])  # id=2 (오늘 마감)
    at.button(key="today_postpone_2").click()
    at.run()
    assert not at.exception
    ups = [c for c in fake.calls_of("tasks", "update") if "deadline" in c["payload"]]
    assert len(ups) == 1
    assert ("eq", "id", 2) in ups[0]["filters"]
    new_dl = datetime.fromisoformat(ups[0]["payload"]["deadline"])
    assert new_dl - orig == timedelta(days=1)


# ── ④ 탭 전환: 4개 화면 모두 렌더 ─────────────────────────────────
def test_nav_all_tabs_render(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    signatures = {
        "오늘": "오늘 마감",
        "전체": "업무 목록",
        "메모": "퀵 메모",
        "분석": "업무 현황",
    }
    for tab, signature in signatures.items():
        _goto(at, tab)
        assert not at.exception, f"[{tab}] 탭 예외"
        assert signature in _all_markdown(at), f"[{tab}] 탭 시그니처 '{signature}' 미표시"


# ── ⑤ 사이드바 미사용 ─────────────────────────────────────────────
def test_no_sidebar_usage(fake_db):
    sources = [ROOT / "app.py"] + sorted((ROOT / "ui").glob("*.py"))
    for f in sources:
        assert "st.sidebar" not in f.read_text(encoding="utf-8"), f"{f.name} 에 st.sidebar 잔존"
    at = _login(_make_apptest())
    assert len(at.sidebar.markdown) == 0 and len(at.sidebar.button) == 0


# ── ⑥ CSS: 폰트 정책(Phase 2.1) — Pretendard 부재 + 헤딩 세리프 스택 존재 ──
def test_css_design_system():
    css_src = (ROOT / "ui" / "components.py").read_text(encoding="utf-8")
    # 웹폰트 로드 없음: Pretendard CDN/선언 부재, 깨진 @font-face 부재 유지
    assert "pretendard" not in css_src.lower()
    assert "@font-face" not in css_src
    assert "@import" not in css_src
    assert "Noto+Serif" not in css_src and "Noto Serif" not in css_src
    # 헤딩은 명시적 세리프 스택 (현재 폴백 룩의 의도적 승격)
    assert "--font-serif: Georgia, 'Times New Roman', serif;" in css_src
    for heading_cls in (".app-header h1", ".section-header", ".stat-number", ".task-title", ".login-wrap h1"):
        idx = css_src.index(heading_cls)
        assert "var(--font-serif)" in css_src[idx:idx + 300], f"{heading_cls} 세리프 미적용"
    # 본문·버튼은 시스템 산세리프 스택
    assert "--font-sans: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;" in css_src
    # 액센트·no-shadow 정책 유지
    assert "#2563EB" in css_src
    assert "text-shadow" not in css_src
    # 다른 모듈에 개별 폰트 선언이 새지 않아야(변수 참조만 허용)
    for f in [ROOT / "app.py"] + sorted((ROOT / "ui").glob("*.py")):
        if f.name == "components.py":
            continue
        src = f.read_text(encoding="utf-8")
        assert "Georgia" not in src and "Pretendard" not in src, f.name
