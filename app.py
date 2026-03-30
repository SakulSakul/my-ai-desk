import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta, timezone, time as dt_time, date as dt_date
import calendar
from typing import Optional
from collections import Counter, defaultdict
import re

# ============================================
# 설정
# ============================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "여기에_수파베이스_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "여기에_수파베이스_ANON_KEY")
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

KST = timezone(timedelta(hours=9))

CATEGORIES = ["전체", "공정거래", "동반성장", "사회공헌", "환경", "기타"]
CATEGORY_COLORS = {
    "공정거래": "#1a1a1a",
    "동반성장": "#c8a26e",
    "사회공헌": "#3a7d5c",
    "환경": "#4a90a4",
    "기타": "#8c8c8c",
}
CATEGORY_ICONS = {
    "공정거래": "⚖️",
    "동반성장": "🤝",
    "사회공헌": "💛",
    "환경": "🌿",
    "기타": "📁",
}
PRIORITIES = {"높음": "🔴", "중간": "🟡", "낮음": "🟢"}
PRIORITY_ORDER = {"높음": 0, "중간": 1, "낮음": 2}

RECURRENCE_OPTIONS = {
    "없음": None, "매일": "daily", "매주": "weekly",
    "격주": "biweekly", "매월": "monthly",
}

# ============================================
# Supabase 클라이언트
# ============================================
@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Supabase 연결 실패: {e}")
        return None

supabase = init_supabase()

