"""ui/today.py — [오늘] 탭: 기본 랜딩 [Phase 2 신규].

구 ui/dashboard.py 를 흡수:
- 통계 카드 + 상태별 필터: 동일 기능 유지 (session_state.stat_filter)
- '오늘의 포커스'(기한초과+오늘마감 목록 + 원클릭 완료): 아래 섹션 분류가
  상위 호환으로 대체(같은 집합 + [내일로] 액션 추가)
섹션 분류는 core.models.split_today_sections — 아침 브리핑과 동일 규칙(KST).
카드 액션(완료/내일로)은 fragment 스코프 리런으로 전체 리런 없이 반영.
"""
import streamlit as st
from streamlit.errors import StreamlitAPIException
from datetime import datetime, timedelta, time as dt_time

from core.models import (
    KST, PRIORITIES, now_kst, format_dt, parse_deadline_kst, get_urgency,
    split_today_sections,
)
from core.db import (
    load_tasks, load_completed_tasks, load_completed_today_count,
    complete_task, postpone_task, add_task,
)


def _render_quick_add():
    """빠른 추가 (오늘 뷰 최상단 고정) — 한 줄 입력 + Enter/버튼 제출 [Phase 2 §4].

    비-LLM 최소 파싱: 제목 그대로 저장. 기한은 '오늘 23:59(KST)' 기본 —
    오늘 뷰에서 추가한 항목이 곧바로 '오늘 마감' 섹션에 보이도록(재량 결정, PR 기록).
    카테고리/우선순위는 기존 폼 기본값 관례(기타/중간). source='quick' 기록.
    """
    with st.form("quick_add_form", clear_on_submit=True, border=False):
        qc1, qc2 = st.columns([4, 1])
        with qc1:
            title = st.text_input("빠른 추가", placeholder="⚡ 할 일 입력 후 Enter — 오늘 23:59 마감으로 등록",
                                  label_visibility="collapsed", key="quick_add_input")
        with qc2:
            submitted = st.form_submit_button("추가", use_container_width=True, type="primary")
    if submitted and title.strip():
        deadline = datetime.combine(now_kst().date(), dt_time(23, 59), tzinfo=KST)
        add_task(title.strip(), "", deadline, "기타", "중간", None, "", source="quick")
        st.toast("✅ 추가!")
        _refresh()

_SECTIONS = [
    ("overdue", "🚨 기한 초과"),
    ("today", "📌 오늘 마감"),
    ("soon", "📅 3일 이내"),
]


def _refresh():
    """fragment 스코프 리런, fragment 리런 문맥이 아니면(전체 실행·AppTest) 전체 리런 폴백.

    scope='fragment' 는 fragment 리런 중에만 허용된다. 성공 시 발생하는
    RerunException 은 BaseException 직계라 아래 except 에 잡히지 않는다.
    """
    try:
        st.rerun(scope="fragment")
    except StreamlitAPIException:
        st.rerun()


def _tomorrow_deadline(task):
    """[내일로] 대상 기한: 기존 기한 +1일, 무기한이면 내일 23:59(KST)."""
    dl = parse_deadline_kst(task.get("deadline"))
    if dl:
        return dl + timedelta(days=1)
    return datetime.combine(now_kst().date() + timedelta(days=1), dt_time(23, 59), tzinfo=KST)


