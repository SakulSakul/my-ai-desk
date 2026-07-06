"""Phase 1-A 자동 스모크 테스트 (§4 체크리스트 7항목).

전 시나리오를 UI(streamlit.testing.v1.AppTest) 경유로 구동한다 —
리팩터 전(단일 app.py)과 후(core/ + ui/)에 '같은 테스트'가 그대로 통과해야
순수 이동이 증명되기 때문이다. DB는 conftest 의 FakeSupabase 로 대체.

골든(7번) 테스트는 core/models.py 가 있으면 그것을, 없으면(기준선 시점)
app.py 원본에서 AST 로 추출한 함수를 대상으로 실행한다.
"""
from __future__ import annotations

import json
from datetime import datetime
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
    login_btn = next(b for b in at.button if "로그인" in (b.label or ""))
    login_btn.click()
    at.run()
    assert at.session_state["authenticated"] is True
    return at


def _all_markdown(at: AppTest) -> str:
    return "\n".join(str(m.value) for m in at.markdown)


# ── 1. 앱 부팅: 예외 없이 렌더 + 인증 게이트 표시 ──────────────────
def test_boot_shows_auth_gate(fake_db):
    at = _make_apptest()
    at.run()
    assert not at.exception
    assert at.text_input(key="pwd_input") is not None
    assert "My AI Desk" in _all_markdown(at)
    # 인증 전에는 업무 데이터가 노출되지 않아야 한다
    assert "기한초과 업무" not in _all_markdown(at)


def test_wrong_password_rejected(fake_db):
    at = _make_apptest()
    at.run()
    at.text_input(key="pwd_input").input("wrong")
    next(b for b in at.button if "로그인" in (b.label or "")).click()
    at.run()
    assert at.session_state["authenticated"] is False
    assert len(at.error) >= 1


# ── 2. 인증 통과 → 태스크 목록 렌더 ────────────────────────────────
def test_task_list_renders(fake_db):
    fake, seed = fake_db
    at = _login(_make_apptest())
    assert not at.exception
    body = _all_markdown(at)
    for t in seed["tasks"]:
        if not t["is_completed"]:
            assert t["title"] in body, f"'{t['title']}' 미렌더"
    # 사이드바 메모 렌더 (Read)
    assert "고정된 메모" in body and "일반 메모" in body


# ── 3. 태스크 추가 → insert 가 올바른 인자로 호출 ─────────────────
def test_add_task_calls_insert(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    title_box = next(w for w in at.text_input if (w.label or "").startswith("업무명"))
    title_box.input("새 스모크 업무")
    submit = next(b for b in at.button if "업무 등록" in (b.label or ""))
    submit.click()
    at.run()
    assert not at.exception
    inserts = fake.calls_of("tasks", "insert")
    assert len(inserts) == 1
    payload = inserts[0]["payload"]
    assert payload["title"] == "새 스모크 업무"
    assert payload["is_completed"] is False
    assert payload["category"] in ("공정거래", "동반성장", "사회공헌", "환경", "기타")
    assert payload["priority"] == "중간"
    assert payload["timer_started_at"]  # 등록 시 타이머 시작 기록(현재 코드 동작)
    # 참고: 현재 코드에 source='form' 필드는 없음 — §7-2 관찰 기록 대상


# ── 4. 태스크 완료 → update 호출 ──────────────────────────────────
def test_complete_task_calls_update(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    at.button(key="quick_전체_1").click()
    at.run()
    assert not at.exception
    updates = [c for c in fake.calls_of("tasks", "update")
               if c["payload"].get("is_completed") is True]
    assert len(updates) == 1
    assert updates[0]["payload"]["completed_at"]
    assert ("eq", "id", 1) in updates[0]["filters"]
    # 반복 없음 → 다음 회차 insert 가 생기면 안 된다
    assert not fake.calls_of("tasks", "insert")


# ── 5. 태스크 삭제 → delete 호출 ──────────────────────────────────
def test_delete_task_calls_delete(fake_db):
    fake, _ = fake_db
    at = _login(_make_apptest())
    at.button(key="del_전체_1").click()
    at.run()
    assert not at.exception
    deletes = fake.calls_of("tasks", "delete")
    assert len(deletes) == 1
    assert ("eq", "id", 1) in deletes[0]["filters"]


# ── 6. 메모 CRUD 각 1회 ───────────────────────────────────────────
def test_memo_crud(fake_db):
    fake, _ = fake_db
    # Create
    at = _login(_make_apptest())
    memo_box = next(w for w in at.text_area if (w.placeholder or "").startswith("번뜩이는"))
    memo_box.input("스모크 메모")
    next(b for b in at.button if "저장" in (b.label or "")).click()
    at.run()
    assert not at.exception
    inserts = fake.calls_of("memos", "insert")
    assert len(inserts) == 1 and inserts[0]["payload"]["content"] == "스모크 메모"

    # Update (고정 토글)
    at.button(key="pin_12").click()
    at.run()
    ups = fake.calls_of("memos", "update")
    assert len(ups) == 1 and ups[0]["payload"] == {"pinned": True}

    # Delete
    at.button(key="del_memo_11").click()
    at.run()
    dels = fake.calls_of("memos", "delete")
    assert len(dels) == 1 and ("eq", "id", 11) in dels[0]["filters"]


# ── 7. 분류 로직 골든 테스트 ──────────────────────────────────────
def _classification_fns():
    """core.models 가 있으면 그것을(시각 고정 monkeypatch), 없으면 원본 app.py 에서 AST 추출."""
    frozen = datetime.fromisoformat(GOLDEN["frozen_now"])
    try:
        import core.models as m
        m_now, m.now_kst = m.now_kst, (lambda: frozen)
        fns = {name: getattr(m, name) for name in (
            "get_urgency", "calc_checklist_progress", "parse_tags",
            "get_next_recurrence_date", "format_minutes", "calc_duration",
            "calc_duration_minutes", "build_task_date_map",
            "build_weekly_report", "build_monthly_report")}
        return fns, (lambda: setattr(m, "now_kst", m_now))
    except ImportError:
        from generate_golden import extract_functions
        return extract_functions(ROOT / "app.py"), (lambda: None)


def test_classification_golden(fake_db):
    fns, restore = _classification_fns()
    try:
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
        restore()