# ============================================
# 페이지 설정
# ============================================
st.set_page_config(
    page_title="My AI Desk · CSR",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================
# CSS — 신세계 뉴스룸 디자인 테마
# 화이트 베이스, 블랙 타이포, 골드 악센트,
# 넓은 여백, 세리프 헤더, 세련된 보더라인
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&display=swap');
    @font-face {
        font-family: 'Pretendard';
        src: url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
    }
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

    :root {
        --font-serif: 'Noto Serif KR', Georgia, serif;
        --font-sans: 'Pretendard Variable', 'Pretendard', -apple-system, sans-serif;
        --black: #1a1a1a;
        --dark: #333333;
        --gray-800: #444444;
        --gray-600: #666666;
        --gray-400: #999999;
        --gray-200: #e0e0e0;
        --gray-100: #f5f5f5;
        --white: #ffffff;
        --gold: #c8a26e;
        --gold-light: #c8a26e15;
        --gold-hover: #b8925e;
        --red: #c0392b;
        --red-light: #c0392b12;
        --orange: #d4880f;
        --orange-light: #d4880f10;
        --green: #3a7d5c;
        --green-light: #3a7d5c10;
        --blue: #4a90a4;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.06);
        --shadow-lg: 0 8px 30px rgba(0,0,0,0.08);
        --radius: 2px;
        --radius-md: 4px;
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    html, body, [class*="css"] {
        font-family: var(--font-sans);
        color: var(--dark);
    }

    /* Streamlit 기본 스타일 오버라이드 */
    .block-container {
        padding-top: 3.5rem;
        max-width: 1100px;
    }
    .stApp > header { background: transparent; }

    /* ── 헤더 영역 ── */
    .app-header {
        border-bottom: 2px solid var(--black);
        padding-bottom: 1.2rem;
        margin-bottom: 1.5rem;
    }
    .app-header h1 {
        font-family: var(--font-serif);
        font-size: 1.8rem;
        font-weight: 900;
        color: var(--black);
        letter-spacing: -0.5px;
        margin: 0;
        line-height: 1.3;
    }
    .app-header-sub {
        font-family: var(--font-sans);
        font-size: 0.82rem;
        color: var(--gray-600);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 0.2rem;
    }

    /* ── 통계 카드 ── */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0;
        border-top: 1px solid var(--gray-200);
        border-bottom: 1px solid var(--gray-200);
        margin-bottom: 2rem;
    }
    .stat-box {
        padding: 1.2rem 1rem;
        text-align: center;
        border-right: 1px solid var(--gray-200);
        transition: var(--transition);
    }
    .stat-box:last-child { border-right: none; }
    .stat-box:hover { background: var(--gray-100); }
    .stat-number {
        font-family: var(--font-serif);
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
    }
    .stat-label {
        font-size: 0.72rem;
        color: var(--gray-400);
        margin-top: 0.4rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* ── 섹션 헤더 (뉴스룸 스타일) ── */
    .section-header {
        font-family: var(--font-serif);
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--black);
        border-bottom: 2px solid var(--black);
        padding-bottom: 0.6rem;
        margin: 2rem 0 1rem 0;
        letter-spacing: -0.3px;
    }
    .section-header-light {
        font-family: var(--font-sans);
        font-size: 0.75rem;
        color: var(--gray-400);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }

    /* ── 업무 카드 ── */
    .task-card {
        background: var(--white);
        border-bottom: 1px solid var(--gray-200);
        padding: 1rem 0.5rem;
        transition: var(--transition);
        position: relative;
    }
    .task-card:hover {
        background: var(--gray-100);
        padding-left: 1rem;
    }
    .task-card.overdue {
        border-left: 3px solid var(--red);
        background: var(--red-light);
        padding-left: 1rem;
    }
    .task-card.today {
        border-left: 3px solid var(--orange);
        background: var(--orange-light);
        padding-left: 1rem;
    }
    .task-card.upcoming { }
    .task-card.completed-card {
        opacity: 0.45;
    }
    .task-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.8rem;
    }
    .task-title {
        font-family: var(--font-serif);
        font-size: 1rem;
        font-weight: 600;
        color: var(--black);
        flex: 1;
        line-height: 1.5;
    }
    .task-badges {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex-shrink: 0;
        flex-wrap: wrap;
    }
    .badge {
        font-family: var(--font-sans);
        font-size: 0.65rem;
        padding: 2px 8px;
        border: 1px solid var(--gray-200);
        color: var(--gray-600);
        letter-spacing: 0.5px;
        white-space: nowrap;
    }
    .badge-priority-높음 { border-color: var(--red); color: var(--red); }
    .badge-priority-중간 { border-color: var(--gold); color: var(--gold-hover); }
    .badge-priority-낮음 { border-color: var(--green); color: var(--green); }
    .badge-tag {
        font-size: 0.63rem;
        padding: 1px 6px;
        border: 1px solid var(--blue);
        color: var(--blue);
    }
    .task-meta {
        font-size: 0.78rem;
        color: var(--gray-400);
        margin-top: 0.4rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem 1rem;
        align-items: center;
    }
    .urgency-tag { font-weight: 600; }
    .urgency-overdue { color: var(--red); }
    .urgency-today { color: var(--orange); }
    .progress-inline { display: inline-flex; align-items: center; gap: 0.3rem; }
    .progress-bar-mini {
        width: 50px; height: 3px; background: var(--gray-200);
        overflow: hidden;
    }
    .progress-bar-mini-fill { height: 100%; background: var(--gold); }
    .timer-active {
        display: inline-flex; align-items: center; gap: 0.3rem;
        border: 1px solid var(--red);
        padding: 1px 8px; font-size: 0.7rem; color: var(--red);
        font-weight: 600;
        animation: pulse-border 2s infinite;
    }
    @keyframes pulse-border {
        0%, 100% { border-color: #e0b0b0; }
        50% { border-color: var(--red); }
    }

    /* ── 차트 영역 ── */
    .chart-container {
        background: var(--white);
        border: 1px solid var(--gray-200);
        padding: 1.2rem;
    }
    .chart-bar-row {
        display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.6rem;
    }
    .chart-bar-label {
        font-size: 0.78rem; font-weight: 500; color: var(--gray-600);
        min-width: 75px; text-align: right; white-space: nowrap;
    }
    .chart-bar-track {
        flex: 1; height: 20px; background: var(--gray-100);
        overflow: hidden; display: flex;
    }
    .chart-bar-segment {
        height: 100%; transition: width 0.5s ease;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.65rem; color: var(--white); font-weight: 600; min-width: 0;
    }
    .chart-bar-count { font-size: 0.72rem; color: var(--gray-400); min-width: 30px; }

    /* ── 타임라인 ── */
    .timeline-item {
        display: flex; gap: 1rem; padding: 0.7rem 0;
        border-bottom: 1px solid var(--gray-100);
    }
    .timeline-date {
        font-size: 0.72rem; color: var(--gray-400); min-width: 75px;
        text-align: right; padding-top: 2px;
        font-variant-numeric: tabular-nums;
    }
    .timeline-content { flex: 1; }
    .timeline-title {
        font-family: var(--font-serif);
        font-size: 0.85rem; font-weight: 500; color: var(--black);
    }
    .timeline-detail { font-size: 0.72rem; color: var(--gray-400); }

    /* ── 리포트 ── */
    .report-grid {
        display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 0; margin-bottom: 1rem;
        border: 1px solid var(--gray-200);
    }
    .report-box {
        padding: 1rem; text-align: center;
        border-right: 1px solid var(--gray-200);
    }
    .report-box:last-child { border-right: none; }
    .report-number {
        font-family: var(--font-serif);
        font-size: 1.4rem; font-weight: 700;
    }
    .report-label { font-size: 0.68rem; color: var(--gray-400); letter-spacing: 1px; }

    /* ── 시간 차트 ── */
    .time-chart-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
    .time-chart-label { font-size: 0.75rem; min-width: 75px; text-align: right; color: var(--gray-600); white-space: nowrap; }
    .time-chart-bar {
        height: 16px; display: flex; align-items: center;
        padding: 0 6px; font-size: 0.65rem; color: var(--white); font-weight: 500;
        transition: width 0.5s ease;
    }

    /* ── 달력 ── */
    .cal-container {
        background: var(--white); border: 1px solid var(--gray-200);
        padding: 1.2rem;
    }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }
    .cal-dow {
        text-align: center; font-size: 0.7rem; font-weight: 600;
        color: var(--gray-400); padding: 0.4rem 0;
        letter-spacing: 1px;
    }
    .cal-dow-sun { color: var(--red); }
    .cal-dow-sat { color: var(--blue); }
    .cal-day {
        text-align: center; padding: 0.4rem 0.1rem;
        min-height: 2.8rem; font-size: 0.85rem;
        color: var(--gray-600); cursor: pointer;
        transition: var(--transition);
        font-variant-numeric: tabular-nums;
    }
    .cal-day:hover { background: var(--gold-light); }
    .cal-day-empty { cursor: default; }
    .cal-day-empty:hover { background: transparent; }
    .cal-day-today {
        background: var(--black); color: var(--white) !important; font-weight: 700;
    }
    .cal-day-today:hover { background: var(--dark); }
    .cal-day-selected { outline: 2px solid var(--gold); outline-offset: -2px; }
    .cal-day-sun { color: var(--red); }
    .cal-day-sat { color: var(--blue); }
    .cal-day-today.cal-day-sun, .cal-day-today.cal-day-sat { color: var(--white) !important; }
    .cal-dots { display: flex; justify-content: center; gap: 2px; margin-top: 2px; }
    .cal-dot { width: 4px; height: 4px; border-radius: 50%; }
    .cal-dot-overdue { background: var(--red); }
    .cal-dot-today { background: var(--orange); }
    .cal-dot-upcoming { background: var(--green); }
    .cal-dot-completed { background: var(--gray-400); }

    /* ── 주간 뷰 ── */
    .week-day-card {
        background: var(--white); border: 1px solid var(--gray-200);
        padding: 0.8rem; margin-bottom: 0.3rem;
    }
    .week-day-card-today {
        border-left: 3px solid var(--black);
        background: var(--gray-100);
    }
    .week-day-header {
        font-family: var(--font-serif);
        font-size: 0.82rem; font-weight: 600; color: var(--black);
        margin-bottom: 0.4rem;
    }
    .week-day-header-today { color: var(--black); }
    .week-task-item {
        font-size: 0.78rem; color: var(--gray-600); padding: 0.15rem 0;
        border-left: 2px solid var(--gray-200); padding-left: 0.6rem;
        margin-bottom: 0.2rem;
    }
    .week-task-item-overdue { border-left-color: var(--red); }
    .week-task-item-today { border-left-color: var(--orange); }
    .week-task-item-upcoming { border-left-color: var(--green); }
    .week-no-task { font-size: 0.75rem; color: var(--gray-400); font-style: italic; }

    /* ── 사이드바 ── */
    .memo-item {
        background: var(--white);
        border: 1px solid var(--gray-200);
        padding: 0.7rem; margin-bottom: 0.4rem;
        font-size: 0.82rem; color: var(--dark);
        transition: var(--transition);
    }
    .memo-item:hover { border-color: var(--gold); }
    .memo-time { font-size: 0.68rem; color: var(--gray-400); margin-top: 0.3rem; }

    .selected-date-header {
        font-family: var(--font-serif);
        font-size: 0.95rem; font-weight: 600; color: var(--black);
        padding: 0.5rem 0;
        border-bottom: 2px solid var(--black);
        margin-bottom: 0.5rem;
    }
    .filter-active {
        font-size: 0.78rem; color: var(--gold-hover);
        font-weight: 500;
    }

    /* ── 로그인 ── */
    .login-wrap {
        text-align: center; padding: 4rem 1rem;
    }
    .login-wrap h1 {
        font-family: var(--font-serif);
        font-size: 2rem; font-weight: 900; color: var(--black);
        letter-spacing: -0.5px;
    }
    .login-wrap p {
        color: var(--gray-400); font-size: 0.85rem;
        letter-spacing: 2px; text-transform: uppercase;
    }

    /* ── 버튼 ── */
    .stButton > button {
        border-radius: var(--radius-md);
        font-family: var(--font-sans);
    }

    /* ── 모바일 ── */
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem; }
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .stat-box:nth-child(2) { border-right: none; }
        .report-grid { grid-template-columns: 1fr; }
        .report-box { border-right: none; border-bottom: 1px solid var(--gray-200); }
        .report-box:last-child { border-bottom: none; }
        .stat-number { font-size: 1.6rem; }
        .app-header h1 { font-size: 1.4rem; }
        .cal-day { min-height: 2.2rem; font-size: 0.75rem; }
        .cal-dot { width: 3px; height: 3px; }
        .task-header { flex-direction: column; align-items: flex-start; }
        .task-badges { margin-top: 0.3rem; }
        .task-title { font-size: 0.92rem; }
        .section-header { font-size: 1rem; }
    }
    @media (max-width: 480px) {
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .chart-bar-label, .time-chart-label { min-width: 65px; font-size: 0.7rem; white-space: nowrap; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# 세션 상태 / 유틸
# ============================================
def now_kst() -> datetime:
    return datetime.now(KST)

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

def format_dt(dt_str: Optional[str]) -> str:
    if not dt_str: return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%m/%d(%a) %H:%M")
    except (ValueError, TypeError):
        return dt_str

def parse_deadline_kst(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str: return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(KST)
    except (ValueError, TypeError):
        return None

def get_urgency(deadline_str: Optional[str]) -> tuple[str, str]:
    if not deadline_str: return "upcoming", ""
    deadline = parse_deadline_kst(deadline_str)
    if not deadline: return "upcoming", ""
    now = now_kst()
    diff = deadline - now
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        overdue_hours = abs(total_seconds) / 3600
        if overdue_hours < 24:
            return "overdue", f"⏰ {int(overdue_hours)}시간 초과"
        return "overdue", f"⏰ {int(overdue_hours / 24)}일 초과"
    deadline_date = deadline.date()
    today_date = now.date()
    day_diff = (deadline_date - today_date).days
    if day_diff == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            return "today", f"⚡ {diff.seconds // 60}분 남음"
        return "today", f"⚡ {hours}시간 남음"
    elif day_diff == 1:
        return "upcoming", "📅 내일 마감"
    else:
        return "upcoming", f"📅 {day_diff}일 남음"

def calc_duration(created_str, completed_str):
    if not created_str or not completed_str: return ""
    try:
        c = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        d = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
        diff = d - c
        days, hours = diff.days, diff.seconds // 3600
        mins = (diff.seconds % 3600) // 60
        parts = []
        if days > 0: parts.append(f"{days}일")
        if hours > 0: parts.append(f"{hours}시간")
        if mins > 0: parts.append(f"{mins}분")
        return " ".join(parts) if parts else "1분 미만"
    except: return ""

def calc_duration_minutes(start_str, end_str):
    if not start_str or not end_str: return 0.0
    try:
        s = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        return max((e - s).total_seconds() / 60, 0)
    except: return 0.0

def format_minutes(mins):
    if mins < 1: return "1분 미만"
    h, m = int(mins // 60), int(mins % 60)
    if h > 0 and m > 0: return f"{h}시간 {m}분"
    elif h > 0: return f"{h}시간"
    return f"{m}분"

def calc_checklist_progress(description):
    if not description: return None
    total = checked = 0
    for line in description.split("\n"):
        s = line.strip()
        if s.startswith("- [ ]") or s.startswith("- [x]") or s.startswith("- [X]"):
            total += 1
            if s.startswith("- [x]") or s.startswith("- [X]"): checked += 1
    return (checked, total) if total > 0 else None

def parse_tags(tags_str):
    if not tags_str: return []
    cleaned = tags_str.replace("#", "")
    tags = re.split(r'[,\s]+', cleaned)
    return [t.strip() for t in tags if t.strip()]

def get_next_recurrence_date(current_deadline, recurrence):
    if recurrence == "daily": return current_deadline + timedelta(days=1)
    elif recurrence == "weekly": return current_deadline + timedelta(weeks=1)
    elif recurrence == "biweekly": return current_deadline + timedelta(weeks=2)
    elif recurrence == "monthly":
        month = current_deadline.month + 1
        year = current_deadline.year
        if month > 12: month, year = 1, year + 1
        day = min(current_deadline.day, calendar.monthrange(year, month)[1])
        return current_deadline.replace(year=year, month=month, day=day)
    return current_deadline


# ============================================
# DB 함수
# ============================================
def safe_db_call(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            st.error(f"데이터베이스 오류: {e}")
            return None
    return wrapper

@safe_db_call
def load_tasks(show_completed=False, search_query="", category="전체", priority="전체", tag_filter=""):
    query = supabase.table("tasks").select("*")
    if not show_completed: query = query.eq("is_completed", False)
    if category != "전체": query = query.eq("category", category)
    if priority != "전체": query = query.eq("priority", priority)
    query = query.order("deadline", desc=False)
    result = query.execute()
    tasks = result.data or []
    if search_query:
        q = search_query.lower()
        tasks = [t for t in tasks if q in (t.get("title") or "").lower() or q in (t.get("description") or "").lower() or q in (t.get("category") or "").lower() or q in (t.get("tags") or "").lower()]
    if tag_filter:
        tf = tag_filter.lower().replace("#", "").strip()
        tasks = [t for t in tasks if tf in (t.get("tags") or "").lower()]
    return tasks

@safe_db_call
def load_all_tasks():
    return (supabase.table("tasks").select("*").order("deadline", desc=False).execute()).data or []

@safe_db_call
def add_task(title, description, deadline, category, priority="중간", recurrence=None, tags=""):
    data = {"title": title, "description": description, "deadline": deadline.isoformat() if deadline else None, "category": category, "priority": priority, "recurrence": recurrence, "tags": tags, "is_completed": False, "timer_started_at": now_kst().isoformat()}
    supabase.table("tasks").insert(data).execute()

@safe_db_call
def complete_task(task):
    now = now_kst().isoformat()
    update_data = {"is_completed": True, "completed_at": now}
    if task.get("timer_started_at") and not task.get("timer_ended_at"):
        update_data["timer_ended_at"] = now
    supabase.table("tasks").update(update_data).eq("id", task["id"]).execute()
    recurrence = task.get("recurrence")
    if recurrence and task.get("deadline"):
        deadline = parse_deadline_kst(task["deadline"])
        if deadline:
            next_deadline = get_next_recurrence_date(deadline, recurrence)
            desc = (task.get("description") or "").replace("- [x]", "- [ ]").replace("- [X]", "- [ ]")
            add_task(task["title"], desc, next_deadline, task.get("category", "기타"), task.get("priority", "중간"), recurrence, task.get("tags", ""))

@safe_db_call
def uncomplete_task(task_id): supabase.table("tasks").update({"is_completed": False, "completed_at": None}).eq("id", task_id).execute()
@safe_db_call
def delete_task(task_id): supabase.table("tasks").delete().eq("id", task_id).execute()
@safe_db_call
def update_task(task_id, title, description, deadline, category, priority="중간", recurrence=None, tags=""):
    supabase.table("tasks").update({"title": title, "description": description, "deadline": deadline.isoformat() if deadline else None, "category": category, "priority": priority, "recurrence": recurrence, "tags": tags}).eq("id", task_id).execute()
@safe_db_call
def start_timer(task_id): supabase.table("tasks").update({"timer_started_at": now_kst().isoformat(), "timer_ended_at": None}).eq("id", task_id).execute()
@safe_db_call
def stop_timer(task_id): supabase.table("tasks").update({"timer_ended_at": now_kst().isoformat()}).eq("id", task_id).execute()
@safe_db_call
def reset_timer(task_id): supabase.table("tasks").update({"timer_started_at": None, "timer_ended_at": None}).eq("id", task_id).execute()
@safe_db_call
def load_memos(): return (supabase.table("memos").select("*").order("created_at", desc=True).limit(50).execute()).data or []
@safe_db_call
def add_memo(content, pinned=False): supabase.table("memos").insert({"content": content, "pinned": pinned}).execute()
@safe_db_call
def delete_memo(memo_id): supabase.table("memos").delete().eq("id", memo_id).execute()
@safe_db_call
def toggle_pin_memo(memo_id, pinned): supabase.table("memos").update({"pinned": not pinned}).eq("id", memo_id).execute()
@safe_db_call
def load_completed_today_count():
    r = supabase.table("tasks").select("id", count="exact").eq("is_completed", True).gte("completed_at", now_kst().replace(hour=0, minute=0, second=0).isoformat()).execute()
    return r.count or 0
@safe_db_call
def load_completed_tasks(limit=100): return (supabase.table("tasks").select("*").eq("is_completed", True).order("completed_at", desc=True).limit(limit).execute()).data or []
@safe_db_call
def load_all_tags():
    result = supabase.table("tasks").select("tags").execute()
    all_tags = []
    for row in (result.data or []): all_tags.extend(parse_tags(row.get("tags")))
    return list(set(all_tags))


# ============================================
# 달력/차트 헬퍼
# ============================================
def build_task_date_map(tasks):
    dm = {}
    for t in tasks:
        dl = parse_deadline_kst(t.get("deadline"))
        if dl: dm.setdefault(dl.strftime("%Y-%m-%d"), []).append(t)
    return dm

def render_monthly_calendar(year, month, task_date_map, today_str, selected_date=None):
    cal = calendar.Calendar(firstweekday=6)
    dow = ["일", "월", "화", "수", "목", "금", "토"]
    html = '<div class="cal-grid">'
    for i, d in enumerate(dow):
        cls = "cal-dow"
        if i == 0: cls += " cal-dow-sun"
        if i == 6: cls += " cal-dow-sat"
        html += f'<div class="{cls}">{d}</div>'
    for day, weekday in cal.itermonthdays2(year, month):
        if day == 0:
            html += '<div class="cal-day cal-day-empty"></div>'; continue
        dk = f"{year}-{month:02d}-{day:02d}"
        awd = (weekday + 1) % 7
        cls = "cal-day"
        if dk == today_str: cls += " cal-day-today"
        elif awd == 0: cls += " cal-day-sun"
        elif awd == 6: cls += " cal-day-sat"
        if dk == selected_date: cls += " cal-day-selected"
        dots = ""
        if dk in task_date_map:
            dd = []
            for t in task_date_map[dk][:3]:
                if t.get("is_completed"): dd.append('<span class="cal-dot cal-dot-completed"></span>')
                else:
                    u, _ = get_urgency(t.get("deadline"))
                    dd.append(f'<span class="cal-dot cal-dot-{u}"></span>')
            dots = f'<div class="cal-dots">{"".join(dd)}</div>'
        html += f'<div class="{cls}">{day}{dots}</div>'
    html += '</div>'
    return html

def render_weekly_view(task_date_map):
    now = now_kst(); today = now.date()
    monday = today - timedelta(days=today.weekday())
    dow = ["월", "화", "수", "목", "금", "토", "일"]
    html = ""
    for i in range(7):
        d = monday + timedelta(days=i)
        dk = d.strftime("%Y-%m-%d")
        is_today = d == today
        cc = "week-day-card-today" if is_today else ""
        hc = "week-day-header-today" if is_today else ""
        tb = " · 오늘" if is_today else ""
        html += f'<div class="week-day-card {cc}"><div class="week-day-header {hc}">{d.strftime("%m/%d")} ({dow[i]}){tb}</div>'
        dt = task_date_map.get(dk, [])
        if dt:
            for t in dt[:5]:
                if t.get("is_completed"): html += f'<div class="week-task-item" style="text-decoration:line-through; color:var(--gray-400);">✅ {t["title"]}</div>'
                else:
                    u, _ = get_urgency(t.get("deadline"))
                    pi = PRIORITIES.get(t.get("priority","중간"),"")
                    dl = parse_deadline_kst(t.get("deadline"))
                    ts = dl.strftime("%H:%M") if dl else ""
                    html += f'<div class="week-task-item week-task-item-{u}">{pi} {t["title"]} <span style="color:var(--gray-400);font-size:0.7rem;">{ts}</span></div>'
            if len(dt) > 5: html += f'<div class="week-no-task">외 {len(dt)-5}건</div>'
        else: html += '<div class="week-no-task">일정 없음</div>'
        html += '</div>'
    return html

def render_category_chart(active, completed):
    cats = [c for c in CATEGORIES if c != "전체"]
    ac = Counter(t.get("category","기타") for t in active)
    cc = Counter(t.get("category","기타") for t in completed)
    mx = max((ac.get(c,0)+cc.get(c,0)) for c in cats) if cats else 1
    mx = max(mx, 1)
    html = ""
    for cat in cats:
        a, co = ac.get(cat,0), cc.get(cat,0)
        total = a + co
        color = CATEGORY_COLORS.get(cat,"#8c8c8c")
        icon = CATEGORY_ICONS.get(cat,"")
        ap = a/mx*100; cp = co/mx*100
        al = str(a) if a > 0 and ap > 10 else ""
        cl = str(co) if co > 0 and cp > 10 else ""
        html += f'<div class="chart-bar-row"><div class="chart-bar-label">{icon} {cat}</div><div class="chart-bar-track"><div class="chart-bar-segment" style="width:{ap}%;background:{color};">{al}</div><div class="chart-bar-segment" style="width:{cp}%;background:{color};opacity:0.3;">{cl}</div></div><div class="chart-bar-count">{total}</div></div>'
    html += '<div style="display:flex;gap:1rem;justify-content:center;margin-top:0.6rem;font-size:0.68rem;color:var(--gray-400);">■ 진행 중 <span style="opacity:0.3;">■</span> 완료</div>'
    return html

def render_time_chart(all_tasks):
    cats = [c for c in CATEGORIES if c != "전체"]
    tbc = defaultdict(float)
    for t in all_tasks:
        s = t.get("timer_started_at")
        if s:
            e = t.get("timer_ended_at") or now_kst().isoformat()
            tbc[t.get("category","기타")] += calc_duration_minutes(s, e)
    mx = max(tbc.values()) if tbc else 1; mx = max(mx,1)
    if not any(tbc.get(c,0)>0 for c in cats):
        return '<div style="text-align:center;color:var(--gray-400);font-size:0.82rem;padding:1.5rem;">아직 시간 기록이 없습니다.<br>업무에서 ▶️ 시작을 눌러보세요.</div>'
    html = ""
    for cat in cats:
        m = tbc.get(cat,0)
        if m == 0: continue
        color = CATEGORY_COLORS.get(cat,"#8c8c8c")
        html += f'<div class="time-chart-row"><div class="time-chart-label">{CATEGORY_ICONS.get(cat,"")} {cat}</div><div class="time-chart-bar" style="width:{max(m/mx*100,8)}%;background:{color};">{format_minutes(m)}</div></div>'
    return html

def build_weekly_report(completed, all_tasks):
    now = now_kst(); mon = now.date()-timedelta(days=now.date().weekday()); sun = mon+timedelta(days=6)
    wc = [t for t in completed if (ca:=parse_deadline_kst(t.get("completed_at"))) and mon<=ca.date()<=sun]
    tm = sum(calc_duration_minutes(t.get("timer_started_at"),t.get("timer_ended_at")) for t in wc)
    cc = Counter(t.get("category","기타") for t in wc)
    dc = defaultdict(int)
    for t in wc:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca: dc[ca.strftime("%m/%d")] += 1
    return {"period":f"{mon.strftime('%m/%d')}~{sun.strftime('%m/%d')}","total_completed":len(wc),"total_minutes":tm,"cat_counts":dict(cc),"daily_counts":dict(dc)}

def build_monthly_report(completed, all_tasks):
    now = now_kst(); y,m = now.year, now.month
    mc = [t for t in completed if (ca:=parse_deadline_kst(t.get("completed_at"))) and ca.year==y and ca.month==m]
    tm = sum(calc_duration_minutes(t.get("timer_started_at"),t.get("timer_ended_at")) for t in mc)
    cc = Counter(t.get("category","기타") for t in mc)
    wc = defaultdict(int)
    for t in mc:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca: wc[f"{(ca.day-1)//7+1}주차"] += 1
    return {"period":f"{y}년 {m}월","total_completed":len(mc),"total_minutes":tm,"cat_counts":dict(cc),"weekly_counts":dict(wc)}


# ============================================
# 비밀번호 잠금
# ============================================
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


# ============================================
# 사이드바
# ============================================
with st.sidebar:
    st.markdown("#### 📝 퀵 메모")
    memo_input = st.text_area("메모", placeholder="번뜩이는 아이디어, URL, 메모...", height=80, label_visibility="collapsed")
    mc1, mc2 = st.columns([3,1])
    with mc1:
        if st.button("💾 저장", use_container_width=True, type="primary"):
            if memo_input.strip(): add_memo(memo_input.strip()); st.toast("✅ 메모 저장!"); st.rerun()
    with mc2:
        if st.button("📌", use_container_width=True):
            if memo_input.strip(): add_memo(memo_input.strip(), pinned=True); st.toast("📌 고정!"); st.rerun()

    memos = load_memos() or []
    for label, group, is_pinned in [("📌 고정", [m for m in memos if m.get("pinned")], True), ("최근", [m for m in memos if not m.get("pinned")][:8], False)]:
        if not group: continue
        st.caption(f"{label} ({len(group)}건)")
        for memo in group:
            cm, cp, cd = st.columns([5,1,1])
            with cm:
                bs = "border-color:var(--gold);" if is_pinned else ""
                st.markdown(f'<div class="memo-item" style="{bs}">{memo["content"][:120]}{"..." if len(memo["content"])>120 else ""}<div class="memo-time">{format_dt(memo["created_at"])}</div></div>', unsafe_allow_html=True)
            with cp:
                if st.button("📌", key=f"pin_{memo['id']}", help="고정 토글"): toggle_pin_memo(memo['id'], is_pinned); st.rerun()
            with cd:
                if st.button("🗑", key=f"del_memo_{memo['id']}", help="삭제"): delete_memo(memo['id']); st.rerun()

    st.markdown("---")
    st.markdown("#### 🔍 검색 & 필터")
    search_query = st.text_input("검색", placeholder="제목, 내용, 태그...", label_visibility="collapsed")
    fc1, fc2 = st.columns(2)
    with fc1: st.session_state.filter_category = st.selectbox("카테고리", CATEGORIES, index=CATEGORIES.index(st.session_state.filter_category))
    with fc2:
        po = ["전체"]+list(PRIORITIES.keys())
        cp = st.session_state.filter_priority if st.session_state.filter_priority in po else "전체"
        st.session_state.filter_priority = st.selectbox("우선순위", po, index=po.index(cp))

    at = load_all_tags() or []
    if at:
        to = [""]+sorted(at)
        st.session_state.filter_tag = st.selectbox("🏷️ 태그", to, format_func=lambda x: "전체" if x=="" else f"#{x}")
    else: st.session_state.filter_tag = ""
    st.session_state.sort_by = st.radio("정렬", ["마감일순","우선순위순","등록순"], index=["마감일순","우선순위순","등록순"].index(st.session_state.sort_by), horizontal=True)
    st.markdown("---")
    st.markdown('<div style="text-align:center;font-size:0.7rem;color:var(--gray-400);letter-spacing:1px;">MY AI DESK v3.0<br>CSR EDITION</div>', unsafe_allow_html=True)


# ============================================
# 메인 헤더
# ============================================
st.markdown('<div class="app-header"><div class="app-header-sub">CSR · Task Manager</div><h1>My AI Desk</h1></div>', unsafe_allow_html=True)


# ============================================
# 데이터 로드
# ============================================
all_active = load_tasks(show_completed=False, search_query="", category="전체", priority="전체") or []
all_completed = load_completed_tasks(100) or []
completed_today = load_completed_today_count() or 0
overdue_count = sum(1 for t in all_active if get_urgency(t.get("deadline"))[0]=="overdue")
today_count = sum(1 for t in all_active if get_urgency(t.get("deadline"))[0]=="today")
total_active = len(all_active)
tts = today_count+completed_today
completion_rate = int(completed_today/tts*100) if tts>0 else 0


# ============================================
# 통계 (클릭 가능)
# ============================================
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
            title_style = 'style="text-decoration:line-through;"' if is_done else ""
            st.markdown(f'<div class="task-card {cls}"><div class="task-header"><span class="task-title" {title_style}>{pi} {t["title"]}</span><div class="task-badges"><span class="badge">{cat}</span></div></div><div class="task-meta"><span>{("📅 "+format_dt(t["deadline"])) if t.get("deadline") else ""}</span>{("<span class=\\"urgency-tag urgency-"+u+"\\">"+ul+"</span>") if ul else ""}{(" · 완료: "+format_dt(t["completed_at"])) if is_done else ""}</div></div>', unsafe_allow_html=True)
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


# ============================================
# 📊 업무 현황 & 시간 분석
# ============================================
with st.expander("📊 업무 현황 & 시간 분석", expanded=True):
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown('<div class="section-header-light">카테고리별</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header" style="margin-top:0;">업무 현황</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-container">{render_category_chart(all_active, all_completed)}</div>', unsafe_allow_html=True)
    with cc2:
        st.markdown('<div class="section-header-light">카테고리별</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header" style="margin-top:0;">시간 투자</div>', unsafe_allow_html=True)
        aft = load_all_tasks() or []
        st.markdown(f'<div class="chart-container">{render_time_chart(aft)}</div>', unsafe_allow_html=True)


# ============================================
# 📋 히스토리 & 리포트
# ============================================
with st.expander("📋 업무 히스토리 & 리포트", expanded=False):
    rt1, rt2, rt3 = st.tabs(["📅 주간","📆 월간","📜 타임라인"])
    with rt1:
        wr = build_weekly_report(all_completed, all_active)
        st.markdown(f'<div class="section-header">{wr["period"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="report-grid"><div class="report-box"><div class="report-number" style="color:var(--green);">{wr["total_completed"]}</div><div class="report-label">완료</div></div><div class="report-box"><div class="report-number" style="color:var(--gold);">{format_minutes(wr["total_minutes"])}</div><div class="report-label">투자 시간</div></div><div class="report-box"><div class="report-number" style="color:var(--orange);">{format_minutes(wr["total_minutes"]/max(wr["total_completed"],1))}</div><div class="report-label">건당 평균</div></div></div>', unsafe_allow_html=True)
        if wr['cat_counts']:
            for cat,cnt in sorted(wr['cat_counts'].items(), key=lambda x:x[1], reverse=True):
                st.markdown(f"{CATEGORY_ICONS.get(cat,'')} **{cat}**: {cnt}건")
        if wr['daily_counts']:
            mx = max(wr['daily_counts'].values())
            for ds,cnt in sorted(wr['daily_counts'].items()):
                pct = cnt/mx*100
                st.markdown(f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;"><span style="font-size:0.75rem;min-width:40px;color:var(--gray-400);font-variant-numeric:tabular-nums;">{ds}</span><div style="height:12px;width:{max(pct,8)}%;background:var(--black);display:flex;align-items:center;padding:0 6px;"><span style="font-size:0.6rem;color:var(--white);">{cnt}</span></div></div>', unsafe_allow_html=True)
        if not wr['total_completed']: st.caption("이번 주 완료된 업무가 없습니다.")
    with rt2:
        mr = build_monthly_report(all_completed, all_active)
        st.markdown(f'<div class="section-header">{mr["period"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="report-grid"><div class="report-box"><div class="report-number" style="color:var(--green);">{mr["total_completed"]}</div><div class="report-label">완료</div></div><div class="report-box"><div class="report-number" style="color:var(--gold);">{format_minutes(mr["total_minutes"])}</div><div class="report-label">투자 시간</div></div><div class="report-box"><div class="report-number" style="color:var(--gold-hover);">{format_minutes(mr["total_minutes"]/max(mr["total_completed"],1))}</div><div class="report-label">건당 평균</div></div></div>', unsafe_allow_html=True)
        if mr['cat_counts']:
            for cat,cnt in sorted(mr['cat_counts'].items(), key=lambda x:x[1], reverse=True):
                st.markdown(f"{CATEGORY_ICONS.get(cat,'')} **{cat}**: {cnt}건")
        if not mr['total_completed']: st.caption("이번 달 완료된 업무가 없습니다.")
    with rt3:
        st.markdown('<div class="section-header">최근 완료 타임라인</div>', unsafe_allow_html=True)
        if all_completed:
            for ct in all_completed[:20]:
                ca = parse_deadline_kst(ct.get("completed_at"))
                ds = ca.strftime("%m/%d %H:%M") if ca else ""
                dur = calc_duration(ct.get("created_at"),ct.get("completed_at"))
                cat = ct.get("category","기타"); color = CATEGORY_COLORS.get(cat,"#8c8c8c")
                tags = parse_tags(ct.get("tags")); th = " ".join(f'<span class="badge-tag">#{t}</span>' for t in tags)
                tm = calc_duration_minutes(ct.get("timer_started_at"),ct.get("timer_ended_at"))
                ts = f" · ⏱ {format_minutes(tm)}" if tm>0 else ""
                st.markdown(f'<div class="timeline-item"><div class="timeline-date">{ds}</div><div class="timeline-content"><div class="timeline-title"><span style="color:{color};">●</span> {ct["title"]}</div><div class="timeline-detail">{cat}{" · "+dur if dur else ""}{ts}{" · "+th if th else ""}</div></div></div>', unsafe_allow_html=True)
        else: st.caption("아직 완료된 업무가 없습니다.")


# ============================================
# 📅 달력
# ============================================
with st.expander("📅 달력", expanded=True):
    cal_tasks = load_all_tasks() or []
    tdm = build_task_date_map(cal_tasks)
    now = now_kst(); today_str = now.strftime("%Y-%m-%d")
    ct1, ct2 = st.tabs(["📆 월간","📋 주간"])
    with ct1:
        n1,n2,n3,n4 = st.columns([1,3,3,1])
        with n1:
            if st.button("◀", key="cp", use_container_width=True):
                if st.session_state.cal_month==1: st.session_state.cal_month=12; st.session_state.cal_year-=1
                else: st.session_state.cal_month-=1
                st.rerun()
        with n2:
            st.markdown(f'<div style="text-align:right;font-family:var(--font-serif);font-size:1.1rem;font-weight:700;color:var(--black);padding:0.3rem 0;">{st.session_state.cal_year}년 {st.session_state.cal_month}월</div>', unsafe_allow_html=True)
        with n3:
            if st.session_state.cal_year!=now.year or st.session_state.cal_month!=now.month:
                if st.button("오늘", key="ct", use_container_width=True): st.session_state.cal_year=now.year; st.session_state.cal_month=now.month; st.session_state.selected_date=None; st.rerun()
        with n4:
            if st.button("▶", key="cn", use_container_width=True):
                if st.session_state.cal_month==12: st.session_state.cal_month=1; st.session_state.cal_year+=1
                else: st.session_state.cal_month+=1
                st.rerun()
        ch = render_monthly_calendar(st.session_state.cal_year, st.session_state.cal_month, tdm, today_str, st.session_state.selected_date)
        st.markdown(f'<div class="cal-container">{ch}</div>', unsafe_allow_html=True)
        y,m = st.session_state.cal_year, st.session_state.cal_month
        md = calendar.monthrange(y,m)[1]
        do = ["선택 안 함"]+[f"{m}/{d}" for d in range(1,md+1)]
        si = 0
        if st.session_state.selected_date:
            try:
                sd = datetime.strptime(st.session_state.selected_date,"%Y-%m-%d")
                if sd.year==y and sd.month==m: si=sd.day
            except: pass
        pk = st.selectbox("📅 날짜 선택", do, index=si, key="dp")
        if pk=="선택 안 함": st.session_state.selected_date=None
        else: st.session_state.selected_date=f"{y}-{m:02d}-{int(pk.split('/')[1]):02d}"
        if st.session_state.selected_date and st.session_state.selected_date in tdm:
            st2 = tdm[st.session_state.selected_date]
            st.markdown(f'<div class="selected-date-header">{st.session_state.selected_date} 업무 ({len(st2)}건)</div>', unsafe_allow_html=True)
            for t in st2:
                u, _ = get_urgency(t.get("deadline"))
                s = "✅" if t.get("is_completed") else PRIORITIES.get(t.get("priority","중간"),"")
                dl = parse_deadline_kst(t.get("deadline")); ts = dl.strftime("%H:%M") if dl else ""
                cls = u if not t.get("is_completed") else "completed-card"
                st.markdown(f'<div class="task-card {cls}" style="padding:0.6rem 0.5rem;"><div class="task-header"><span class="task-title" style="font-size:0.88rem;">{s} {t["title"]}</span><span style="font-size:0.72rem;color:var(--gray-400);">{ts}</span></div></div>', unsafe_allow_html=True)
        elif st.session_state.selected_date: st.caption(f"{st.session_state.selected_date}에 업무 없음.")
        st.markdown('<div style="display:flex;gap:1rem;justify-content:center;margin-top:0.6rem;font-size:0.68rem;color:var(--gray-400);"><span><span class="cal-dot cal-dot-overdue" style="display:inline-block;"></span> 기한초과</span><span><span class="cal-dot cal-dot-today" style="display:inline-block;"></span> 오늘</span><span><span class="cal-dot cal-dot-upcoming" style="display:inline-block;"></span> 예정</span><span><span class="cal-dot cal-dot-completed" style="display:inline-block;"></span> 완료</span></div>', unsafe_allow_html=True)
    with ct2:
        wd = now.date().weekday(); mon = now.date()-timedelta(days=wd); sun = mon+timedelta(days=6)
        st.markdown(f'<div style="text-align:center;font-family:var(--font-serif);font-size:1rem;font-weight:600;color:var(--black);margin-bottom:0.5rem;">{mon.strftime("%m/%d")} — {sun.strftime("%m/%d")} 이번 주</div>', unsafe_allow_html=True)
        st.markdown(render_weekly_view(tdm), unsafe_allow_html=True)


# ============================================
# ➕ 새 업무 등록
# ============================================
with st.expander("➕ 새 업무 등록", expanded=False):
    with st.form("add_task_form", clear_on_submit=True):
        nt = st.text_input("업무명 *", placeholder="예: 공정거래 자율준수 점검, 동반성장 협력사 간담회")
        nd = st.text_area("상세 내용", height=200, placeholder="마크다운 체크리스트 등 자유롭게 작성\n\n- [ ] 할 일 1\n- [ ] 할 일 2")
        rc1, rc2 = st.columns(2)
        with rc1: ndt = st.date_input("마감일", value=None)
        with rc2: ntm = st.time_input("마감 시간", value=None)
        rc3, rc4, rc5 = st.columns(3)
        cna = [c for c in CATEGORIES if c!="전체"]
        with rc3: ncat = st.selectbox("카테고리", cna, index=0)
        with rc4: npri = st.selectbox("우선순위", list(PRIORITIES.keys()), index=1, format_func=lambda x: f"{PRIORITIES[x]} {x}")
        with rc5: nrec = RECURRENCE_OPTIONS[st.selectbox("반복", list(RECURRENCE_OPTIONS.keys()), index=0)]
        ntg = st.text_input("🏷️ 태그", placeholder="#급함 #보고용 #협력사")
        submitted = st.form_submit_button("📌 업무 등록", use_container_width=True, type="primary")
        if submitted:
            if nt.strip():
                dl = None
                if ndt: dl = datetime.combine(ndt, ntm if ntm else dt_time(18,0)).replace(tzinfo=KST)
                add_task(nt.strip(), nd.strip(), dl, ncat, npri, nrec, ", ".join(parse_tags(ntg)))
                st.toast("✅ 업무 등록 완료!"); st.balloons(); st.rerun()
            else: st.warning("업무명을 입력해주세요.")


# ============================================
# 📌 업무 목록
# ============================================
afp = []
if st.session_state.filter_category!="전체": afp.append(f"카테고리: {st.session_state.filter_category}")
if st.session_state.filter_priority!="전체": afp.append(f"우선순위: {st.session_state.filter_priority}")
if st.session_state.filter_tag: afp.append(f"태그: #{st.session_state.filter_tag}")
if search_query: afp.append(f'검색: "{search_query}"')
fi = f' · <span class="filter-active">{" | ".join(afp)}</span>' if afp else ""

st.markdown(f'<div class="section-header-light">진행 중인</div>', unsafe_allow_html=True)
st.markdown(f'<div class="section-header">업무 목록{fi}</div>', unsafe_allow_html=True)

# 카테고리 탭
cat_tabs = st.tabs([f"{CATEGORY_ICONS.get(c,'')} {c}" if c != "전체" else "📋 전체" for c in CATEGORIES])

for tab_idx, cat_tab in enumerate(cat_tabs):
    with cat_tab:
        tab_category = CATEGORIES[tab_idx]
        # 탭 카테고리 + 사이드바 필터 조합
        effective_category = tab_category if tab_category != "전체" else st.session_state.filter_category

        tasks = load_tasks(show_completed=False, search_query=search_query, category=effective_category if tab_category != "전체" else st.session_state.filter_category, priority=st.session_state.filter_priority, tag_filter=st.session_state.filter_tag) or []
        if st.session_state.sort_by=="우선순위순": tasks.sort(key=lambda t: PRIORITY_ORDER.get(t.get("priority","중간"),1))
        elif st.session_state.sort_by=="등록순": tasks.sort(key=lambda t: t.get("created_at",""), reverse=True)

        if not tasks:
            if search_query or afp: st.info("조건에 맞는 업무가 없습니다.")
            else: st.caption(f"{'등록된 업무가 없습니다.' if tab_category == '전체' else f'{tab_category} 업무가 없습니다.'}")
        else:
            for task in tasks:
                urgency, urgency_label = get_urgency(task.get("deadline"))
                pri = task.get("priority","중간"); pi = PRIORITIES.get(pri,"")
                rec = task.get("recurrence"); tags = parse_tags(task.get("tags"))
                prog_html = ""
                prog = calc_checklist_progress(task.get("description"))
                if prog:
                    pct = int(prog[0]/prog[1]*100) if prog[1]>0 else 0
                    prog_html = f'<span class="progress-inline"><span class="progress-bar-mini"><span class="progress-bar-mini-fill" style="width:{pct}%;"></span></span><span style="font-size:0.7rem;">{prog[0]}/{prog[1]}</span></span>'
                urg_html = f'<span class="urgency-tag urgency-{urgency}">{urgency_label}</span>' if urgency_label else ""
                tag_badges = " ".join(f'<span class="badge-tag">#{t}</span>' for t in tags[:4])
                timer_html = ""
                if task.get("timer_started_at") and not task.get("timer_ended_at"):
                    el = calc_duration_minutes(task["timer_started_at"], now_kst().isoformat())
                    timer_html = f'<span class="timer-active">⏱ {format_minutes(el)} 진행 중</span>'
                elif task.get("timer_started_at") and task.get("timer_ended_at"):
                    el = calc_duration_minutes(task["timer_started_at"], task["timer_ended_at"])
                    timer_html = f'<span style="font-size:0.72rem;color:var(--gray-400);">⏱ {format_minutes(el)}</span>'

                card = (f'<div class="task-card {urgency}"><div class="task-header"><span class="task-title">{pi} {task["title"]}</span><div class="task-badges"><span class="badge badge-priority-{pri}">{pri}</span><span class="badge">{task.get("category","기타")}</span>{tag_badges}</div></div><div class="task-meta"><span>{("📅 "+format_dt(task["deadline"])) if task.get("deadline") else "📅 마감일 미지정"}</span>{urg_html}{prog_html}{timer_html}{"<span>🔁 반복</span>" if rec else ""}</div></div>')
                st.markdown(card, unsafe_allow_html=True)

                # 원클릭 완료 + 상세 보기 (같은 줄)
                qc1, qc2 = st.columns([1, 7])
                with qc1:
                    if st.button("✅", key=f"quick_{tab_category}_{task['id']}", help="완료 처리"):
                        complete_task(task)
                        st.toast("🎉 완료! 다음 회차 생성됨" if rec else "🎉 수고하셨습니다!")
                        st.balloons(); st.rerun()

                with qc2:
                    with st.expander(f"상세 · {task['title']}", expanded=False):
                        if task.get("description"): st.markdown(task["description"])
                        else: st.caption("상세 내용 없음")
                        if tags: st.markdown("🏷️ " + " ".join(f"`#{t}`" for t in tags))

                        st.markdown("**⏱️ 소요시간 트래킹**")
                        tc1,tc2,tc3 = st.columns(3)
                        hs = bool(task.get("timer_started_at")); he = bool(task.get("timer_ended_at")); ir = hs and not he
                        with tc1:
                            if not hs:
                                if st.button("▶️ 시작", key=f"ts_{tab_category}_{task['id']}", use_container_width=True): start_timer(task["id"]); st.toast("⏱ 시작!"); st.rerun()
                            elif ir: st.markdown(f"🔴 **진행 중** · {format_minutes(calc_duration_minutes(task['timer_started_at'],now_kst().isoformat()))}")
                            else: st.markdown(f"✅ **기록 완료** · {format_minutes(calc_duration_minutes(task['timer_started_at'],task['timer_ended_at']))}")
                        with tc2:
                            if ir:
                                if st.button("⏹ 정지", key=f"tp_{tab_category}_{task['id']}", use_container_width=True): stop_timer(task["id"]); st.toast("⏱ 정지!"); st.rerun()
                        with tc3:
                            if hs:
                                if st.button("🔄 초기화", key=f"tr_{tab_category}_{task['id']}", use_container_width=True): reset_timer(task["id"]); st.toast("초기화!"); st.rerun()

                        st.markdown("---")
                        bc1,bc2 = st.columns([1,1])
                        with bc1:
                            if st.button("✏️ 수정", key=f"edit_{tab_category}_{task['id']}", use_container_width=True): st.session_state[f"editing_{task['id']}"]=True; st.rerun()
                        with bc2:
                            if st.button("🗑️ 삭제", key=f"del_{tab_category}_{task['id']}", use_container_width=True): delete_task(task["id"]); st.toast("삭제됨."); st.rerun()

                        if st.session_state.get(f"editing_{task['id']}"):
                            st.markdown("---")
                            et = st.text_input("업무명", value=task["title"], key=f"et_{tab_category}_{task['id']}")
                            ed = st.text_area("상세", value=task.get("description",""), height=150, key=f"ed_{tab_category}_{task['id']}")
                            dl = parse_deadline_kst(task.get("deadline"))
                            if dl: edt=st.date_input("마감일",value=dl.date(),key=f"edt_{tab_category}_{task['id']}"); etm=st.time_input("시간",value=dl.time(),key=f"etm_{tab_category}_{task['id']}")
                            else: edt=st.date_input("마감일",value=None,key=f"edt_{tab_category}_{task['id']}"); etm=st.time_input("시간",value=None,key=f"etm_{tab_category}_{task['id']}")
                            ec1,ec2,ec3 = st.columns(3)
                            cna = [c for c in CATEGORIES if c!="전체"]
                            with ec1: ect=st.selectbox("카테고리",cna,index=cna.index(task.get("category","기타")) if task.get("category","기타") in cna else 0, key=f"ec_{tab_category}_{task['id']}")
                            with ec2: epr=st.selectbox("우선순위",list(PRIORITIES.keys()),index=list(PRIORITIES.keys()).index(task.get("priority","중간")) if task.get("priority","중간") in PRIORITIES else 1, key=f"ep_{tab_category}_{task['id']}", format_func=lambda x:f"{PRIORITIES[x]} {x}")
                            with ec3:
                                rk=list(RECURRENCE_OPTIONS.keys()); ri=0
                                cr=task.get("recurrence")
                                if cr:
                                    for i,k in enumerate(rk):
                                        if RECURRENCE_OPTIONS[k]==cr: ri=i; break
                                erc=RECURRENCE_OPTIONS[st.selectbox("반복",rk,index=ri,key=f"er_{tab_category}_{task['id']}")]
                            etg=st.text_input("🏷️ 태그",value=task.get("tags",""),key=f"etag_{tab_category}_{task['id']}")
                            sc1,sc2=st.columns(2)
                            with sc1:
                                if st.button("💾 저장",key=f"save_{tab_category}_{task['id']}",use_container_width=True,type="primary"):
                                    ddl=None
                                    if edt: ddl=datetime.combine(edt,etm if etm else dt_time(18,0)).replace(tzinfo=KST)
                                    update_task(task["id"],et,ed,ddl,ect,epr,erc,", ".join(parse_tags(etg)))
                                    st.session_state[f"editing_{task['id']}"]=False; st.toast("✅ 수정 완료!"); st.rerun()
                            with sc2:
                                if st.button("취소",key=f"cancel_{tab_category}_{task['id']}",use_container_width=True): st.session_state[f"editing_{task['id']}"]=False; st.rerun()


# ============================================
# ✅ 완료 업무
# ============================================
st.markdown("---")
with st.expander("✅ 완료된 업무"):
    ct = load_completed_tasks(30) or []
    if not ct: st.caption("완료된 업무가 없습니다.")
    else:
        for c in ct:
            dur=calc_duration(c.get("created_at"),c.get("completed_at"))
            pi=PRIORITIES.get(c.get("priority","중간"),"")
            tags=parse_tags(c.get("tags")); tb=" ".join(f'<span class="badge-tag">#{t}</span>' for t in tags[:3])
            tm=calc_duration_minutes(c.get("timer_started_at"),c.get("timer_ended_at"))
            ts=f" · ⏱ {format_minutes(tm)}" if tm>0 else ""
            cc = (f'<div class="task-card completed-card"><div class="task-header"><span class="task-title" style="text-decoration:line-through;">{pi} {c["title"]}</span><div class="task-badges"><span class="badge">{c.get("category","기타")}</span>{tb}</div></div><div class="task-meta"><span>완료: {format_dt(c["completed_at"])}</span>{"<span>⏱ "+dur+"</span>" if dur else ""}<span>{ts}</span></div></div>')
            st.markdown(cc, unsafe_allow_html=True)
            cr1,cr2=st.columns(2)
            with cr1:
                if st.button("↩️ 되돌리기",key=f"undo_{c['id']}"): uncomplete_task(c["id"]); st.rerun()
            with cr2:
                if st.button("🗑️ 삭제",key=f"cdel_{c['id']}"): delete_task(c["id"]); st.rerun()
