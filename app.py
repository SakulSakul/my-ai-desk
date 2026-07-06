"""My AI Desk — 엔트리포인트 [Phase 2: 모바일 우선 상단 내비].

역할: 페이지 설정 + 세션 초기화 + 인증 게이트 + 상단 내비([오늘][전체][메모][분석]) 라우팅.
로직은 core/(db·models), 화면은 ui/ 에 있다. 사이드바는 사용하지 않는다.
"""
import streamlit as st

from core.models import now_kst
# core.db import 시점에 Supabase 클라이언트가 생성된다(set_page_config 이전).
import core.db  # noqa: F401
from ui.components import inject_css
from ui.today import render_today
from ui.tasks import render_all_tab
from ui.memos import render_memos
from ui.analytics import render_analytics_tab

# ── 설정 ──
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

# ── 페이지 설정 ──
st.set_page_config(
    page_title="My AI Desk",
    page_icon="🗂️",
    layout="wide",
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


# ── 메인 헤더 ──
st.markdown('<div class="app-header"><div class="app-header-sub">CSR · Task Manager</div><h1>My AI Desk</h1></div>', unsafe_allow_html=True)

# ── 상단 내비 ──
NAV_ITEMS = ["오늘", "전체", "메모", "분석"]
nav = st.segmented_control("메뉴", NAV_ITEMS, default="오늘", key="nav", label_visibility="collapsed") or "오늘"

# ── 화면 라우팅 ──
if nav == "오늘":
    render_today()
elif nav == "전체":
    render_all_tab()
elif nav == "메모":
    render_memos()
else:
    render_analytics_tab()
