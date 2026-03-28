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
    "공정거래": "#6366f1",
    "동반성장": "#f59e0b",
    "사회공헌": "#10b981",
    "환경": "#06b6d4",
    "기타": "#8b5cf6",
}
PRIORITIES = {"높음": "🔴", "중간": "🟡", "낮음": "🟢"}
PRIORITY_ORDER = {"높음": 0, "중간": 1, "낮음": 2}

RECURRENCE_OPTIONS = {
    "없음": None,
    "매일": "daily",
    "매주": "weekly",
    "격주": "biweekly",
    "매월": "monthly",
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
    page_title="My AI Desk",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================
# CSS
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

    :root {
        --bg-primary: #ffffff;
        --bg-secondary: #f7fafc;
        --bg-card: #ffffff;
        --text-primary: #1a202c;
        --text-secondary: #4a5568;
        --text-muted: #718096;
        --text-faint: #a0aec0;
        --border: #e2e8f0;
        --accent: #667eea;
        --accent-light: #667eea18;
        --red: #e53e3e;
        --orange: #ed8936;
        --green: #48bb78;
        --blue: #4299e1;
        --yellow: #ecc94b;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
        --shadow-md: 0 2px 12px rgba(0,0,0,0.08);
        --radius: 12px;
        --radius-sm: 8px;
    }

    .block-container { padding-top: 1.5rem; max-width: 1200px; }

    /* ── 통계 카드 ── */
    .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin-bottom: 1rem; }
    .stat-box {
        background: var(--bg-card); border-radius: var(--radius); padding: 1rem 0.8rem;
        text-align: center; border: 1px solid var(--border); box-shadow: var(--shadow-sm);
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .stat-box:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
    .stat-number { font-size: 2rem; font-weight: 700; line-height: 1.2; }
    .stat-label { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.15rem; }
    .stat-bar { height: 3px; border-radius: 2px; margin-top: 0.5rem; background: var(--border); overflow: hidden; }
    .stat-bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s ease; }

    /* ── 업무 카드 ── */
    .task-card {
        background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
        padding: 1rem 1.2rem; margin-bottom: 0.6rem; transition: all 0.2s;
        border-left: 4px solid var(--border);
    }
    .task-card:hover { box-shadow: var(--shadow-md); border-color: var(--accent); }
    .task-card.overdue { border-left-color: var(--red); background: #fff5f5; }
    .task-card.today { border-left-color: var(--orange); background: #fffaf0; }
    .task-card.upcoming { border-left-color: var(--green); }
    .task-card.completed-card { opacity: 0.55; border-left-color: var(--text-faint); }
    .task-header { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; }
    .task-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); flex: 1; }
    .task-badges { display: flex; gap: 0.3rem; align-items: center; flex-shrink: 0; flex-wrap: wrap; }
    .badge {
        font-size: 0.7rem; padding: 2px 8px; border-radius: 12px;
        background: var(--bg-secondary); color: var(--text-secondary);
        white-space: nowrap;
    }
    .badge-priority-높음 { background: #fed7d7; color: #c53030; }
    .badge-priority-중간 { background: #fefcbf; color: #975a16; }
    .badge-priority-낮음 { background: #c6f6d5; color: #276749; }
    .badge-tag {
        background: #ebf4ff; color: #3182ce; font-size: 0.68rem;
        padding: 1px 6px; border-radius: 10px;
    }
    .task-meta {
        font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;
        display: flex; flex-wrap: wrap; gap: 0.3rem 0.8rem; align-items: center;
    }
    .urgency-tag { font-weight: 600; }
    .urgency-overdue { color: var(--red); }
    .urgency-today { color: var(--orange); }
    .progress-inline { display: inline-flex; align-items: center; gap: 0.3rem; }
    .progress-bar-mini {
        width: 50px; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden;
    }
    .progress-bar-mini-fill { height: 100%; background: var(--accent); border-radius: 2px; }
    .timer-active {
        display: inline-flex; align-items: center; gap: 0.3rem;
        background: #fff5f5; border: 1px solid #feb2b2; border-radius: 6px;
        padding: 1px 8px; font-size: 0.75rem; color: var(--red); font-weight: 600;
        animation: pulse-border 2s infinite;
    }
    @keyframes pulse-border {
        0%, 100% { border-color: #feb2b2; }
        50% { border-color: var(--red); }
    }

    /* ── 차트 영역 ── */
    .chart-container {
        background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
        padding: 1rem; box-shadow: var(--shadow-sm);
    }
    .chart-bar-row {
        display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;
    }
    .chart-bar-label {
        font-size: 0.8rem; font-weight: 500; color: var(--text-secondary);
        min-width: 65px; text-align: right;
    }
    .chart-bar-track {
        flex: 1; height: 22px; background: var(--bg-secondary); border-radius: 6px;
        overflow: hidden; display: flex;
    }
    .chart-bar-segment {
        height: 100%; transition: width 0.5s ease; display: flex; align-items: center;
        justify-content: center; font-size: 0.68rem; color: white; font-weight: 600;
        min-width: 0;
    }
    .chart-bar-count {
        font-size: 0.75rem; color: var(--text-muted); min-width: 30px;
    }

    /* ── 타임라인 ── */
    .timeline-item {
        display: flex; gap: 0.8rem; padding: 0.5rem 0; border-bottom: 1px solid var(--border);
    }
    .timeline-date {
        font-size: 0.75rem; color: var(--text-faint); min-width: 75px; text-align: right;
        padding-top: 2px;
    }
    .timeline-content { flex: 1; }
    .timeline-title { font-size: 0.85rem; font-weight: 500; color: var(--text-primary); }
    .timeline-detail { font-size: 0.75rem; color: var(--text-muted); }

    /* ── 리포트 카드 ── */
    .report-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin-bottom: 0.8rem; }
    .report-box {
        background: var(--bg-secondary); border-radius: var(--radius-sm); padding: 0.8rem;
        text-align: center;
    }
    .report-number { font-size: 1.5rem; font-weight: 700; }
    .report-label { font-size: 0.72rem; color: var(--text-muted); }

    /* ── 시간 트래킹 ── */
    .time-chart-row {
        display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;
    }
    .time-chart-label {
        font-size: 0.78rem; min-width: 65px; text-align: right; color: var(--text-secondary);
    }
    .time-chart-bar {
        height: 18px; border-radius: 4px; display: flex; align-items: center;
        padding: 0 6px; font-size: 0.68rem; color: white; font-weight: 500;
        transition: width 0.5s ease;
    }

    /* ── 달력 ── */
    .cal-container {
        background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
        padding: 1rem; box-shadow: var(--shadow-sm);
    }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
    .cal-dow {
        text-align: center; font-size: 0.75rem; font-weight: 600;
        color: var(--text-faint); padding: 0.3rem 0;
    }
    .cal-dow-sun { color: var(--red); }
    .cal-dow-sat { color: var(--blue); }
    .cal-day {
        position: relative; text-align: center; padding: 0.35rem 0.1rem;
        border-radius: var(--radius-sm); min-height: 2.8rem; font-size: 0.85rem;
        color: var(--text-secondary); cursor: pointer; transition: background 0.15s;
    }
    .cal-day:hover { background: var(--accent-light); }
    .cal-day-empty { cursor: default; }
    .cal-day-empty:hover { background: transparent; }
    .cal-day-today { background: var(--accent); color: white !important; font-weight: 700; }
    .cal-day-today:hover { background: #5a6fd6; }
    .cal-day-selected { outline: 2px solid var(--accent); outline-offset: -2px; }
    .cal-day-sun { color: var(--red); }
    .cal-day-sat { color: var(--blue); }
    .cal-day-today.cal-day-sun, .cal-day-today.cal-day-sat { color: white !important; }
    .cal-dots { display: flex; justify-content: center; gap: 2px; margin-top: 2px; }
    .cal-dot { width: 5px; height: 5px; border-radius: 50%; }
    .cal-dot-overdue { background: var(--red); }
    .cal-dot-today { background: var(--orange); }
    .cal-dot-upcoming { background: var(--green); }
    .cal-dot-completed { background: var(--text-faint); }

    /* ── 주간 뷰 ── */
    .week-day-card {
        background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
        padding: 0.7rem; margin-bottom: 0.4rem;
    }
    .week-day-card-today { background: var(--accent-light); border: 1.5px solid var(--accent); }
    .week-day-header { font-size: 0.82rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.4rem; }
    .week-day-header-today { color: var(--accent); }
    .week-task-item {
        font-size: 0.8rem; color: var(--text-secondary); padding: 0.15rem 0;
        border-left: 3px solid var(--border); padding-left: 0.5rem; margin-bottom: 0.2rem;
    }
    .week-task-item-overdue { border-left-color: var(--red); }
    .week-task-item-today { border-left-color: var(--orange); }
    .week-task-item-upcoming { border-left-color: var(--green); }
    .week-no-task { font-size: 0.78rem; color: var(--text-faint); font-style: italic; }

    /* ── 사이드바 메모 ── */
    .memo-item {
        background: #fffff0; border: 1px solid rgba(236,201,75,0.25);
        border-radius: var(--radius-sm); padding: 0.7rem; margin-bottom: 0.5rem; font-size: 0.85rem;
    }
    .memo-time { font-size: 0.72rem; color: var(--text-faint); }

    /* ── 기타 ── */
    .selected-date-header {
        font-size: 0.95rem; font-weight: 600; color: var(--accent);
        padding: 0.5rem 0; border-bottom: 2px solid var(--accent); margin-bottom: 0.5rem;
    }
    .filter-active { font-size: 0.8rem; color: var(--accent); font-weight: 500; padding: 0.3rem 0; }

    @media (max-width: 768px) {
        .block-container { padding: 0.8rem; }
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .report-grid { grid-template-columns: repeat(2, 1fr); }
        .stat-number { font-size: 1.5rem; }
        .cal-day { min-height: 2.2rem; font-size: 0.78rem; }
        .cal-dot { width: 4px; height: 4px; }
        .task-header { flex-direction: column; align-items: flex-start; }
        .task-badges { margin-top: 0.3rem; }
    }

    .stButton > button { border-radius: var(--radius-sm); }
</style>
""", unsafe_allow_html=True)


# ============================================
# 세션 상태 초기화
# ============================================
def now_kst() -> datetime:
    return datetime.now(KST)

def init_session_state():
    defaults = {
        "authenticated": False,
        "cal_year": now_kst().year,
        "cal_month": now_kst().month,
        "selected_date": None,
        "filter_category": "전체",
        "filter_priority": "전체",
        "filter_tag": "",
        "sort_by": "마감일순",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()


# ============================================
# 유틸리티 함수
# ============================================
def format_dt(dt_str: Optional[str]) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%m/%d(%a) %H:%M")
    except (ValueError, TypeError):
        return dt_str

def parse_deadline_kst(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(KST)
    except (ValueError, TypeError):
        return None

def get_urgency(deadline_str: Optional[str]) -> tuple[str, str]:
    if not deadline_str:
        return "upcoming", ""
    deadline = parse_deadline_kst(deadline_str)
    if not deadline:
        return "upcoming", ""
    diff = deadline - now_kst()
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        overdue_hours = abs(total_seconds) / 3600
        if overdue_hours < 24:
            return "overdue", f"⏰ {int(overdue_hours)}시간 초과"
        return "overdue", f"⏰ {int(overdue_hours / 24)}일 초과"
    elif diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            return "today", f"⚡ {diff.seconds // 60}분 남음"
        return "today", f"⚡ {hours}시간 남음"
    else:
        return "upcoming", f"📅 {diff.days}일 남음"

def calc_duration(created_str: Optional[str], completed_str: Optional[str]) -> str:
    if not created_str or not completed_str:
        return ""
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
    except (ValueError, TypeError):
        return ""

def calc_duration_minutes(start_str: Optional[str], end_str: Optional[str]) -> float:
    """두 ISO 시각 사이 분 단위 차이"""
    if not start_str or not end_str:
        return 0.0
    try:
        s = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        return max((e - s).total_seconds() / 60, 0)
    except (ValueError, TypeError):
        return 0.0

def format_minutes(mins: float) -> str:
    """분을 사람이 읽기 좋은 형태로"""
    if mins < 1:
        return "1분 미만"
    h = int(mins // 60)
    m = int(mins % 60)
    if h > 0 and m > 0:
        return f"{h}시간 {m}분"
    elif h > 0:
        return f"{h}시간"
    return f"{m}분"

def calc_checklist_progress(description: Optional[str]) -> Optional[tuple[int, int]]:
    if not description:
        return None
    total = checked = 0
    for line in description.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ]") or stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            total += 1
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                checked += 1
    return (checked, total) if total > 0 else None

def parse_tags(tags_str: Optional[str]) -> list[str]:
    """콤마 또는 공백으로 구분된 태그 문자열을 리스트로"""
    if not tags_str:
        return []
    # #을 제거하고 콤마/공백 분리
    cleaned = tags_str.replace("#", "")
    tags = re.split(r'[,\s]+', cleaned)
    return [t.strip() for t in tags if t.strip()]

def tags_to_str(tags: list[str]) -> str:
    return ", ".join(tags)

def get_next_recurrence_date(current_deadline: datetime, recurrence: str) -> datetime:
    if recurrence == "daily":
        return current_deadline + timedelta(days=1)
    elif recurrence == "weekly":
        return current_deadline + timedelta(weeks=1)
    elif recurrence == "biweekly":
        return current_deadline + timedelta(weeks=2)
    elif recurrence == "monthly":
        month = current_deadline.month + 1
        year = current_deadline.year
        if month > 12:
            month = 1
            year += 1
        day = min(current_deadline.day, calendar.monthrange(year, month)[1])
        return current_deadline.replace(year=year, month=month, day=day)
    return current_deadline


# ============================================
# DB 함수
# ============================================
def safe_db_call(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"데이터베이스 오류: {e}")
            return None
    return wrapper

@safe_db_call
def load_tasks(
    show_completed: bool = False,
    search_query: str = "",
    category: str = "전체",
    priority: str = "전체",
    tag_filter: str = "",
) -> list[dict]:
    query = supabase.table("tasks").select("*")
    if not show_completed:
        query = query.eq("is_completed", False)
    if category != "전체":
        query = query.eq("category", category)
    if priority != "전체":
        query = query.eq("priority", priority)
    query = query.order("deadline", desc=False)
    result = query.execute()
    tasks = result.data or []
    if search_query:
        q = search_query.lower()
        tasks = [t for t in tasks if
                 q in (t.get("title") or "").lower() or
                 q in (t.get("description") or "").lower() or
                 q in (t.get("category") or "").lower() or
                 q in (t.get("tags") or "").lower()]
    if tag_filter:
        tf = tag_filter.lower().replace("#", "").strip()
        tasks = [t for t in tasks if tf in (t.get("tags") or "").lower()]
    return tasks

@safe_db_call
def load_all_tasks() -> list[dict]:
    result = supabase.table("tasks").select("*").order("deadline", desc=False).execute()
    return result.data or []

@safe_db_call
def add_task(
    title: str, description: str, deadline: Optional[datetime],
    category: str, priority: str = "중간", recurrence: Optional[str] = None,
    tags: str = "",
) -> None:
    data = {
        "title": title, "description": description,
        "deadline": deadline.isoformat() if deadline else None,
        "category": category, "priority": priority,
        "recurrence": recurrence, "tags": tags,
        "is_completed": False,
        "timer_started_at": now_kst().isoformat(),
    }
    supabase.table("tasks").insert(data).execute()

@safe_db_call
def complete_task(task: dict) -> None:
    now = now_kst().isoformat()
    update_data = {"is_completed": True, "completed_at": now}
    # 타이머가 돌고 있었다면 자동 정지
    if task.get("timer_started_at") and not task.get("timer_ended_at"):
        update_data["timer_ended_at"] = now
    supabase.table("tasks").update(update_data).eq("id", task["id"]).execute()

    # 반복 업무 → 다음 회차 자동 생성
    recurrence = task.get("recurrence")
    if recurrence and task.get("deadline"):
        deadline = parse_deadline_kst(task["deadline"])
        if deadline:
            next_deadline = get_next_recurrence_date(deadline, recurrence)
            desc = (task.get("description") or "").replace("- [x]", "- [ ]").replace("- [X]", "- [ ]")
            add_task(
                title=task["title"], description=desc, deadline=next_deadline,
                category=task.get("category", "기타"),
                priority=task.get("priority", "중간"),
                recurrence=recurrence, tags=task.get("tags", ""),
            )

@safe_db_call
def uncomplete_task(task_id: int) -> None:
    supabase.table("tasks").update({
        "is_completed": False, "completed_at": None,
    }).eq("id", task_id).execute()

@safe_db_call
def delete_task(task_id: int) -> None:
    supabase.table("tasks").delete().eq("id", task_id).execute()

@safe_db_call
def update_task(
    task_id: int, title: str, description: str, deadline: Optional[datetime],
    category: str, priority: str = "중간", recurrence: Optional[str] = None,
    tags: str = "",
) -> None:
    data = {
        "title": title, "description": description,
        "deadline": deadline.isoformat() if deadline else None,
        "category": category, "priority": priority,
        "recurrence": recurrence, "tags": tags,
    }
    supabase.table("tasks").update(data).eq("id", task_id).execute()

# -- 타이머 DB 함수 --
@safe_db_call
def start_timer(task_id: int) -> None:
    supabase.table("tasks").update({
        "timer_started_at": now_kst().isoformat(),
        "timer_ended_at": None,
    }).eq("id", task_id).execute()

@safe_db_call
def stop_timer(task_id: int) -> None:
    supabase.table("tasks").update({
        "timer_ended_at": now_kst().isoformat(),
    }).eq("id", task_id).execute()

@safe_db_call
def reset_timer(task_id: int) -> None:
    supabase.table("tasks").update({
        "timer_started_at": None,
        "timer_ended_at": None,
    }).eq("id", task_id).execute()

# -- 메모 DB 함수 --
@safe_db_call
def load_memos() -> list[dict]:
    result = supabase.table("memos").select("*").order("created_at", desc=True).limit(50).execute()
    return result.data or []

@safe_db_call
def add_memo(content: str, pinned: bool = False) -> None:
    supabase.table("memos").insert({"content": content, "pinned": pinned}).execute()

@safe_db_call
def delete_memo(memo_id: int) -> None:
    supabase.table("memos").delete().eq("id", memo_id).execute()

@safe_db_call
def toggle_pin_memo(memo_id: int, pinned: bool) -> None:
    supabase.table("memos").update({"pinned": not pinned}).eq("id", memo_id).execute()

@safe_db_call
def load_completed_today_count() -> int:
    result = supabase.table("tasks").select("id", count="exact").eq(
        "is_completed", True
    ).gte(
        "completed_at", now_kst().replace(hour=0, minute=0, second=0).isoformat()
    ).execute()
    return result.count or 0

@safe_db_call
def load_completed_tasks(limit: int = 100) -> list[dict]:
    result = supabase.table("tasks").select("*").eq(
        "is_completed", True
    ).order("completed_at", desc=True).limit(limit).execute()
    return result.data or []

@safe_db_call
def load_all_tags() -> list[str]:
    """모든 업무에서 사용된 태그 수집"""
    result = supabase.table("tasks").select("tags").execute()
    all_tags = []
    for row in (result.data or []):
        all_tags.extend(parse_tags(row.get("tags")))
    return list(set(all_tags))


# ============================================
# 달력 헬퍼
# ============================================
def build_task_date_map(tasks: list[dict]) -> dict[str, list[dict]]:
    date_map: dict[str, list[dict]] = {}
    for t in tasks:
        dl = parse_deadline_kst(t.get("deadline"))
        if dl:
            key = dl.strftime("%Y-%m-%d")
            date_map.setdefault(key, []).append(t)
    return date_map

def render_monthly_calendar(
    year: int, month: int, task_date_map: dict,
    today_str: str, selected_date: Optional[str] = None,
) -> str:
    cal = calendar.Calendar(firstweekday=6)
    days_in_month = list(cal.itermonthdays2(year, month))
    dow_names = ["일", "월", "화", "수", "목", "금", "토"]
    html = '<div class="cal-grid">'
    for i, d in enumerate(dow_names):
        cls = "cal-dow"
        if i == 0: cls += " cal-dow-sun"
        if i == 6: cls += " cal-dow-sat"
        html += f'<div class="{cls}">{d}</div>'
    for day, weekday in days_in_month:
        if day == 0:
            html += '<div class="cal-day cal-day-empty"></div>'
            continue
        date_key = f"{year}-{month:02d}-{day:02d}"
        adjusted_wd = (weekday + 1) % 7
        cls = "cal-day"
        if date_key == today_str:
            cls += " cal-day-today"
        elif adjusted_wd == 0:
            cls += " cal-day-sun"
        elif adjusted_wd == 6:
            cls += " cal-day-sat"
        if date_key == selected_date:
            cls += " cal-day-selected"
        dots_html = ""
        if date_key in task_date_map:
            dots = []
            for t in task_date_map[date_key][:3]:
                if t.get("is_completed"):
                    dots.append('<span class="cal-dot cal-dot-completed"></span>')
                else:
                    urg, _ = get_urgency(t.get("deadline"))
                    dots.append(f'<span class="cal-dot cal-dot-{urg}"></span>')
            dots_html = f'<div class="cal-dots">{"".join(dots)}</div>'
        html += f'<div class="{cls}">{day}{dots_html}</div>'
    html += '</div>'
    return html

def render_weekly_view(task_date_map: dict) -> str:
    now = now_kst()
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    dow_names = ["월", "화", "수", "목", "금", "토", "일"]
    html = ""
    for i in range(7):
        d = monday + timedelta(days=i)
        date_key = d.strftime("%Y-%m-%d")
        is_today = d == today
        card_cls = "week-day-card-today" if is_today else ""
        header_cls = "week-day-header-today" if is_today else ""
        today_badge = " · 오늘" if is_today else ""
        html += f'<div class="week-day-card {card_cls}">'
        html += f'<div class="week-day-header {header_cls}">{d.strftime("%m/%d")} ({dow_names[i]}){today_badge}</div>'
        day_tasks = task_date_map.get(date_key, [])
        if day_tasks:
            for t in day_tasks[:5]:
                if t.get("is_completed"):
                    html += f'<div class="week-task-item" style="text-decoration:line-through; color:var(--text-faint);">✅ {t["title"]}</div>'
                else:
                    urg, _ = get_urgency(t.get("deadline"))
                    pri_icon = PRIORITIES.get(t.get("priority", "중간"), "")
                    dl = parse_deadline_kst(t.get("deadline"))
                    time_str = dl.strftime("%H:%M") if dl else ""
                    html += f'<div class="week-task-item week-task-item-{urg}">{pri_icon} {t["title"]} <span style="color:var(--text-faint); font-size:0.72rem;">{time_str}</span></div>'
            if len(day_tasks) > 5:
                html += f'<div class="week-no-task">외 {len(day_tasks)-5}건 더</div>'
        else:
            html += '<div class="week-no-task">일정 없음</div>'
        html += '</div>'
    return html


# ============================================
# 차트/리포트 헬퍼
# ============================================
def render_category_chart(active_tasks: list[dict], completed_tasks: list[dict]) -> str:
    """카테고리별 진행/완료 스택바 차트 HTML"""
    cats = [c for c in CATEGORIES if c != "전체"]
    active_by_cat = Counter(t.get("category", "기타") for t in active_tasks)
    completed_by_cat = Counter(t.get("category", "기타") for t in completed_tasks)
    max_total = max((active_by_cat.get(c, 0) + completed_by_cat.get(c, 0)) for c in cats) if cats else 1
    max_total = max(max_total, 1)

    html = ""
    for cat in cats:
        a = active_by_cat.get(cat, 0)
        comp = completed_by_cat.get(cat, 0)
        total = a + comp
        color = CATEGORY_COLORS.get(cat, "#8b5cf6")
        a_pct = (a / max_total * 100) if max_total > 0 else 0
        c_pct = (comp / max_total * 100) if max_total > 0 else 0
        a_label = str(a) if a > 0 and a_pct > 8 else ""
        c_label = str(comp) if comp > 0 and c_pct > 8 else ""

        html += f"""<div class="chart-bar-row">
            <div class="chart-bar-label">{cat}</div>
            <div class="chart-bar-track">
                <div class="chart-bar-segment" style="width:{a_pct}%; background:{color};">{a_label}</div>
                <div class="chart-bar-segment" style="width:{c_pct}%; background:{color}; opacity:0.4;">{c_label}</div>
            </div>
            <div class="chart-bar-count">{total}</div>
        </div>"""
    html += """<div style="display:flex; gap:1rem; justify-content:center; margin-top:0.5rem; font-size:0.7rem; color:var(--text-faint);">
        <span>■ 진행 중</span> <span style="opacity:0.4;">■ 완료</span>
    </div>"""
    return html

def render_time_chart(all_tasks: list[dict]) -> str:
    """카테고리별 투자 시간 차트"""
    cats = [c for c in CATEGORIES if c != "전체"]
    time_by_cat: dict[str, float] = defaultdict(float)

    for t in all_tasks:
        started = t.get("timer_started_at")
        ended = t.get("timer_ended_at")
        if started:
            end_time = ended or now_kst().isoformat()
            mins = calc_duration_minutes(started, end_time)
            cat = t.get("category", "기타")
            time_by_cat[cat] += mins

    max_mins = max(time_by_cat.values()) if time_by_cat else 1
    max_mins = max(max_mins, 1)

    if not any(time_by_cat.get(c, 0) > 0 for c in cats):
        return '<div style="text-align:center; color:var(--text-faint); font-size:0.85rem; padding:1rem;">아직 시간 기록이 없습니다. 업무에서 ▶️ 시작을 눌러보세요.</div>'

    html = ""
    for cat in cats:
        mins = time_by_cat.get(cat, 0)
        if mins == 0:
            continue
        pct = mins / max_mins * 100
        color = CATEGORY_COLORS.get(cat, "#8b5cf6")
        html += f"""<div class="time-chart-row">
            <div class="time-chart-label">{cat}</div>
            <div class="time-chart-bar" style="width:{max(pct, 5)}%; background:{color};">{format_minutes(mins)}</div>
        </div>"""
    return html

def build_weekly_report(completed_tasks: list[dict], all_tasks: list[dict]) -> dict:
    """이번 주 리포트 데이터"""
    now = now_kst()
    monday = now.date() - timedelta(days=now.date().weekday())
    sunday = monday + timedelta(days=6)

    week_completed = []
    for t in completed_tasks:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca and monday <= ca.date() <= sunday:
            week_completed.append(t)

    # 소요시간 합계
    total_mins = 0.0
    for t in week_completed:
        total_mins += calc_duration_minutes(t.get("timer_started_at"), t.get("timer_ended_at"))

    # 카테고리별 완료
    cat_counts = Counter(t.get("category", "기타") for t in week_completed)

    # 일별 완료 수
    daily_counts = defaultdict(int)
    for t in week_completed:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca:
            daily_counts[ca.strftime("%m/%d")] += 1

    return {
        "period": f"{monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')}",
        "total_completed": len(week_completed),
        "total_minutes": total_mins,
        "cat_counts": dict(cat_counts),
        "daily_counts": dict(daily_counts),
        "tasks": week_completed,
    }

def build_monthly_report(completed_tasks: list[dict], all_tasks: list[dict]) -> dict:
    """이번 달 리포트 데이터"""
    now = now_kst()
    year, month = now.year, now.month

    month_completed = []
    for t in completed_tasks:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca and ca.year == year and ca.month == month:
            month_completed.append(t)

    total_mins = 0.0
    for t in month_completed:
        total_mins += calc_duration_minutes(t.get("timer_started_at"), t.get("timer_ended_at"))

    cat_counts = Counter(t.get("category", "기타") for t in month_completed)

    # 주차별 완료
    weekly_counts = defaultdict(int)
    for t in month_completed:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca:
            week_num = (ca.day - 1) // 7 + 1
            weekly_counts[f"{week_num}주차"] += 1

    return {
        "period": f"{year}년 {month}월",
        "total_completed": len(month_completed),
        "total_minutes": total_mins,
        "cat_counts": dict(cat_counts),
        "weekly_counts": dict(weekly_counts),
        "tasks": month_completed,
    }


# ============================================
# 비밀번호 잠금
# ============================================
def check_password() -> bool:
    if st.session_state.authenticated:
        return True
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🗂️</div>
        <h1 style="font-size: 1.8rem; font-weight: 700; color: var(--text-primary);">My AI Desk</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">CSR팀 업무 비서</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("비밀번호를 입력하세요", type="password", key="pwd_input")
        if st.button("로그인", use_container_width=True, type="primary"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    return False

if not check_password():
    st.stop()


# ============================================
# 사이드바
# ============================================
with st.sidebar:
    st.markdown("### 📝 퀵 메모")
    memo_input = st.text_area("메모", placeholder="번뜩이는 아이디어, URL, 메모...", height=80, label_visibility="collapsed")
    memo_cols = st.columns([3, 1])
    with memo_cols[0]:
        if st.button("💾 저장", use_container_width=True, type="primary"):
            if memo_input.strip():
                add_memo(memo_input.strip())
                st.toast("✅ 메모 저장!")
                st.rerun()
    with memo_cols[1]:
        if st.button("📌 고정", use_container_width=True):
            if memo_input.strip():
                add_memo(memo_input.strip(), pinned=True)
                st.toast("📌 고정 메모 저장!")
                st.rerun()

    memos = load_memos() or []
    pinned = [m for m in memos if m.get("pinned")]
    unpinned = [m for m in memos if not m.get("pinned")]

    for label, group, is_pinned in [
        ("📌 고정 메모", pinned, True),
        ("최근 메모", unpinned[:8], False),
    ]:
        if not group:
            continue
        color = "var(--yellow)" if is_pinned else "var(--text-faint)"
        st.markdown(f"<div style='font-size:0.78rem; color:{color}; margin:0.5rem 0; font-weight:600;'>{label} ({len(group)}건)</div>", unsafe_allow_html=True)
        for memo in group:
            col_m, col_p, col_d = st.columns([5, 1, 1])
            with col_m:
                border_style = "border-color: rgba(236,201,75,0.5);" if is_pinned else ""
                st.markdown(f"""<div class="memo-item" style="{border_style}">
                    {memo['content'][:120]}{'...' if len(memo['content']) > 120 else ''}
                    <div class="memo-time">{format_dt(memo['created_at'])}</div>
                </div>""", unsafe_allow_html=True)
            with col_p:
                icon = "📌" if not is_pinned else "📌"
                help_text = "고정" if not is_pinned else "고정 해제"
                if st.button(icon, key=f"pin_{memo['id']}", help=help_text):
                    toggle_pin_memo(memo['id'], is_pinned)
                    st.rerun()
            with col_d:
                if st.button("🗑", key=f"del_memo_{memo['id']}", help="삭제"):
                    delete_memo(memo['id'])
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 검색 & 필터")
    search_query = st.text_input("검색", placeholder="제목, 내용, 태그...", label_visibility="collapsed")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        st.session_state.filter_category = st.selectbox(
            "카테고리", CATEGORIES,
            index=CATEGORIES.index(st.session_state.filter_category),
        )
    with filter_col2:
        priority_options = ["전체"] + list(PRIORITIES.keys())
        current_pri = st.session_state.filter_priority
        if current_pri not in priority_options:
            current_pri = "전체"
        st.session_state.filter_priority = st.selectbox(
            "우선순위", priority_options,
            index=priority_options.index(current_pri),
        )

    # 태그 필터
    all_tags = load_all_tags() or []
    if all_tags:
        tag_options = [""] + sorted(all_tags)
        st.session_state.filter_tag = st.selectbox(
            "🏷️ 태그 필터", tag_options,
            format_func=lambda x: "전체" if x == "" else f"#{x}",
        )
    else:
        st.session_state.filter_tag = ""

    st.session_state.sort_by = st.radio(
        "정렬", ["마감일순", "우선순위순", "등록순"],
        index=["마감일순", "우선순위순", "등록순"].index(st.session_state.sort_by),
        horizontal=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:var(--text-faint);'>"
        "My AI Desk v3.0<br>CSR Team Edition</div>",
        unsafe_allow_html=True,
    )


# ============================================
# 메인 헤더
# ============================================
st.markdown("""
<div style="display:flex; align-items:center; gap:0.7rem; margin-bottom:0.3rem;">
    <span style="font-size:2rem;">🗂️</span>
    <div>
        <h1 style="margin:0; font-size:1.6rem; font-weight:700; color:var(--text-primary);">My AI Desk</h1>
        <p style="margin:0; font-size:0.85rem; color:var(--text-muted);">CSR팀 업무 비서</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================
# 데이터 로드 (한 번만)
# ============================================
all_active_tasks = load_tasks(show_completed=False, search_query="", category="전체", priority="전체") or []
all_completed = load_completed_tasks(100) or []
completed_today = load_completed_today_count() or 0

overdue_count = sum(1 for t in all_active_tasks if get_urgency(t.get("deadline"))[0] == "overdue")
today_count = sum(1 for t in all_active_tasks if get_urgency(t.get("deadline"))[0] == "today")
total_active = len(all_active_tasks)
total_today_scope = today_count + completed_today
completion_rate = int((completed_today / total_today_scope * 100)) if total_today_scope > 0 else 0


# ============================================
# 통계 대시보드
# ============================================
st.markdown(f"""
<div class="stat-grid">
    <div class="stat-box">
        <div class="stat-number" style="color:var(--blue);">{total_active}</div>
        <div class="stat-label">진행 중</div>
    </div>
    <div class="stat-box">
        <div class="stat-number" style="color:var(--red);">{overdue_count}</div>
        <div class="stat-label">기한 초과</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{min(overdue_count * 10, 100)}%; background:var(--red);"></div></div>
    </div>
    <div class="stat-box">
        <div class="stat-number" style="color:var(--orange);">{today_count}</div>
        <div class="stat-label">오늘 마감</div>
    </div>
    <div class="stat-box">
        <div class="stat-number" style="color:var(--green);">{completed_today}</div>
        <div class="stat-label">오늘 완료</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{completion_rate}%; background:var(--green);"></div></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================
# 📊 카테고리별 현황 + ⏱️ 시간 투자 분석
# ============================================
with st.expander("📊 업무 현황 & 시간 분석", expanded=True):
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**카테고리별 업무 현황**")
        chart_html = render_category_chart(all_active_tasks, all_completed)
        st.markdown(f'<div class="chart-container">{chart_html}</div>', unsafe_allow_html=True)

    with chart_col2:
        st.markdown("**⏱️ 카테고리별 시간 투자**")
        all_for_time = load_all_tasks() or []
        time_html = render_time_chart(all_for_time)
        st.markdown(f'<div class="chart-container">{time_html}</div>', unsafe_allow_html=True)


# ============================================
# 📋 업무 히스토리 & 리포트
# ============================================
with st.expander("📋 업무 히스토리 & 리포트", expanded=False):
    report_tab1, report_tab2, report_tab3 = st.tabs(["📅 주간 리포트", "📆 월간 리포트", "📜 타임라인"])

    with report_tab1:
        wr = build_weekly_report(all_completed, all_active_tasks)
        st.markdown(f"**{wr['period']}**")
        st.markdown(f"""
        <div class="report-grid">
            <div class="report-box">
                <div class="report-number" style="color:var(--green);">{wr['total_completed']}</div>
                <div class="report-label">완료 업무</div>
            </div>
            <div class="report-box">
                <div class="report-number" style="color:var(--accent);">{format_minutes(wr['total_minutes'])}</div>
                <div class="report-label">총 투자 시간</div>
            </div>
            <div class="report-box">
                <div class="report-number" style="color:var(--orange);">{format_minutes(wr['total_minutes'] / max(wr['total_completed'], 1))}</div>
                <div class="report-label">건당 평균</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if wr['cat_counts']:
            st.markdown("**카테고리별 완료**")
            for cat, cnt in sorted(wr['cat_counts'].items(), key=lambda x: x[1], reverse=True):
                color = CATEGORY_COLORS.get(cat, "#8b5cf6")
                st.markdown(f"<span style='color:{color}; font-weight:600;'>●</span> {cat}: {cnt}건", unsafe_allow_html=True)

        if wr['daily_counts']:
            st.markdown("**일별 완료 추이**")
            max_daily = max(wr['daily_counts'].values()) if wr['daily_counts'] else 1
            for day_str, cnt in sorted(wr['daily_counts'].items()):
                pct = cnt / max_daily * 100
                st.markdown(
                    f'<div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.2rem;">'
                    f'<span style="font-size:0.78rem; min-width:40px; color:var(--text-muted);">{day_str}</span>'
                    f'<div style="height:14px; width:{max(pct, 8)}%; background:var(--accent); border-radius:3px; display:flex; align-items:center; padding:0 6px;">'
                    f'<span style="font-size:0.65rem; color:white;">{cnt}</span></div></div>',
                    unsafe_allow_html=True,
                )

        if not wr['total_completed']:
            st.caption("이번 주 완료된 업무가 없습니다.")

    with report_tab2:
        mr = build_monthly_report(all_completed, all_active_tasks)
        st.markdown(f"**{mr['period']}**")
        st.markdown(f"""
        <div class="report-grid">
            <div class="report-box">
                <div class="report-number" style="color:var(--green);">{mr['total_completed']}</div>
                <div class="report-label">완료 업무</div>
            </div>
            <div class="report-box">
                <div class="report-number" style="color:var(--accent);">{format_minutes(mr['total_minutes'])}</div>
                <div class="report-label">총 투자 시간</div>
            </div>
            <div class="report-box">
                <div class="report-number" style="color:var(--orange);">{format_minutes(mr['total_minutes'] / max(mr['total_completed'], 1))}</div>
                <div class="report-label">건당 평균</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if mr['cat_counts']:
            st.markdown("**카테고리별 완료**")
            for cat, cnt in sorted(mr['cat_counts'].items(), key=lambda x: x[1], reverse=True):
                color = CATEGORY_COLORS.get(cat, "#8b5cf6")
                st.markdown(f"<span style='color:{color}; font-weight:600;'>●</span> {cat}: {cnt}건", unsafe_allow_html=True)

        if mr['weekly_counts']:
            st.markdown("**주차별 완료 추이**")
            for week, cnt in sorted(mr['weekly_counts'].items()):
                st.markdown(f"- {week}: **{cnt}건**")

        if not mr['total_completed']:
            st.caption("이번 달 완료된 업무가 없습니다.")

    with report_tab3:
        st.markdown("**최근 완료 타임라인**")
        if all_completed:
            for ct in all_completed[:20]:
                ca = parse_deadline_kst(ct.get("completed_at"))
                date_str = ca.strftime("%m/%d %H:%M") if ca else ""
                duration = calc_duration(ct.get("created_at"), ct.get("completed_at"))
                cat = ct.get("category", "기타")
                color = CATEGORY_COLORS.get(cat, "#8b5cf6")
                tags = parse_tags(ct.get("tags"))
                tag_html = " ".join(f'<span class="badge-tag">#{t}</span>' for t in tags)

                # 타이머 기반 소요시간
                timer_mins = calc_duration_minutes(ct.get("timer_started_at"), ct.get("timer_ended_at"))
                timer_str = f" · ⏱ {format_minutes(timer_mins)}" if timer_mins > 0 else ""

                st.markdown(f"""<div class="timeline-item">
                    <div class="timeline-date">{date_str}</div>
                    <div class="timeline-content">
                        <div class="timeline-title">
                            <span style="color:{color};">●</span> {ct['title']}
                        </div>
                        <div class="timeline-detail">
                            {cat}{' · 소요: ' + duration if duration else ''}{timer_str}
                            {' · ' + tag_html if tag_html else ''}
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.caption("아직 완료된 업무가 없습니다.")


# ============================================
# 📅 달력
# ============================================
with st.expander("📅 달력", expanded=True):
    cal_tasks = load_all_tasks() or []
    task_date_map = build_task_date_map(cal_tasks)
    now = now_kst()
    today_str = now.strftime("%Y-%m-%d")

    cal_tab1, cal_tab2 = st.tabs(["📆 월간", "📋 주간"])

    with cal_tab1:
        nav1, nav2, nav3, nav4 = st.columns([1, 3, 3, 1])
        with nav1:
            if st.button("◀", key="cal_prev", use_container_width=True):
                if st.session_state.cal_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
        with nav2:
            st.markdown(
                f"<div style='text-align:right; font-size:1.1rem; font-weight:700; color:var(--text-primary); padding:0.3rem 0;'>"
                f"{st.session_state.cal_year}년 {st.session_state.cal_month}월</div>",
                unsafe_allow_html=True,
            )
        with nav3:
            if st.session_state.cal_year != now.year or st.session_state.cal_month != now.month:
                if st.button("오늘", key="cal_today", use_container_width=True):
                    st.session_state.cal_year = now.year
                    st.session_state.cal_month = now.month
                    st.session_state.selected_date = None
                    st.rerun()
        with nav4:
            if st.button("▶", key="cal_next", use_container_width=True):
                if st.session_state.cal_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()

        cal_html = render_monthly_calendar(
            st.session_state.cal_year, st.session_state.cal_month,
            task_date_map, today_str, st.session_state.selected_date,
        )
        st.markdown(f'<div class="cal-container">{cal_html}</div>', unsafe_allow_html=True)

        y, m = st.session_state.cal_year, st.session_state.cal_month
        max_day = calendar.monthrange(y, m)[1]
        day_options = ["선택 안 함"] + [f"{m}/{d}" for d in range(1, max_day + 1)]
        selected_idx = 0
        if st.session_state.selected_date:
            try:
                sd = datetime.strptime(st.session_state.selected_date, "%Y-%m-%d")
                if sd.year == y and sd.month == m:
                    selected_idx = sd.day
            except ValueError:
                pass
        picked = st.selectbox("📅 날짜 선택하여 업무 보기", day_options, index=selected_idx, key="date_picker")
        if picked == "선택 안 함":
            st.session_state.selected_date = None
        else:
            day_num = int(picked.split("/")[1])
            st.session_state.selected_date = f"{y}-{m:02d}-{day_num:02d}"

        if st.session_state.selected_date and st.session_state.selected_date in task_date_map:
            sel_tasks = task_date_map[st.session_state.selected_date]
            st.markdown(f'<div class="selected-date-header">📋 {st.session_state.selected_date} 업무 ({len(sel_tasks)}건)</div>', unsafe_allow_html=True)
            for t in sel_tasks:
                urg, _ = get_urgency(t.get("deadline"))
                status = "✅" if t.get("is_completed") else PRIORITIES.get(t.get("priority", "중간"), "")
                dl = parse_deadline_kst(t.get("deadline"))
                time_str = dl.strftime("%H:%M") if dl else ""
                st.markdown(
                    f'<div class="task-card {urg if not t.get("is_completed") else "completed-card"}" style="margin-bottom:0.4rem; padding:0.7rem 1rem;">'
                    f'<div class="task-header"><span class="task-title" style="font-size:0.9rem;">{status} {t["title"]}</span>'
                    f'<span style="font-size:0.75rem; color:var(--text-muted);">{time_str}</span></div></div>',
                    unsafe_allow_html=True,
                )
        elif st.session_state.selected_date:
            st.caption(f"{st.session_state.selected_date}에 등록된 업무가 없습니다.")

        st.markdown("""
        <div style="display:flex; gap:1rem; justify-content:center; margin-top:0.6rem; font-size:0.72rem; color:var(--text-faint);">
            <span><span class="cal-dot cal-dot-overdue" style="display:inline-block;"></span> 기한초과</span>
            <span><span class="cal-dot cal-dot-today" style="display:inline-block;"></span> 오늘마감</span>
            <span><span class="cal-dot cal-dot-upcoming" style="display:inline-block;"></span> 예정</span>
            <span><span class="cal-dot cal-dot-completed" style="display:inline-block;"></span> 완료</span>
        </div>
        """, unsafe_allow_html=True)

    with cal_tab2:
        weekday = now.date().weekday()
        monday = now.date() - timedelta(days=weekday)
        sunday = monday + timedelta(days=6)
        st.markdown(
            f"<div style='text-align:center; font-size:1rem; font-weight:600; color:var(--text-primary); margin-bottom:0.5rem;'>"
            f"📋 {monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')} 이번 주</div>",
            unsafe_allow_html=True,
        )
        st.markdown(render_weekly_view(task_date_map), unsafe_allow_html=True)


# ============================================
# ➕ 새 업무 등록
# ============================================
with st.expander("➕ 새 업무 등록", expanded=False):
    with st.form("add_task_form", clear_on_submit=True):
        new_title = st.text_input("업무명 *", placeholder="예: 공정거래 자율준수 점검, 동반성장 협력사 간담회")
        new_desc = st.text_area(
            "상세 내용", height=200,
            placeholder="마크다운 체크리스트, 메모, 담당자 정보 등 자유롭게 작성\n\n- [ ] 할 일 1\n- [ ] 할 일 2",
        )

        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            new_date = st.date_input("마감일", value=None)
        with reg_col2:
            new_time = st.time_input("마감 시간", value=None)

        reg_col3, reg_col4, reg_col5 = st.columns(3)
        with reg_col3:
            categories_no_all = [c for c in CATEGORIES if c != "전체"]
            new_category = st.selectbox("카테고리", categories_no_all, index=0)
        with reg_col4:
            priority_list = list(PRIORITIES.keys())
            new_priority = st.selectbox("우선순위", priority_list, index=1,
                format_func=lambda x: f"{PRIORITIES[x]} {x}")
        with reg_col5:
            recurrence_keys = list(RECURRENCE_OPTIONS.keys())
            new_recurrence_label = st.selectbox("반복", recurrence_keys, index=0)
            new_recurrence = RECURRENCE_OPTIONS[new_recurrence_label]

        new_tags_input = st.text_input(
            "🏷️ 태그",
            placeholder="#급함 #보고용 #협력사  (콤마 또는 공백으로 구분)",
        )
        new_tags = ", ".join(parse_tags(new_tags_input))

        submitted = st.form_submit_button("📌 업무 등록", use_container_width=True, type="primary")
        if submitted:
            if new_title.strip():
                deadline = None
                if new_date:
                    t = new_time if new_time else dt_time(18, 0)
                    deadline = datetime.combine(new_date, t).replace(tzinfo=KST)
                add_task(
                    new_title.strip(), new_desc.strip(), deadline,
                    new_category, new_priority, new_recurrence, new_tags,
                )
                st.toast("✅ 업무가 등록되었습니다!")
                st.balloons()
                st.rerun()
            else:
                st.warning("업무명을 입력해주세요.")


# ============================================
# 📌 업무 목록
# ============================================
active_filter_parts = []
if st.session_state.filter_category != "전체":
    active_filter_parts.append(f"카테고리: {st.session_state.filter_category}")
if st.session_state.filter_priority != "전체":
    active_filter_parts.append(f"우선순위: {st.session_state.filter_priority}")
if st.session_state.filter_tag:
    active_filter_parts.append(f"태그: #{st.session_state.filter_tag}")
if search_query:
    active_filter_parts.append(f"검색: \"{search_query}\"")

filter_info = f" · <span class='filter-active'>{' | '.join(active_filter_parts)}</span>" if active_filter_parts else ""
st.markdown(f"### 📌 진행 중인 업무{filter_info}", unsafe_allow_html=True)

tasks = load_tasks(
    show_completed=False, search_query=search_query,
    category=st.session_state.filter_category,
    priority=st.session_state.filter_priority,
    tag_filter=st.session_state.filter_tag,
) or []

if st.session_state.sort_by == "우선순위순":
    tasks.sort(key=lambda t: PRIORITY_ORDER.get(t.get("priority", "중간"), 1))
elif st.session_state.sort_by == "등록순":
    tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)

if not tasks:
    if search_query or active_filter_parts:
        st.info("조건에 맞는 업무가 없습니다. 필터를 조정해보세요.")
    else:
        st.info("등록된 업무가 없습니다. 위에서 새 업무를 등록해보세요! 🎯")
else:
    for task in tasks:
        urgency, urgency_label = get_urgency(task.get("deadline"))
        pri = task.get("priority", "중간")
        pri_icon = PRIORITIES.get(pri, "")
        recurrence = task.get("recurrence")
        tags = parse_tags(task.get("tags"))

        # 체크리스트 진행률
        progress_html = ""
        prog = calc_checklist_progress(task.get("description"))
        if prog:
            pct = int(prog[0] / prog[1] * 100) if prog[1] > 0 else 0
            progress_html = (
                f'<span class="progress-inline">'
                f'<span class="progress-bar-mini"><span class="progress-bar-mini-fill" style="width:{pct}%;"></span></span>'
                f'<span style="font-size:0.72rem;">{prog[0]}/{prog[1]}</span></span>'
            )

        urgency_html = ""
        if urgency_label:
            urgency_html = f'<span class="urgency-tag urgency-{urgency}">{urgency_label}</span>'

        # 태그 뱃지
        tag_badges = " ".join(f'<span class="badge-tag">#{t}</span>' for t in tags[:4])

        # 타이머 상태
        timer_html = ""
        if task.get("timer_started_at") and not task.get("timer_ended_at"):
            elapsed = calc_duration_minutes(task["timer_started_at"], now_kst().isoformat())
            timer_html = f'<span class="timer-active">⏱ {format_minutes(elapsed)} 진행 중</span>'
        elif task.get("timer_started_at") and task.get("timer_ended_at"):
            elapsed = calc_duration_minutes(task["timer_started_at"], task["timer_ended_at"])
            timer_html = f'<span style="font-size:0.75rem; color:var(--text-muted);">⏱ {format_minutes(elapsed)}</span>'

        card_html = (
            f'<div class="task-card {urgency}">'
            f'<div class="task-header">'
            f'<span class="task-title">{pri_icon} {task["title"]}</span>'
            f'<div class="task-badges">'
            f'<span class="badge badge-priority-{pri}">{pri}</span>'
            f'<span class="badge">{task.get("category","기타")}</span>'
            f'{tag_badges}'
            f'</div></div>'
            f'<div class="task-meta">'
            f'<span>{("📅 " + format_dt(task["deadline"])) if task.get("deadline") else "📅 마감일 미지정"}</span>'
            f'{urgency_html}'
            f'{progress_html}'
            f'{timer_html}'
            f'{"<span>🔁 반복</span>" if recurrence else ""}'
            f'</div></div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        with st.expander(f"상세 보기 · {task['title']}", expanded=False):
            if task.get("description"):
                st.markdown(task["description"])
            else:
                st.caption("상세 내용 없음")

            if tags:
                st.markdown("🏷️ " + " ".join(f"`#{t}`" for t in tags))

            # ⏱️ 타이머 컨트롤
            st.markdown("**⏱️ 소요시간 트래킹**")
            timer_col1, timer_col2, timer_col3 = st.columns(3)
            has_started = bool(task.get("timer_started_at"))
            has_ended = bool(task.get("timer_ended_at"))
            is_running = has_started and not has_ended

            with timer_col1:
                if not has_started:
                    if st.button("▶️ 시작", key=f"timer_start_{task['id']}", use_container_width=True):
                        start_timer(task["id"])
                        st.toast("⏱ 타이머 시작!")
                        st.rerun()
                elif is_running:
                    elapsed = calc_duration_minutes(task["timer_started_at"], now_kst().isoformat())
                    st.markdown(f"🔴 **진행 중** · {format_minutes(elapsed)}")
                else:
                    elapsed = calc_duration_minutes(task["timer_started_at"], task["timer_ended_at"])
                    st.markdown(f"✅ **기록 완료** · {format_minutes(elapsed)}")

            with timer_col2:
                if is_running:
                    if st.button("⏹ 정지", key=f"timer_stop_{task['id']}", use_container_width=True):
                        stop_timer(task["id"])
                        st.toast("⏱ 타이머 정지!")
                        st.rerun()

            with timer_col3:
                if has_started:
                    if st.button("🔄 초기화", key=f"timer_reset_{task['id']}", use_container_width=True):
                        reset_timer(task["id"])
                        st.toast("⏱ 타이머 초기화!")
                        st.rerun()

            st.markdown("---")

            # 완료/수정/삭제
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button("✅ 완료 처리", key=f"done_{task['id']}", use_container_width=True, type="primary"):
                    complete_task(task)
                    msg = "🎉 완료! 다음 회차 자동 생성됨" if task.get("recurrence") else "🎉 수고하셨습니다!"
                    st.toast(msg)
                    st.balloons()
                    st.rerun()
            with col2:
                if st.button("✏️ 수정", key=f"edit_{task['id']}", use_container_width=True):
                    st.session_state[f"editing_{task['id']}"] = True
                    st.rerun()
            with col3:
                if st.button("🗑️ 삭제", key=f"del_{task['id']}", use_container_width=True):
                    delete_task(task["id"])
                    st.toast("업무가 삭제되었습니다.")
                    st.rerun()

            # 수정 폼
            if st.session_state.get(f"editing_{task['id']}", False):
                st.markdown("---")
                st.markdown("**✏️ 업무 수정**")
                edit_title = st.text_input("업무명", value=task["title"], key=f"et_{task['id']}")
                edit_desc = st.text_area("상세 내용", value=task.get("description", ""), height=150, key=f"ed_{task['id']}")

                edit_date, edit_time = None, None
                dl = parse_deadline_kst(task.get("deadline"))
                if dl:
                    edit_date = st.date_input("마감일", value=dl.date(), key=f"edt_{task['id']}")
                    edit_time = st.time_input("마감 시간", value=dl.time(), key=f"etm_{task['id']}")
                else:
                    edit_date = st.date_input("마감일", value=None, key=f"edt_{task['id']}")
                    edit_time = st.time_input("마감 시간", value=None, key=f"etm_{task['id']}")

                edit_col1, edit_col2, edit_col3 = st.columns(3)
                categories_no_all = [c for c in CATEGORIES if c != "전체"]
                with edit_col1:
                    edit_cat = st.selectbox("카테고리", categories_no_all,
                        index=categories_no_all.index(task.get("category", "기타")) if task.get("category", "기타") in categories_no_all else 0,
                        key=f"ec_{task['id']}")
                with edit_col2:
                    edit_pri = st.selectbox("우선순위", list(PRIORITIES.keys()),
                        index=list(PRIORITIES.keys()).index(task.get("priority", "중간")) if task.get("priority", "중간") in PRIORITIES else 1,
                        key=f"ep_{task['id']}",
                        format_func=lambda x: f"{PRIORITIES[x]} {x}")
                with edit_col3:
                    current_rec = task.get("recurrence")
                    rec_keys = list(RECURRENCE_OPTIONS.keys())
                    rec_idx = 0
                    if current_rec:
                        for i, k in enumerate(rec_keys):
                            if RECURRENCE_OPTIONS[k] == current_rec:
                                rec_idx = i
                                break
                    edit_rec_label = st.selectbox("반복", rec_keys, index=rec_idx, key=f"er_{task['id']}")
                    edit_rec = RECURRENCE_OPTIONS[edit_rec_label]

                edit_tags_input = st.text_input(
                    "🏷️ 태그", value=task.get("tags", ""),
                    key=f"etag_{task['id']}",
                    placeholder="#급함 #보고용 #협력사",
                )
                edit_tags = ", ".join(parse_tags(edit_tags_input))

                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    if st.button("💾 저장", key=f"save_{task['id']}", use_container_width=True, type="primary"):
                        deadline = None
                        if edit_date:
                            t = edit_time if edit_time else dt_time(18, 0)
                            deadline = datetime.combine(edit_date, t).replace(tzinfo=KST)
                        update_task(task["id"], edit_title, edit_desc, deadline, edit_cat, edit_pri, edit_rec, edit_tags)
                        st.session_state[f"editing_{task['id']}"] = False
                        st.toast("✅ 수정 완료!")
                        st.rerun()
                with ecol2:
                    if st.button("취소", key=f"cancel_{task['id']}", use_container_width=True):
                        st.session_state[f"editing_{task['id']}"] = False
                        st.rerun()


# ============================================
# ✅ 완료된 업무
# ============================================
st.markdown("---")
with st.expander("✅ 완료된 업무 보기"):
    c_tasks = load_completed_tasks(30) or []
    if not c_tasks:
        st.caption("아직 완료된 업무가 없습니다.")
    else:
        for ct in c_tasks:
            duration = calc_duration(ct.get("created_at"), ct.get("completed_at"))
            pri_icon = PRIORITIES.get(ct.get("priority", "중간"), "")
            tags = parse_tags(ct.get("tags"))
            tag_badges = " ".join(f'<span class="badge-tag">#{t}</span>' for t in tags[:3])
            timer_mins = calc_duration_minutes(ct.get("timer_started_at"), ct.get("timer_ended_at"))
            timer_str = f" · ⏱ {format_minutes(timer_mins)}" if timer_mins > 0 else ""

            ct_card = (
                f'<div class="task-card completed-card">'
                f'<div class="task-header">'
                f'<span class="task-title" style="text-decoration: line-through;">{pri_icon} {ct["title"]}</span>'
                f'<div class="task-badges">'
                f'<span class="badge">{ct.get("category","기타")}</span>'
                f'{tag_badges}'
                f'</div></div>'
                f'<div class="task-meta">'
                f'<span>완료: {format_dt(ct["completed_at"])}</span>'
                f'{"<span>⏱ " + duration + "</span>" if duration else ""}'
                f'<span>{timer_str}</span>'
                f'</div></div>'
            )
            st.markdown(ct_card, unsafe_allow_html=True)

            col_r1, col_r2 = st.columns([1, 1])
            with col_r1:
                if st.button("↩️ 되돌리기", key=f"undo_{ct['id']}"):
                    uncomplete_task(ct["id"])
                    st.rerun()
            with col_r2:
                if st.button("🗑️ 삭제", key=f"cdel_{ct['id']}"):
                    delete_task(ct["id"])
                    st.rerun()
