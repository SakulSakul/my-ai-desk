import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta, timezone, time as dt_time
import calendar
import json
from typing import Optional
from dataclasses import dataclass, field

# ============================================
# 설정
# ============================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "여기에_수파베이스_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "여기에_수파베이스_ANON_KEY")
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

KST = timezone(timedelta(hours=9))

CATEGORIES = ["전체", "일반", "정기보고", "기획", "미팅", "MD", "대외협력", "기타"]
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
# CSS (CSS 변수 기반 테마, 다크모드 대응)
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
    .task-badges { display: flex; gap: 0.3rem; align-items: center; flex-shrink: 0; }
    .badge {
        font-size: 0.7rem; padding: 2px 8px; border-radius: 12px;
        background: var(--bg-secondary); color: var(--text-secondary);
        white-space: nowrap;
    }
    .badge-priority-높음 { background: #fed7d7; color: #c53030; }
    .badge-priority-중간 { background: #fefcbf; color: #975a16; }
    .badge-priority-낮음 { background: #c6f6d5; color: #276749; }
    .task-meta {
        font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;
        display: flex; flex-wrap: wrap; gap: 0.3rem 0.8rem; align-items: center;
    }
    .urgency-tag { font-weight: 600; }
    .urgency-overdue { color: var(--red); }
    .urgency-today { color: var(--orange); }
    .progress-inline {
        display: inline-flex; align-items: center; gap: 0.3rem;
    }
    .progress-bar-mini {
        width: 50px; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden;
    }
    .progress-bar-mini-fill { height: 100%; background: var(--accent); border-radius: 2px; }

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
    .memo-pin { color: var(--yellow); }

    /* ── 선택된 날짜 업무 ── */
    .selected-date-header {
        font-size: 0.95rem; font-weight: 600; color: var(--accent);
        padding: 0.5rem 0; border-bottom: 2px solid var(--accent); margin-bottom: 0.5rem;
    }

    /* ── 필터 영역 ── */
    .filter-active {
        font-size: 0.8rem; color: var(--accent); font-weight: 500;
        padding: 0.3rem 0;
    }

    /* ── 모바일 ── */
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem; }
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
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
def init_session_state():
    defaults = {
        "authenticated": False,
        "cal_year": now_kst().year,
        "cal_month": now_kst().month,
        "selected_date": None,
        "filter_category": "전체",
        "filter_priority": "전체",
        "sort_by": "마감일순",
        "show_completed": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def now_kst() -> datetime:
    return datetime.now(KST)

init_session_state()


# ============================================
# 유틸리티 함수 (타입 힌트 + 에러 핸들링)
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
            mins = diff.seconds // 60
            return "today", f"⚡ {mins}분 남음"
        return "today", f"⚡ {hours}시간 남음"
    elif diff.days <= 3:
        return "upcoming", f"📅 {diff.days}일 남음"
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

def calc_checklist_progress(description: Optional[str]) -> Optional[tuple[int, int]]:
    """마크다운 체크리스트에서 진행률 계산: (완료, 전체)"""
    if not description:
        return None
    total = 0
    checked = 0
    for line in description.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ]") or stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            total += 1
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                checked += 1
    if total == 0:
        return None
    return (checked, total)

def get_next_recurrence_date(current_deadline: datetime, recurrence: str) -> datetime:
    """반복 주기에 따른 다음 마감일 계산"""
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
# DB 함수 (에러 핸들링 강화)
# ============================================
def safe_db_call(func):
    """DB 호출 래퍼 — 에러 시 빈 결과 반환"""
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
                 q in (t.get("category") or "").lower()]
    return tasks

@safe_db_call
def load_all_tasks() -> list[dict]:
    result = supabase.table("tasks").select("*").order("deadline", desc=False).execute()
    return result.data or []

@safe_db_call
def add_task(
    title: str,
    description: str,
    deadline: Optional[datetime],
    category: str,
    priority: str = "중간",
    recurrence: Optional[str] = None,
) -> None:
    data = {
        "title": title,
        "description": description,
        "deadline": deadline.isoformat() if deadline else None,
        "category": category,
        "priority": priority,
        "recurrence": recurrence,
        "is_completed": False,
    }
    supabase.table("tasks").insert(data).execute()

@safe_db_call
def complete_task(task: dict) -> None:
    supabase.table("tasks").update({
        "is_completed": True,
        "completed_at": now_kst().isoformat(),
    }).eq("id", task["id"]).execute()

    # 반복 업무면 다음 회차 자동 생성
    recurrence = task.get("recurrence")
    if recurrence and task.get("deadline"):
        deadline = parse_deadline_kst(task["deadline"])
        if deadline:
            next_deadline = get_next_recurrence_date(deadline, recurrence)
            # 체크리스트 초기화 (체크된 항목을 미체크로)
            desc = task.get("description", "") or ""
            desc = desc.replace("- [x]", "- [ ]").replace("- [X]", "- [ ]")
            add_task(
                title=task["title"],
                description=desc,
                deadline=next_deadline,
                category=task.get("category", "일반"),
                priority=task.get("priority", "중간"),
                recurrence=recurrence,
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
    task_id: int,
    title: str,
    description: str,
    deadline: Optional[datetime],
    category: str,
    priority: str = "중간",
    recurrence: Optional[str] = None,
) -> None:
    data = {
        "title": title,
        "description": description,
        "deadline": deadline.isoformat() if deadline else None,
        "category": category,
        "priority": priority,
        "recurrence": recurrence,
    }
    supabase.table("tasks").update(data).eq("id", task_id).execute()

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
def load_completed_tasks(limit: int = 30) -> list[dict]:
    result = supabase.table("tasks").select("*").eq(
        "is_completed", True
    ).order("completed_at", desc=True).limit(limit).execute()
    return result.data or []


# ============================================
# 템플릿
# ============================================
TEMPLATES = {
    "ISO 경영검토 보고서": {
        "category": "정기보고",
        "priority": "높음",
        "description": """## ISO 경영검토 보고서 체크리스트

- [ ] 전기 경영검토 후속조치 확인
- [ ] 내부/외부 이슈 변화 검토
- [ ] 이해관계자 요구사항 변경 확인
- [ ] 품질목표 달성도 분석
- [ ] 프로세스 성과 및 제품 적합성
- [ ] 부적합 및 시정조치 현황
- [ ] 모니터링/측정 결과
- [ ] 심사 결과 (내부/외부)
- [ ] 외부 공급자 성과
- [ ] 자원의 충분성
- [ ] 리스크/기회 조치 효과성
- [ ] 개선 기회 도출
- [ ] 경영진 승인 및 서명""",
    },
    "사회공헌 프로그램 기획": {
        "category": "기획",
        "priority": "중간",
        "description": """## 사회공헌 프로그램 기획 체크리스트

- [ ] 프로그램 목적 및 배경 정리
- [ ] 대상 지역/수혜자 선정
- [ ] 협력 기관 섭외 및 MOU
- [ ] 예산 수립 (인건비, 물품, 운송 등)
- [ ] 일정표 작성 (D-30, D-7, D-Day)
- [ ] 자원봉사자 모집 및 교육
- [ ] 물품 구매 및 키트 제작
- [ ] 홍보 계획 (사내보, SNS, 보도자료)
- [ ] 현장 운영 매뉴얼 작성
- [ ] 사진/영상 촬영 계획
- [ ] 사후 보고서 작성
- [ ] 참여자 설문 및 피드백 수집""",
    },
    "대외 협력 미팅 준비": {
        "category": "미팅",
        "priority": "높음",
        "description": """## 대외 협력 미팅 준비 체크리스트

- [ ] 미팅 목적 및 안건 정리
- [ ] 참석자 명단 및 연락처 확인
- [ ] 장소 예약 / 화상회의 링크 생성
- [ ] 발표 자료 준비
- [ ] 관련 데이터/실적 취합
- [ ] 기존 협력 이력 정리
- [ ] 명함/기념품 준비
- [ ] 회의록 양식 준비
- [ ] 후속 조치 사항 정리
- [ ] 감사 메일 발송""",
    },
    "신규 입점 브랜드 검토": {
        "category": "MD",
        "priority": "중간",
        "description": """## 신규 입점 브랜드 검토 체크리스트

- [ ] 브랜드 기본 정보 수집 (연혁, 규모, 주요 상품)
- [ ] 시장 내 포지셔닝 분석
- [ ] 경쟁사 입점 현황 조사
- [ ] 예상 매출 시뮬레이션
- [ ] 수수료/조건 협의
- [ ] 계약 조건 법무 검토 요청
- [ ] 매장 위치/면적 배정안
- [ ] 인테리어 가이드라인 협의
- [ ] 상품 구성(SKU) 확인
- [ ] 오픈일정 역산 스케줄""",
    },
}


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
    year: int, month: int,
    task_date_map: dict, today_str: str,
    selected_date: Optional[str] = None,
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
    weekday = today.weekday()
    monday = today - timedelta(days=weekday)
    dow_names = ["월", "화", "수", "목", "금", "토", "일"]
    html = ""

    for i in range(7):
        d = monday + timedelta(days=i)
        date_key = d.strftime("%Y-%m-%d")
        is_today = (d == today)

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
# 비밀번호 잠금
# ============================================
def check_password() -> bool:
    if st.session_state.authenticated:
        return True

    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🗂️</div>
        <h1 style="font-size: 1.8rem; font-weight: 700; color: var(--text-primary);">My AI Desk</h1>
        <p style="color: var(--text-muted); font-size: 0.95rem;">개인 업무 비서에 오신 걸 환영합니다</p>
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
    # -- 퀵 메모 --
    st.markdown("### 📝 퀵 메모")
    memo_input = st.text_area(
        "메모", placeholder="번뜩이는 아이디어, URL, 메모...",
        height=80, label_visibility="collapsed",
    )
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

    if pinned:
        st.markdown(f"<div style='font-size:0.78rem; color:var(--yellow); margin:0.5rem 0; font-weight:600;'>📌 고정 메모 ({len(pinned)}건)</div>", unsafe_allow_html=True)
        for memo in pinned:
            col_m, col_p, col_d = st.columns([5, 1, 1])
            with col_m:
                st.markdown(f"""<div class="memo-item" style="border-color: rgba(236,201,75,0.5);">
                    {memo['content'][:120]}{'...' if len(memo['content']) > 120 else ''}
                    <div class="memo-time">{format_dt(memo['created_at'])}</div>
                </div>""", unsafe_allow_html=True)
            with col_p:
                if st.button("📌", key=f"unpin_{memo['id']}", help="고정 해제"):
                    toggle_pin_memo(memo['id'], True)
                    st.rerun()
            with col_d:
                if st.button("🗑", key=f"del_memo_{memo['id']}", help="삭제"):
                    delete_memo(memo['id'])
                    st.rerun()

    if unpinned:
        st.markdown(f"<div style='font-size:0.78rem; color:var(--text-faint); margin:0.5rem 0;'>최근 메모 ({len(unpinned)}건)</div>", unsafe_allow_html=True)
        for memo in unpinned[:8]:
            col_m, col_p, col_d = st.columns([5, 1, 1])
            with col_m:
                st.markdown(f"""<div class="memo-item">
                    {memo['content'][:120]}{'...' if len(memo['content']) > 120 else ''}
                    <div class="memo-time">{format_dt(memo['created_at'])}</div>
                </div>""", unsafe_allow_html=True)
            with col_p:
                if st.button("📌", key=f"pin_{memo['id']}", help="고정"):
                    toggle_pin_memo(memo['id'], False)
                    st.rerun()
            with col_d:
                if st.button("🗑", key=f"del_memo_{memo['id']}", help="삭제"):
                    delete_memo(memo['id'])
                    st.rerun()

    st.markdown("---")

    # -- 검색 & 필터 --
    st.markdown("### 🔍 검색 & 필터")
    search_query = st.text_input("검색", placeholder="제목, 내용, 카테고리...", label_visibility="collapsed")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        st.session_state.filter_category = st.selectbox(
            "카테고리", CATEGORIES, index=CATEGORIES.index(st.session_state.filter_category),
        )
    with filter_col2:
        priority_options = ["전체"] + list(PRIORITIES.keys())
        current_pri = st.session_state.filter_priority
        if current_pri not in priority_options:
            current_pri = "전체"
        st.session_state.filter_priority = st.selectbox(
            "우선순위", priority_options, index=priority_options.index(current_pri),
        )

    st.session_state.sort_by = st.radio(
        "정렬", ["마감일순", "우선순위순", "등록순"],
        index=["마감일순", "우선순위순", "등록순"].index(st.session_state.sort_by),
        horizontal=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:var(--text-faint);'>"
        "My AI Desk v2.0<br>UI + 기능 + 코드 개선</div>",
        unsafe_allow_html=True,
    )


# ============================================
# 메인 헤더
# ============================================
st.markdown("""
<div style="display:flex; align-items:center; gap:0.7rem; margin-bottom:0.3rem;">
    <span style="font-size:2rem;">🗂️</span>
    <div>
        <h1 style="margin:0; font-size:1.6rem; font-weight:700; color: var(--text-primary);">My AI Desk</h1>
        <p style="margin:0; font-size:0.85rem; color: var(--text-muted);">개인 맞춤형 업무 비서</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================
# 통계 대시보드 (DB 호출 최소화)
# ============================================
all_active_tasks = load_tasks(
    show_completed=False, search_query="",
    category="전체", priority="전체",
) or []
completed_today = load_completed_today_count() or 0

overdue_count = sum(1 for t in all_active_tasks if get_urgency(t.get("deadline"))[0] == "overdue")
today_count = sum(1 for t in all_active_tasks if get_urgency(t.get("deadline"))[0] == "today")
total_active = len(all_active_tasks)

# 완료율 계산 (오늘 기준)
total_today_scope = today_count + completed_today
completion_rate = int((completed_today / total_today_scope * 100)) if total_today_scope > 0 else 0

st.markdown(f"""
<div class="stat-grid">
    <div class="stat-box">
        <div class="stat-number" style="color: var(--blue);">{total_active}</div>
        <div class="stat-label">진행 중</div>
    </div>
    <div class="stat-box">
        <div class="stat-number" style="color: var(--red);">{overdue_count}</div>
        <div class="stat-label">기한 초과</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{min(overdue_count * 10, 100)}%; background:var(--red);"></div></div>
    </div>
    <div class="stat-box">
        <div class="stat-number" style="color: var(--orange);">{today_count}</div>
        <div class="stat-label">오늘 마감</div>
    </div>
    <div class="stat-box">
        <div class="stat-number" style="color: var(--green);">{completed_today}</div>
        <div class="stat-label">오늘 완료</div>
        <div class="stat-bar"><div class="stat-bar-fill" style="width:{completion_rate}%; background:var(--green);"></div></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================
# 📅 달력 섹션
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

        # 날짜 선택 (Streamlit 위젯 기반)
        y = st.session_state.cal_year
        m = st.session_state.cal_month
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

        picked = st.selectbox(
            "📅 날짜 선택하여 업무 보기", day_options, index=selected_idx,
            key="date_picker",
        )
        if picked == "선택 안 함":
            st.session_state.selected_date = None
        else:
            day_num = int(picked.split("/")[1])
            st.session_state.selected_date = f"{y}-{m:02d}-{day_num:02d}"

        # 선택된 날짜의 업무 표시
        if st.session_state.selected_date and st.session_state.selected_date in task_date_map:
            sel_tasks = task_date_map[st.session_state.selected_date]
            st.markdown(
                f'<div class="selected-date-header">📋 {st.session_state.selected_date} 업무 ({len(sel_tasks)}건)</div>',
                unsafe_allow_html=True,
            )
            for t in sel_tasks:
                urg, label = get_urgency(t.get("deadline"))
                status = "✅" if t.get("is_completed") else PRIORITIES.get(t.get("priority", "중간"), "")
                dl = parse_deadline_kst(t.get("deadline"))
                time_str = dl.strftime("%H:%M") if dl else ""
                st.markdown(
                    f'<div class="task-card {urg if not t.get("is_completed") else "completed-card"}" style="margin-bottom:0.4rem; padding:0.7rem 1rem;">'
                    f'<div class="task-header"><span class="task-title" style="font-size:0.9rem;">{status} {t["title"]}</span>'
                    f'<span style="font-size:0.75rem; color:var(--text-muted);">{time_str}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        elif st.session_state.selected_date:
            st.caption(f"{st.session_state.selected_date}에 등록된 업무가 없습니다.")

        # 범례
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
# ➕ 업무 등록 폼
# ============================================
with st.expander("➕ 새 업무 등록", expanded=False):
    template_name = st.selectbox("템플릿 선택 (선택사항)", ["직접 입력"] + list(TEMPLATES.keys()))

    if template_name != "직접 입력":
        tmpl = TEMPLATES[template_name]
        default_title, default_desc = template_name, tmpl["description"]
        default_cat, default_pri = tmpl["category"], tmpl.get("priority", "중간")
    else:
        default_title, default_desc, default_cat, default_pri = "", "", "일반", "중간"

    new_title = st.text_input("업무명 *", value=default_title, placeholder="예: 3월 경영검토 보고서 작성")
    new_desc = st.text_area(
        "상세 내용", value=default_desc, height=200,
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
        cat_index = categories_no_all.index(default_cat) if default_cat in categories_no_all else 0
        new_category = st.selectbox("카테고리", categories_no_all, index=cat_index)
    with reg_col4:
        priority_list = list(PRIORITIES.keys())
        pri_index = priority_list.index(default_pri) if default_pri in priority_list else 1
        new_priority = st.selectbox("우선순위", priority_list, index=pri_index,
            format_func=lambda x: f"{PRIORITIES[x]} {x}")
    with reg_col5:
        recurrence_keys = list(RECURRENCE_OPTIONS.keys())
        new_recurrence_label = st.selectbox("반복", recurrence_keys, index=0)
        new_recurrence = RECURRENCE_OPTIONS[new_recurrence_label]

    if st.button("📌 업무 등록", use_container_width=True, type="primary"):
        if new_title.strip():
            deadline = None
            if new_date:
                t = new_time if new_time else dt_time(18, 0)
                deadline = datetime.combine(new_date, t).replace(tzinfo=KST)
            add_task(
                new_title.strip(), new_desc.strip(), deadline,
                new_category, new_priority, new_recurrence,
            )
            st.toast("✅ 업무가 등록되었습니다!")
            st.balloons()
            st.rerun()
        else:
            st.warning("업무명을 입력해주세요.")


# ============================================
# 📌 업무 목록 (필터 + 정렬 적용)
# ============================================
active_filter_parts = []
if st.session_state.filter_category != "전체":
    active_filter_parts.append(f"카테고리: {st.session_state.filter_category}")
if st.session_state.filter_priority != "전체":
    active_filter_parts.append(f"우선순위: {st.session_state.filter_priority}")
if search_query:
    active_filter_parts.append(f"검색: \"{search_query}\"")

filter_info = f" · <span class='filter-active'>{' | '.join(active_filter_parts)}</span>" if active_filter_parts else ""
st.markdown(f"### 📌 진행 중인 업무{filter_info}", unsafe_allow_html=True)

tasks = load_tasks(
    show_completed=False,
    search_query=search_query,
    category=st.session_state.filter_category,
    priority=st.session_state.filter_priority,
) or []

# 정렬
if st.session_state.sort_by == "우선순위순":
    tasks.sort(key=lambda t: PRIORITY_ORDER.get(t.get("priority", "중간"), 1))
elif st.session_state.sort_by == "등록순":
    tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
# 마감일순은 DB에서 이미 정렬됨

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
        recurrence_label = ""
        if recurrence:
            recurrence_map = {v: k for k, v in RECURRENCE_OPTIONS.items() if v}
            recurrence_label = f' · 🔁 {recurrence_map.get(recurrence, recurrence)}'

        # 체크리스트 진행률
        progress_html = ""
        prog = calc_checklist_progress(task.get("description"))
        if prog:
            pct = int(prog[0] / prog[1] * 100) if prog[1] > 0 else 0
            progress_html = (
                f'<span class="progress-inline">'
                f'<span class="progress-bar-mini"><span class="progress-bar-mini-fill" style="width:{pct}%;"></span></span>'
                f'<span style="font-size:0.72rem;">{prog[0]}/{prog[1]}</span>'
                f'</span>'
            )

        urgency_html = ""
        if urgency_label:
            urgency_cls = f"urgency-{urgency}"
            urgency_html = f'<span class="urgency-tag {urgency_cls}">{urgency_label}</span>'

        st.markdown(f"""<div class="task-card {urgency}">
            <div class="task-header">
                <span class="task-title">{pri_icon} {task['title']}</span>
                <div class="task-badges">
                    <span class="badge badge-priority-{pri}">{pri}</span>
                    <span class="badge">{task.get('category','일반')}</span>
                </div>
            </div>
            <div class="task-meta">
                <span>{('📅 ' + format_dt(task['deadline'])) if task.get('deadline') else '📅 마감일 미지정'}</span>
                {urgency_html}
                {progress_html}
                {f'<span>🔁 반복</span>' if recurrence else ''}
            </div>
        </div>""", unsafe_allow_html=True)

        with st.expander(f"상세 보기 · {task['title']}", expanded=False):
            if task.get("description"):
                st.markdown(task["description"])
            else:
                st.caption("상세 내용 없음")

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button("✅ 완료 처리", key=f"done_{task['id']}", use_container_width=True, type="primary"):
                    complete_task(task)
                    if task.get("recurrence"):
                        st.toast("🎉 완료! 다음 회차 자동 생성됨")
                    else:
                        st.toast("🎉 수고하셨습니다!")
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
                        index=categories_no_all.index(task.get("category", "일반")) if task.get("category", "일반") in categories_no_all else 0,
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

                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    if st.button("💾 저장", key=f"save_{task['id']}", use_container_width=True, type="primary"):
                        deadline = None
                        if edit_date:
                            t = edit_time if edit_time else dt_time(18, 0)
                            deadline = datetime.combine(edit_date, t).replace(tzinfo=KST)
                        update_task(task["id"], edit_title, edit_desc, deadline, edit_cat, edit_pri, edit_rec)
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
            st.markdown(f"""<div class="task-card completed-card">
                <div class="task-header">
                    <span class="task-title" style="text-decoration: line-through;">{pri_icon} {ct['title']}</span>
                    <span class="badge">{ct.get('category','일반')}</span>
                </div>
                <div class="task-meta">
                    <span>완료: {format_dt(ct['completed_at'])}</span>
                    {f'<span>⏱ {duration}</span>' if duration else ''}
                </div>
            </div>""", unsafe_allow_html=True)

            col_r1, col_r2 = st.columns([1, 1])
            with col_r1:
                if st.button("↩️ 되돌리기", key=f"undo_{ct['id']}"):
                    uncomplete_task(ct["id"])
                    st.rerun()
            with col_r2:
                if st.button("🗑️ 삭제", key=f"cdel_{ct['id']}"):
                    delete_task(ct["id"])
                    st.rerun()
