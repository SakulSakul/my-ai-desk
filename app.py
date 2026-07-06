"""My AI Desk — 엔트리포인트 [Phase 1-A 구조 분해].

역할: 페이지 설정 + 세션 초기화 + 인증 게이트 + 화면 라우팅.
로직은 core/(db·models), 화면은 ui/ 에 있다.
"""
import streamlit as st

from core.models import now_kst, get_urgency
# core.db import 시점에 Supabase 클라이언트가 생성된다(원본과 동일하게 set_page_config 이전).
from core.db import load_tasks, load_completed_tasks, load_completed_today_count
from ui.components import inject_css
from ui.sidebar import render_sidebar
from ui.dashboard import render_dashboard
from ui.analytics import render_analytics
from ui.calendar_view import render_calendar
from ui.tasks import render_task_form, render_task_list, render_completed_tasks

# ── 설정 ──
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

# ── 페이지 설정 ──
st.set_page_config(
    page_title="My AI Desk · CSR",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS 테마 ──
inject_css()


# ── 세션 상태 ──
def init_session_state():
    defaults = {
        "authenticated": False,
        "cal_year": now_kst().year, "cal_month": now_kst().month,
        "selected_date": None,
        "filter_category": "전체", "filter_priority": "전체",
        "filter_tag": "", "sort_by": "마감일순",
        "stat_filter": None,  # "active", "overdue", "today", "completed_today"
        "task_cat_tab": "전체",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()


# ── 비밀번호 잠금 ──
def check_password():
    if st.session_state.authenticated: return True
    st.markdown('<div class="login-wrap"><h1>My AI Desk</h1><p>CSR · Task Manager</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        pwd = st.text_input("비밀번호", type="password", key="pwd_input")
        if st.button("로그인", use_container_width=True, type="primary"):
            if pwd == APP_PASSWORD: st.session_state.authenticated = True; st.rerun()
            else: st.error("비밀번호가 틀렸습니다.")
    return False

if not check_password(): st.stop()


# ── 사이드바 ──
search_query = render_sidebar()

# ── 메인 헤더 ──
st.markdown('<div class="app-header"><div class="app-header-sub">CSR · Task Manager</div><h1>My AI Desk</h1></div>', unsafe_allow_html=True)

# ── 데이터 로드 ──
all_active = load_tasks(show_completed=False, search_query="", category="전체", priority="전체") or []
all_completed = load_completed_tasks(100) or []
completed_today = load_completed_today_count() or 0
overdue_count = sum(1 for t in all_active if get_urgency(t.get("deadline"))[0]=="overdue")
today_count = sum(1 for t in all_active if get_urgency(t.get("deadline"))[0]=="today")
total_active = len(all_active)
tts = today_count+completed_today
completion_rate = int(completed_today/tts*100) if tts>0 else 0

# ── 화면 라우팅 ──
render_dashboard(all_active, all_completed, completed_today, overdue_count, today_count, total_active)
render_analytics(all_active, all_completed)
render_calendar()
render_task_form()
render_task_list(search_query)
render_completed_tasks()
