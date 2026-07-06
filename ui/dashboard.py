"""ui/dashboard.py — 통계 카드/통계 필터/오늘의 포커스 [Phase 1-A, app.py 에서 순수 이동]."""
import streamlit as st

from core.models import PRIORITIES, now_kst, format_dt, get_urgency
from core.db import complete_task


def render_dashboard(all_active, all_completed, completed_today, overdue_count, today_count, total_active):
    st.markdown(f'<div class="stat-grid"><div class="stat-box"><div class="stat-number" style="color:var(--black);">{total_active}</div><div class="stat-label">진행 중</div></div><div class="stat-box"><div class="stat-number" style="color:var(--red);">{overdue_count}</div><div class="stat-label">기한 초과</div></div><div class="stat-box"><div class="stat-number" style="color:var(--orange);">{today_count}</div><div class="stat-label">오늘 마감</div></div><div class="stat-box"><div class="stat-number" style="color:var(--green);">{completed_today}</div><div class="stat-label">오늘 완료</div></div></div>', unsafe_allow_html=True)

    # 통계 필터 버튼
    stc1, stc2, stc3, stc4, stc5 = st.columns(5)
    with stc1:
        if st.button("📋 진행 중", use_container_width=True, disabled=st.session_state.stat_filter=="active"):
            st.session_state.stat_filter = "active" if st.session_state.stat_filter != "active" else None; st.rerun()
    with stc2:
        if st.button("🚨 기한 초과", use_container_width=True, disabled=st.session_state.stat_filter=="overdue"):
            st.session_state.stat_filter = "overdue" if st.session_state.stat_filter != "overdue" else None; st.rerun()
    with stc3:
        if st.button("⚡ 오늘 마감", use_container_width=True, disabled=st.session_state.stat_filter=="today"):
            st.session_state.stat_filter = "today" if st.session_state.stat_filter != "today" else None; st.rerun()
    with stc4:
        if st.button("✅ 오늘 완료", use_container_width=True, disabled=st.session_state.stat_filter=="completed_today"):
            st.session_state.stat_filter = "completed_today" if st.session_state.stat_filter != "completed_today" else None; st.rerun()
    with stc5:
        if st.session_state.stat_filter:
            if st.button("✕ 필터 해제", use_container_width=True):
                st.session_state.stat_filter = None; st.rerun()

    # 통계 필터 결과 표시
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
                sf_card = (
                    f'<div class="task-card {cls}"><div class="task-header">'
                    f'<span class="task-title"{title_style}>{pi} {t["title"]}</span>'
                    f'<div class="task-badges"><span class="badge">{cat}</span></div>'
                    f'</div><div class="task-meta">'
                    f'<span>{dl_span}</span>{urg_span}{done_span}'
                    f'</div></div>'
                )
                st.markdown(sf_card, unsafe_allow_html=True)
        else:
            st.caption("해당 업무가 없습니다.")
        st.markdown("---")


    # ============================================
    # 🎯 오늘의 포커스 (기한초과 + 오늘마감)
    # ============================================
    focus_tasks = [t for t in all_active if get_urgency(t.get("deadline"))[0] in ("overdue", "today")]
    if focus_tasks:
        st.markdown('<div class="section-header-light">지금 당장</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-header">🎯 오늘의 포커스 ({len(focus_tasks)}건)</div>', unsafe_allow_html=True)

        for task in focus_tasks:
            urgency, urgency_label = get_urgency(task.get("deadline"))
            pi = PRIORITIES.get(task.get("priority","중간"),"")
            cat = task.get("category","기타")

            card = (f'<div class="task-card {urgency}"><div class="task-header"><span class="task-title">{pi} {task["title"]}</span><div class="task-badges"><span class="badge badge-priority-{task.get("priority","중간")}">{task.get("priority","중간")}</span><span class="badge">{cat}</span></div></div><div class="task-meta"><span>📅 {format_dt(task["deadline"])}</span><span class="urgency-tag urgency-{urgency}">{urgency_label}</span></div></div>')
            st.markdown(card, unsafe_allow_html=True)

            # 원클릭 완료
            fc1, fc2 = st.columns([1, 5])
            with fc1:
                if st.button("✅", key=f"focus_done_{task['id']}", help="완료 처리"):
                    complete_task(task)
                    st.toast("🎉 수고하셨습니다!")
                    st.balloons(); st.rerun()

        st.markdown("---")
