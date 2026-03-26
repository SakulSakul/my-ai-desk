import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta, timezone
import calendar
import json

# ============================================
# 설정 (Streamlit Secrets 또는 직접 입력)
# ============================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "여기에_수파베이스_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "여기에_수파베이스_ANON_KEY")
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

KST = timezone(timedelta(hours=9))

# ============================================
# Supabase 클라이언트 초기화
# ============================================
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ============================================
# 페이지 기본 설정
# ============================================
st.set_page_config(
    page_title="My AI Desk",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================
# 커스텀 CSS
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .block-container { padding-top: 1.5rem; }

    /* 카드 스타일 */
    .task-card {
        background: linear-gradient(135deg, #667eea11, #764ba211);
        border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 1rem 1.2rem; margin-bottom: 0.8rem; transition: all 0.2s;
    }
    .task-card:hover { border-color: #667eea; box-shadow: 0 2px 12px rgba(102,126,234,0.15); }
    .task-title { font-size: 1.05rem; font-weight: 600; color: #1a202c; margin-bottom: 0.3rem; }
    .task-meta { font-size: 0.82rem; color: #718096; }
    .overdue { border-left: 4px solid #e53e3e; }
    .today { border-left: 4px solid #ed8936; }
    .upcoming { border-left: 4px solid #48bb78; }
    .completed-card { opacity: 0.6; border-left: 4px solid #a0aec0; }

    /* 통계 카드 */
    .stat-box {
        background: white; border-radius: 12px; padding: 1rem;
        text-align: center; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .stat-number { font-size: 2rem; font-weight: 700; }
    .stat-label { font-size: 0.8rem; color: #718096; margin-top: 0.2rem; }

    /* 사이드바 메모 */
    .memo-item {
        background: #fffff0; border: 1px solid #ecc94b44;
        border-radius: 8px; padding: 0.7rem; margin-bottom: 0.5rem; font-size: 0.85rem;
    }
    .memo-time { font-size: 0.72rem; color: #a0aec0; }

    /* ===== 달력 스타일 ===== */
    .cal-container {
        background: white; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .cal-header {
        display: flex; justify-content: center; align-items: center;
        gap: 1.5rem; margin-bottom: 0.8rem;
    }
    .cal-header-month { font-size: 1.15rem; font-weight: 700; color: #2d3748; min-width: 140px; text-align: center; }

    .cal-grid {
        display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
    }
    .cal-dow {
        text-align: center; font-size: 0.75rem; font-weight: 600;
        color: #a0aec0; padding: 0.3rem 0;
    }
    .cal-dow-sun { color: #e53e3e; }
    .cal-dow-sat { color: #4299e1; }

    .cal-day {
        position: relative; text-align: center; padding: 0.35rem 0.1rem;
        border-radius: 8px; min-height: 2.8rem; font-size: 0.85rem; color: #4a5568;
    }
    .cal-day-empty { }
    .cal-day-today {
        background: #667eea; color: white; font-weight: 700; border-radius: 8px;
    }
    .cal-day-sun { color: #e53e3e; }
    .cal-day-sat { color: #4299e1; }
    .cal-day-today.cal-day-sun, .cal-day-today.cal-day-sat { color: white; }

    .cal-dots {
        display: flex; justify-content: center; gap: 2px; margin-top: 2px;
    }
    .cal-dot {
        width: 5px; height: 5px; border-radius: 50%;
    }
    .cal-dot-overdue { background: #e53e3e; }
    .cal-dot-today { background: #ed8936; }
    .cal-dot-upcoming { background: #48bb78; }
    .cal-dot-completed { background: #a0aec0; }

    /* 주간 뷰 */
    .week-day-card {
        background: white; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 0.7rem; margin-bottom: 0.4rem;
    }
    .week-day-card-today {
        background: linear-gradient(135deg, #667eea08, #764ba208);
        border: 1.5px solid #667eea;
    }
    .week-day-header {
        font-size: 0.82rem; font-weight: 600; color: #2d3748; margin-bottom: 0.4rem;
    }
    .week-day-header-today { color: #667eea; }
    .week-task-item {
        font-size: 0.8rem; color: #4a5568; padding: 0.15rem 0;
        border-left: 3px solid #e2e8f0; padding-left: 0.5rem; margin-bottom: 0.2rem;
    }
    .week-task-item-overdue { border-left-color: #e53e3e; }
    .week-task-item-today { border-left-color: #ed8936; }
    .week-task-item-upcoming { border-left-color: #48bb78; }
    .week-no-task { font-size: 0.78rem; color: #cbd5e0; font-style: italic; }

    /* 모바일 */
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem; }
        .stat-number { font-size: 1.5rem; }
        .cal-day { min-height: 2.2rem; font-size: 0.78rem; }
        .cal-dot { width: 4px; height: 4px; }
    }

    .stButton > button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ============================================
# 비밀번호 잠금
# ============================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🗂️</div>
        <h1 style="font-size: 1.8rem; font-weight: 700; color: #2d3748;">My AI Desk</h1>
        <p style="color: #718096; font-size: 0.95rem;">개인 업무 비서에 오신 걸 환영합니다</p>
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
# 유틸리티 함수
# ============================================
def now_kst():
    return datetime.now(KST)

def format_dt(dt_str):
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%m/%d(%a) %H:%M")
    except:
        return dt_str

def parse_deadline_kst(dt_str):
    """마감일 문자열을 KST datetime으로 변환"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(KST)
    except:
        return None

def get_urgency(deadline_str):
    if not deadline_str:
        return "upcoming", ""
    try:
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00")).astimezone(KST)
        now = now_kst()
        diff = deadline - now
        if diff.total_seconds() < 0:
            return "overdue", "⏰ 기한 초과"
        elif diff.days == 0:
            hours = diff.seconds // 3600
            return "today", f"⚡ {hours}시간 남음"
        elif diff.days <= 3:
            return "upcoming", f"📅 {diff.days}일 남음"
        else:
            return "upcoming", f"📅 {diff.days}일 남음"
    except:
        return "upcoming", ""

def calc_duration(created_str, completed_str):
    if not created_str or not completed_str:
        return ""
    try:
        c = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        d = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
        diff = d - c
        days = diff.days
        hours = diff.seconds // 3600
        mins = (diff.seconds % 3600) // 60
        parts = []
        if days > 0: parts.append(f"{days}일")
        if hours > 0: parts.append(f"{hours}시간")
        if mins > 0: parts.append(f"{mins}분")
        return " ".join(parts) if parts else "1분 미만"
    except:
        return ""

# ============================================
# DB 함수
# ============================================
def load_tasks(show_completed=False, search_query=""):
    query = supabase.table("tasks").select("*")
    if not show_completed:
        query = query.eq("is_completed", False)
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

def load_all_tasks_for_calendar():
    """달력용: 완료/미완료 모두 가져오기"""
    result = supabase.table("tasks").select("*").order("deadline", desc=False).execute()
    return result.data or []

def add_task(title, description, deadline, category, alarm_before_min):
    data = {
        "title": title, "description": description,
        "deadline": deadline.isoformat() if deadline else None,
        "category": category, "alarm_before_min": alarm_before_min,
        "is_completed": False,
    }
    supabase.table("tasks").insert(data).execute()

def complete_task(task_id):
    supabase.table("tasks").update({
        "is_completed": True, "completed_at": now_kst().isoformat()
    }).eq("id", task_id).execute()

def uncomplete_task(task_id):
    supabase.table("tasks").update({
        "is_completed": False, "completed_at": None
    }).eq("id", task_id).execute()

def delete_task(task_id):
    supabase.table("tasks").delete().eq("id", task_id).execute()

def update_task(task_id, title, description, deadline, category):
    data = {
        "title": title, "description": description,
        "deadline": deadline.isoformat() if deadline else None,
        "category": category,
    }
    supabase.table("tasks").update(data).eq("id", task_id).execute()

def load_memos():
    result = supabase.table("memos").select("*").order("created_at", desc=True).limit(50).execute()
    return result.data or []

def add_memo(content):
    supabase.table("memos").insert({"content": content}).execute()

def delete_memo(memo_id):
    supabase.table("memos").delete().eq("id", memo_id).execute()

# ============================================
# 템플릿 정의
# ============================================
TEMPLATES = {
    "ISO 경영검토 보고서": {
        "category": "정기보고",
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
# 달력 헬퍼 함수
# ============================================
def build_task_date_map(tasks):
    """업무를 날짜별로 분류한 dict 반환: { 'YYYY-MM-DD': [task, ...] }"""
    date_map = {}
    for t in tasks:
        dl = parse_deadline_kst(t.get("deadline"))
        if dl:
            key = dl.strftime("%Y-%m-%d")
            if key not in date_map:
                date_map[key] = []
            date_map[key].append(t)
    return date_map

def render_monthly_calendar(year, month, task_date_map, today_str):
    """월간 달력 HTML 생성"""
    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    days_in_month = list(cal.itermonthdays2(year, month))

    dow_names = ["일", "월", "화", "수", "목", "금", "토"]
    html = '<div class="cal-grid">'

    # 요일 헤더
    for i, d in enumerate(dow_names):
        cls = "cal-dow"
        if i == 0: cls += " cal-dow-sun"
        if i == 6: cls += " cal-dow-sat"
        html += f'<div class="{cls}">{d}</div>'

    # 날짜 셀
    for day, weekday in days_in_month:
        if day == 0:
            html += '<div class="cal-day cal-day-empty"></div>'
            continue

        date_key = f"{year}-{month:02d}-{day:02d}"
        adjusted_wd = (weekday + 1) % 7  # 0=일, 6=토

        cls = "cal-day"
        if date_key == today_str:
            cls += " cal-day-today"
        elif adjusted_wd == 0:
            cls += " cal-day-sun"
        elif adjusted_wd == 6:
            cls += " cal-day-sat"

        # 해당 날짜의 업무 dots
        dots_html = ""
        if date_key in task_date_map:
            dots = []
            for t in task_date_map[date_key][:3]:  # 최대 3개 dot
                if t.get("is_completed"):
                    dots.append('<span class="cal-dot cal-dot-completed"></span>')
                else:
                    urg, _ = get_urgency(t.get("deadline"))
                    dot_cls = f"cal-dot cal-dot-{urg}"
                    dots.append(f'<span class="{dot_cls}"></span>')
            dots_html = f'<div class="cal-dots">{"".join(dots)}</div>'

        html += f'<div class="{cls}">{day}{dots_html}</div>'

    html += '</div>'
    return html

def render_weekly_view(tasks, task_date_map):
    """주간 뷰 HTML 생성"""
    now = now_kst()
    today = now.date()
    # 이번 주 월요일 ~ 일요일
    weekday = today.weekday()  # 0=월
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
                    html += f'<div class="week-task-item" style="text-decoration:line-through; color:#a0aec0;">✅ {t["title"]}</div>'
                else:
                    urg, _ = get_urgency(t.get("deadline"))
                    item_cls = f"week-task-item week-task-item-{urg}"
                    dl = parse_deadline_kst(t.get("deadline"))
                    time_str = dl.strftime("%H:%M") if dl else ""
                    html += f'<div class="{item_cls}">{t["title"]} <span style="color:#a0aec0; font-size:0.72rem;">{time_str}</span></div>'
            if len(day_tasks) > 5:
                html += f'<div class="week-no-task">외 {len(day_tasks)-5}건 더</div>'
        else:
            html += '<div class="week-no-task">일정 없음</div>'

        html += '</div>'

    return html

# ============================================
# 사이드바: 퀵 메모 + 검색
# ============================================
with st.sidebar:
    st.markdown("### 📝 퀵 메모")
    memo_input = st.text_area("메모", placeholder="번뜩이는 아이디어, URL, 메모...", height=80, label_visibility="collapsed")
    if st.button("메모 저장", use_container_width=True, type="primary"):
        if memo_input.strip():
            add_memo(memo_input.strip())
            st.toast("✅ 메모 저장 완료!")
            st.rerun()

    memos = load_memos()
    if memos:
        st.markdown(f"<div style='font-size:0.8rem; color:#a0aec0; margin:0.5rem 0;'>최근 메모 ({len(memos)}건)</div>", unsafe_allow_html=True)
        for memo in memos[:10]:
            col_m, col_d = st.columns([5, 1])
            with col_m:
                st.markdown(f"""<div class="memo-item">
                    {memo['content'][:100]}{'...' if len(memo['content']) > 100 else ''}
                    <div class="memo-time">{format_dt(memo['created_at'])}</div>
                </div>""", unsafe_allow_html=True)
            with col_d:
                if st.button("🗑", key=f"del_memo_{memo['id']}", help="삭제"):
                    delete_memo(memo['id'])
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🔍 업무 검색")
    search_query = st.text_input("검색", placeholder="제목, 내용, 카테고리 검색...", label_visibility="collapsed")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:0.75rem; color:#a0aec0;'>"
        "My AI Desk v1.1<br>Phase 1 + Calendar</div>",
        unsafe_allow_html=True,
    )

# ============================================
# 메인 헤더
# ============================================
st.markdown("""
<div style="display:flex; align-items:center; gap:0.7rem; margin-bottom:0.3rem;">
    <span style="font-size:2rem;">🗂️</span>
    <div>
        <h1 style="margin:0; font-size:1.6rem; font-weight:700; color:#2d3748;">My AI Desk</h1>
        <p style="margin:0; font-size:0.85rem; color:#718096;">개인 맞춤형 업무 비서</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# 통계 대시보드
# ============================================
all_tasks = load_tasks(show_completed=False, search_query="")
completed_today_q = supabase.table("tasks").select("*").eq("is_completed", True).gte(
    "completed_at", now_kst().replace(hour=0, minute=0, second=0).isoformat()
).execute()
completed_today = len(completed_today_q.data or [])

overdue_count = sum(1 for t in all_tasks if get_urgency(t.get("deadline"))[0] == "overdue")
today_count = sum(1 for t in all_tasks if get_urgency(t.get("deadline"))[0] == "today")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#4299e1;">{len(all_tasks)}</div><div class="stat-label">진행 중</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#e53e3e;">{overdue_count}</div><div class="stat-label">기한 초과</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#ed8936;">{today_count}</div><div class="stat-label">오늘 마감</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="stat-box"><div class="stat-number" style="color:#48bb78;">{completed_today}</div><div class="stat-label">오늘 완료</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

# ============================================
# 📅 달력 섹션
# ============================================
with st.expander("📅 달력", expanded=True):
    cal_tasks = load_all_tasks_for_calendar()
    task_date_map = build_task_date_map(cal_tasks)
    now = now_kst()
    today_str = now.strftime("%Y-%m-%d")

    # 월 이동 상태 관리
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = now.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = now.month

    # 월간/주간 탭
    cal_tab1, cal_tab2 = st.tabs(["📆 월간", "📋 주간"])

    with cal_tab1:
        # 월 이동 버튼
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
                f"<div style='text-align:right; font-size:1.1rem; font-weight:700; color:#2d3748; padding:0.3rem 0;'>"
                f"{st.session_state.cal_year}년 {st.session_state.cal_month}월</div>",
                unsafe_allow_html=True
            )
        with nav3:
            if st.session_state.cal_year != now.year or st.session_state.cal_month != now.month:
                if st.button("오늘", key="cal_today", use_container_width=True):
                    st.session_state.cal_year = now.year
                    st.session_state.cal_month = now.month
                    st.rerun()
        with nav4:
            if st.button("▶", key="cal_next", use_container_width=True):
                if st.session_state.cal_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()

        # 월간 달력 렌더링
        cal_html = render_monthly_calendar(
            st.session_state.cal_year, st.session_state.cal_month,
            task_date_map, today_str
        )
        st.markdown(f'<div class="cal-container">{cal_html}</div>', unsafe_allow_html=True)

        # 범례
        st.markdown("""
        <div style="display:flex; gap:1rem; justify-content:center; margin-top:0.6rem; font-size:0.72rem; color:#a0aec0;">
            <span><span class="cal-dot cal-dot-overdue" style="display:inline-block;"></span> 기한초과</span>
            <span><span class="cal-dot cal-dot-today" style="display:inline-block;"></span> 오늘마감</span>
            <span><span class="cal-dot cal-dot-upcoming" style="display:inline-block;"></span> 예정</span>
            <span><span class="cal-dot cal-dot-completed" style="display:inline-block;"></span> 완료</span>
        </div>
        """, unsafe_allow_html=True)

    with cal_tab2:
        # 주간 뷰
        weekday = now.date().weekday()
        monday = now.date() - timedelta(days=weekday)
        sunday = monday + timedelta(days=6)
        st.markdown(
            f"<div style='text-align:center; font-size:1rem; font-weight:600; color:#2d3748; margin-bottom:0.5rem;'>"
            f"📋 {monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')} 이번 주</div>",
            unsafe_allow_html=True
        )
        week_html = render_weekly_view(cal_tasks, task_date_map)
        st.markdown(week_html, unsafe_allow_html=True)

# ============================================
# 업무 등록 폼
# ============================================
with st.expander("➕ 새 업무 등록", expanded=False):
    template_name = st.selectbox("템플릿 선택 (선택사항)", ["직접 입력"] + list(TEMPLATES.keys()))

    if template_name != "직접 입력":
        tmpl = TEMPLATES[template_name]
        default_title = template_name
        default_desc = tmpl["description"]
        default_cat = tmpl["category"]
    else:
        default_title = ""
        default_desc = ""
        default_cat = "일반"

    new_title = st.text_input("업무명 *", value=default_title, placeholder="예: 3월 경영검토 보고서 작성")
    new_desc = st.text_area("상세 내용", value=default_desc, height=200,
        placeholder="마크다운 체크리스트, 메모, 담당자 정보 등 자유롭게 작성\n\n- [ ] 할 일 1\n- [ ] 할 일 2")

    col_a, col_b = st.columns(2)
    with col_a:
        new_date = st.date_input("마감일", value=None)
    with col_b:
        new_time = st.time_input("마감 시간", value=None)

    col_c, col_d = st.columns(2)
    with col_c:
        categories = ["일반", "정기보고", "기획", "미팅", "MD", "대외협력", "기타"]
        cat_index = categories.index(default_cat) if default_cat in categories else 0
        new_category = st.selectbox("카테고리", categories, index=cat_index)
    with col_d:
        new_alarm = st.selectbox("알람 (향후 연동)", [60, 10, 30, 120, 1440], format_func=lambda x: {
            10: "10분 전", 30: "30분 전", 60: "1시간 전", 120: "2시간 전", 1440: "1일 전"
        }.get(x, f"{x}분 전"))

    if st.button("📌 업무 등록", use_container_width=True, type="primary"):
        if new_title.strip():
            deadline = None
            if new_date:
                if new_time:
                    deadline = datetime.combine(new_date, new_time).replace(tzinfo=KST)
                else:
                    deadline = datetime.combine(new_date, datetime.min.time().replace(hour=18)).replace(tzinfo=KST)
            add_task(new_title.strip(), new_desc.strip(), deadline, new_category, new_alarm)
            st.toast("✅ 업무가 등록되었습니다!")
            st.balloons()
            st.rerun()
        else:
            st.warning("업무명을 입력해주세요.")

# ============================================
# 업무 목록 (진행 중)
# ============================================
st.markdown("### 📌 진행 중인 업무")

tasks = load_tasks(show_completed=False, search_query=search_query)

if not tasks:
    if search_query:
        st.info(f"'{search_query}'에 대한 검색 결과가 없습니다.")
    else:
        st.info("등록된 업무가 없습니다. 위에서 새 업무를 등록해보세요!")
else:
    for task in tasks:
        urgency, urgency_label = get_urgency(task.get("deadline"))

        st.markdown(f"""<div class="task-card {urgency}">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div class="task-title">{task['title']}</div>
                <span style="font-size:0.75rem; background:#edf2f7; padding:2px 8px; border-radius:12px; color:#4a5568;">{task.get('category','일반')}</span>
            </div>
            <div class="task-meta">
                {('📅 마감: ' + format_dt(task['deadline'])) if task.get('deadline') else '📅 마감일 미지정'}
                {(' · ' + urgency_label) if urgency_label else ''}
                · 등록: {format_dt(task['created_at'])}
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
                    complete_task(task["id"])
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

            if st.session_state.get(f"editing_{task['id']}", False):
                st.markdown("---")
                st.markdown("**✏️ 업무 수정**")
                edit_title = st.text_input("업무명", value=task["title"], key=f"et_{task['id']}")
                edit_desc = st.text_area("상세 내용", value=task.get("description", ""), height=150, key=f"ed_{task['id']}")

                edit_date = None
                edit_time = None
                if task.get("deadline"):
                    try:
                        dl = datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")).astimezone(KST)
                        edit_date = st.date_input("마감일", value=dl.date(), key=f"edt_{task['id']}")
                        edit_time = st.time_input("마감 시간", value=dl.time(), key=f"etm_{task['id']}")
                    except:
                        edit_date = st.date_input("마감일", value=None, key=f"edt_{task['id']}")
                        edit_time = st.time_input("마감 시간", value=None, key=f"etm_{task['id']}")
                else:
                    edit_date = st.date_input("마감일", value=None, key=f"edt_{task['id']}")
                    edit_time = st.time_input("마감 시간", value=None, key=f"etm_{task['id']}")

                edit_cat = st.selectbox("카테고리", categories,
                    index=categories.index(task.get("category", "일반")) if task.get("category", "일반") in categories else 0,
                    key=f"ec_{task['id']}")

                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    if st.button("💾 저장", key=f"save_{task['id']}", use_container_width=True, type="primary"):
                        deadline = None
                        if edit_date:
                            if edit_time:
                                deadline = datetime.combine(edit_date, edit_time).replace(tzinfo=KST)
                            else:
                                deadline = datetime.combine(edit_date, datetime.min.time().replace(hour=18)).replace(tzinfo=KST)
                        update_task(task["id"], edit_title, edit_desc, deadline, edit_cat)
                        st.session_state[f"editing_{task['id']}"] = False
                        st.toast("✅ 수정 완료!")
                        st.rerun()
                with ecol2:
                    if st.button("취소", key=f"cancel_{task['id']}", use_container_width=True):
                        st.session_state[f"editing_{task['id']}"] = False
                        st.rerun()

# ============================================
# 완료된 업무
# ============================================
st.markdown("---")
with st.expander("✅ 완료된 업무 보기"):
    completed_tasks = supabase.table("tasks").select("*").eq("is_completed", True).order("completed_at", desc=True).limit(30).execute()
    c_tasks = completed_tasks.data or []

    if not c_tasks:
        st.caption("아직 완료된 업무가 없습니다.")
    else:
        for ct in c_tasks:
            duration = calc_duration(ct.get("created_at"), ct.get("completed_at"))
            st.markdown(f"""<div class="task-card completed-card">
                <div class="task-title" style="text-decoration: line-through;">{ct['title']}</div>
                <div class="task-meta">
                    완료: {format_dt(ct['completed_at'])}
                    {(' · 소요: ' + duration) if duration else ''}
                    · <span style="background:#edf2f7; padding:1px 6px; border-radius:8px;">{ct.get('category','일반')}</span>
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