def _render_task_card(task):
    """카드: 제목 + 중요표시(우선순위) + 상대 기한 + 카드 내장 [완료 ✓][내일로 →].

    st.container(key="tcard_<urgency>_<id>") 가 st-key-* 클래스를 얻으므로,
    components.py 의 [class*="st-key-tcard_"] CSS 가 컨테이너 자체를 카드로 그린다.
    버튼은 카드 내부에서 컴팩트 아웃라인(각 ~160px, 전폭 금지) — 상세는 CSS 참조.
    """
    urgency, urgency_label = get_urgency(task.get("deadline"))
    pri = task.get("priority", "중간")
    cat = task.get("category", "기타")
    dl_span = ("📅 " + format_dt(task["deadline"])) if task.get("deadline") else "📅 마감일 미지정"
    urg_html = f'<span class="urgency-tag urgency-{urgency}">{urgency_label}</span>' if urgency_label else ""
    with st.container(key=f"tcard_{urgency}_{task['id']}"):
        st.markdown(
            f'<div class="task-header">'
            f'<span class="task-title">{task["title"]}</span>'
            f'<div class="task-badges"><span class="badge badge-priority-{pri}">{pri}</span><span class="badge badge-cat-{cat}">{cat}</span></div>'
            f'</div><div class="task-meta"><span>{dl_span}</span>{urg_html}</div>',
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("완료 ✓", key=f"today_done_{task['id']}", use_container_width=True):
                complete_task(task)
                st.toast("🎉 수고하셨습니다!")
                _refresh()
        with b2:
            if st.button("내일로 →", key=f"today_postpone_{task['id']}", use_container_width=True):
                postpone_task(task["id"], _tomorrow_deadline(task))
                st.toast("📅 내일로 미뤘습니다")
                _refresh()


def _render_stat_filter(all_active, all_completed):
    """상태별 필터 버튼 + 결과 목록 (구 dashboard 동일 기능)."""
    stc1, stc2, stc3, stc4, stc5 = st.columns(5)
    with stc1:
        if st.button("📋 진행 중", use_container_width=True, disabled=st.session_state.stat_filter=="active"):
            st.session_state.stat_filter = "active" if st.session_state.stat_filter != "active" else None; _refresh()
    with stc2:
        if st.button("🚨 기한 초과", use_container_width=True, disabled=st.session_state.stat_filter=="overdue"):
            st.session_state.stat_filter = "overdue" if st.session_state.stat_filter != "overdue" else None; _refresh()
    with stc3:
        if st.button("⚡ 오늘 마감", use_container_width=True, disabled=st.session_state.stat_filter=="today"):
            st.session_state.stat_filter = "today" if st.session_state.stat_filter != "today" else None; _refresh()
    with stc4:
        if st.button("✅ 오늘 완료", use_container_width=True, disabled=st.session_state.stat_filter=="completed_today"):
            st.session_state.stat_filter = "completed_today" if st.session_state.stat_filter != "completed_today" else None; _refresh()
    with stc5:
        if st.session_state.stat_filter:
            if st.button("✕ 필터 해제", use_container_width=True):
                st.session_state.stat_filter = None; _refresh()

    if st.session_state.stat_filter:
        sf = st.session_state.stat_filter
        if sf == "active":
            sf_tasks = all_active
            sf_label = f"📋 진행 중 업무 ({len(sf_tasks)}건)"
        elif sf == "overdue":
            sf_tasks = [t for t in all_active if get_urgency(t.get("deadline"))[0] == "overdue"]
            sf_label = f"🚨 기한 초과 업무 ({len(sf_tasks)}건)"
        elif sf == "today":
            sf_tasks = [t for t in all_active if get_urgency(t.get("deadline"))[0] == "today"]
            sf_label = f"⚡ 오늘 마감 업무 ({len(sf_tasks)}건)"
        elif sf == "completed_today":
            today_start = now_kst().replace(hour=0, minute=0, second=0).isoformat()
            sf_tasks = [t for t in all_completed if t.get("completed_at") and t["completed_at"] >= today_start]
            sf_label = f"✅ 오늘 완료한 업무 ({len(sf_tasks)}건)"
        else:
            sf_tasks = []; sf_label = ""

        st.markdown(f'<div class="section-header">{sf_label}</div>', unsafe_allow_html=True)
        if sf_tasks:
            for t in sf_tasks:
                u, ul = get_urgency(t.get("deadline"))
                pi = PRIORITIES.get(t.get("priority","중간"),"")
                cat = t.get("category","기타")
                is_done = t.get("is_completed", False)
                cls = "completed-card" if is_done else u
                title_style = ' style="text-decoration:line-through;"' if is_done else ""
                urg_span = f'<span class="urgency-tag urgency-{u}">{ul}</span>' if ul else ""
                done_span = f" · 완료: {format_dt(t['completed_at'])}" if is_done else ""
                dl_span = ("📅 " + format_dt(t["deadline"])) if t.get("deadline") else ""
                st.markdown(
                    f'<div class="task-card {cls}"><div class="task-header">'
                    f'<span class="task-title"{title_style}>{pi} {t["title"]}</span>'
                    f'<div class="task-badges"><span class="badge">{cat}</span></div>'
                    f'</div><div class="task-meta"><span>{dl_span}</span>{urg_span}{done_span}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("해당 업무가 없습니다.")
        st.markdown("---")


@st.fragment
def _today_fragment():
    # ── 빠른 추가 (최상단 고정) ──
    _render_quick_add()

    # 데이터 로드는 fragment 내부 — 카드 액션 후 fragment 리런만으로 최신화된다.
    all_active = load_tasks(show_completed=False, search_query="", category="전체", priority="전체") or []
    all_completed = load_completed_tasks(100) or []
    completed_today = load_completed_today_count() or 0
    sections = split_today_sections(all_active)
    overdue_count, today_count = len(sections["overdue"]), len(sections["today"])
    total_active = len(all_active)

    # ── 통계 카드 (구 dashboard 흡수) ──
    st.markdown(
        f'<div class="stat-grid">'
        f'<div class="stat-box"><div class="stat-number" style="color:var(--black);">{total_active}</div><div class="stat-label">진행 중</div></div>'
        f'<div class="stat-box"><div class="stat-number" style="color:var(--red);">{overdue_count}</div><div class="stat-label">기한 초과</div></div>'
        f'<div class="stat-box"><div class="stat-number" style="color:var(--orange);">{today_count}</div><div class="stat-label">오늘 마감</div></div>'
        f'<div class="stat-box"><div class="stat-number" style="color:var(--green);">{completed_today}</div><div class="stat-label">오늘 완료</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _render_stat_filter(all_active, all_completed)

    # ── 오늘 섹션 ──
    if not (sections["overdue"] or sections["today"] or sections["soon"]):
        st.markdown(
            '<div class="empty-state">📋 오늘 처리할 업무가 없습니다.<br>여유로운 하루 보내세요! 🎉</div>',
            unsafe_allow_html=True,
        )
    else:
        for key, label in _SECTIONS:
            group = sections[key]
            if not group:
                continue
            st.markdown(f'<div class="section-header">{label} ({len(group)}건)</div>', unsafe_allow_html=True)
            for task in group:
                _render_task_card(task)

    if sections["rest"]:
        with st.expander(f"진행 중인 나머지 업무 ({len(sections['rest'])}건)", expanded=False):
            for task in sections["rest"]:
                _render_task_card(task)


def render_today():
    _today_fragment()
