"""ui/components.py — 공용 위젯/렌더 함수 [Phase 1-A, app.py 에서 순수 이동].

CSS 테마 주입 + 순수 HTML 렌더 헬퍼(달력/주간뷰/차트).
"""
import streamlit as st
import calendar
from datetime import timedelta
from collections import Counter, defaultdict

from core.models import (
    CATEGORIES, CATEGORY_COLORS, CATEGORY_ICONS, PRIORITIES,
    now_kst, parse_deadline_kst, get_urgency,
    calc_duration_minutes, format_duration_compact,
)


# CSS — Phase 2 디자인 시스템
# 헤딩=명시적 세리프(Georgia) · 본문=시스템 산세리프 · 액센트 1색(#2563EB) · 카드형 · 모바일 우선
# 웹폰트 로드 없음(Phase 2.1 폰트 정책: 현재 폴백 룩을 의도된 디자인으로 승격)
def inject_css():
    st.markdown("""
<style>
    :root {
        --font-sans: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;
        --font-serif: Georgia, 'Times New Roman', serif;
        --black: #1a1a1a;
        --dark: #333333;
        --gray-800: #444444;
        --gray-600: #666666;
        --gray-400: #999999;
        --gray-200: #e0e0e0;
        --gray-100: #f5f7fa;
        --white: #ffffff;
        --accent: #3056D3;
        --accent-dark: #2646AC;
        --accent-light: #3056D314;
        --red: #c0392b;
        --red-light: #c0392b12;
        --orange: #d4880f;
        --orange-light: #d4880f10;
        --green: #3a7d5c;
        --green-light: #3a7d5c10;
        --blue: #4a90a4;
        --radius: 10px;
        --radius-md: 12px;
        --transition: all 0.2s ease;
        /* 호환 별칭 — 잔존 참조가 있어도 새 시스템 안에서 렌더되도록 */
        --gold: var(--accent);
        --gold-hover: var(--accent-dark);
        --gold-light: var(--accent-light);
    }

    html, body, [class*="css"] {
        font-family: var(--font-sans);
        font-weight: 400;
        line-height: 1.55;
        color: var(--dark);
    }

    /* Streamlit 기본 스타일 오버라이드 */
    .block-container {
        padding-top: 2.2rem;
        max-width: 860px;
    }
    .stApp > header { background: transparent; }

    /* 버튼 — 모바일 터치 타겟 */
    .stButton > button, .stFormSubmitButton > button {
        border-radius: var(--radius);
        font-family: var(--font-sans);
        font-weight: 500;
        min-height: 44px;
        white-space: normal;
    }

    /* ── 헤더 영역 ── */
    .app-header {
        border-bottom: 2px solid var(--black);
        padding-bottom: 16px;
        margin-bottom: 16px;
    }
    .app-header h1 {
        font-family: var(--font-serif);
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--black);
        letter-spacing: -0.5px;
        margin: 0;
        line-height: 1.3;
    }
    .app-header-sub {
        font-size: 0.78rem;
        font-weight: 500;
        color: var(--gray-600);
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-top: 4px;
    }

    /* ── 통계 카드 ── */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin: 12px 0 20px 0;
    }
    .stat-box {
        padding: 16px 8px;
        min-height: 88px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        background: var(--gray-100);
        border: 1px solid var(--gray-200);
        border-radius: var(--radius-md);
        transition: var(--transition);
    }
    .stat-box:hover { border-color: var(--gray-400); }
    .stat-number {
        font-family: var(--font-serif);
        font-size: 1.8rem;
        font-weight: 700;
        line-height: 1;
    }
    .stat-label {
        font-size: 0.7rem;
        font-weight: 500;
        color: var(--gray-600);
        margin-top: 8px;
        letter-spacing: 1px;
    }

    /* ── 섹션 헤더 ── */
    .section-header {
        font-family: var(--font-serif);
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--black);
        border-bottom: 1px solid var(--gray-200);
        padding-bottom: 8px;
        margin: 24px 0 12px 0;
        letter-spacing: -0.3px;
    }
    .section-header-light {
        font-size: 0.72rem;
        font-weight: 500;
        color: var(--gray-400);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }

    /* ── 업무 카드 ── */
    .task-card {
        background: var(--white);
        border: 1px solid var(--gray-200);
        border-left: 4px solid transparent;
        border-radius: var(--radius-md);
        padding: 12px 16px;
        margin-bottom: 8px;
        transition: var(--transition);
        position: relative;
    }
    .task-card:hover { border-color: var(--gray-400); background: var(--gray-100); }
    .task-card.overdue {
        border-left: 4px solid var(--red);
        background: var(--red-light);
    }
    .task-card.today {
        border-left: 4px solid var(--orange);
        background: var(--orange-light);
    }
    .task-card.upcoming { }
    .task-card.completed-card { opacity: 0.45; }
    .task-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.8rem;
    }
    .task-title {
        font-family: var(--font-serif);
        font-size: 0.95rem;
        font-weight: 500;
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
        font-size: 0.65rem;
        font-weight: 500;
        padding: 2px 8px;
        border: 1px solid var(--gray-200);
        border-radius: 999px;
        color: var(--gray-600);
        letter-spacing: 0.5px;
        white-space: nowrap;
    }
    .badge-priority-높음 { border-color: var(--red); color: var(--red); }
    .badge-priority-중간 { border-color: var(--gray-400); color: var(--gray-600); }
    .badge-priority-낮음 { border-color: var(--green); color: var(--green); }
    .badge-tag {
        font-size: 0.63rem;
        padding: 1px 6px;
        border: 1px solid var(--blue);
        border-radius: 999px;
        color: var(--blue);
    }
    .task-meta {
        font-size: 0.76rem;
        color: var(--gray-400);
        margin-top: 8px;
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem 1rem;
        align-items: center;
    }
    .urgency-tag { font-weight: 700; }
    .urgency-overdue { color: var(--red); }
    .urgency-today { color: var(--orange); }
    .progress-inline { display: inline-flex; align-items: center; gap: 0.3rem; }
    .progress-bar-mini {
        width: 50px; height: 4px; background: var(--gray-200);
        border-radius: 999px; overflow: hidden;
    }
    .progress-bar-mini-fill { height: 100%; background: var(--green); }
    .timer-active {
        display: inline-flex; align-items: center; gap: 0.3rem;
        border: 1px solid var(--red); border-radius: 999px;
        padding: 1px 8px; font-size: 0.7rem; color: var(--red);
        font-weight: 700;
        animation: pulse-border 2s infinite;
    }
    @keyframes pulse-border {
        0%, 100% { border-color: #e0b0b0; }
        50% { border-color: var(--red); }
    }

    /* ── 오늘 뷰 카드 컨테이너 (st.container key=tcard_*) ──
       HTML 카드와 동일한 룩에 액션 버튼을 '카드 안'에 내장한다. */
    [class*="st-key-tcard_"] {
        background: var(--white);
        border: 1px solid var(--gray-200);
        border-left: 4px solid transparent;
        border-radius: var(--radius-md);
        padding: 12px 16px;
        margin-bottom: 8px;
        gap: 8px;
    }
    [class*="st-key-tcard_overdue"] { border-left-color: var(--red); background: var(--red-light); }
    [class*="st-key-tcard_today"] { border-left-color: var(--orange); background: var(--orange-light); }
    /* 카드 내 액션 버튼: 컴팩트 아웃라인, 전폭 금지(데스크톱 각 ~160px),
       모바일에서도 2열 유지(스택 방지) + 터치 44px */
    [class*="st-key-tcard_"] [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }
    [class*="st-key-tcard_"] [data-testid="stColumn"] {
        flex: 0 1 160px !important;
        min-width: 120px !important;
        width: auto !important;
    }
    [class*="st-key-tcard_"] .stButton > button {
        width: 100%;
        min-height: 44px;
        padding: 4px 12px;
        background: transparent;
        font-size: 0.85rem;
    }
    /* 완료 = 액센트 아웃라인 / 내일로 = 중립 아웃라인 (진한 채움 금지) */
    [class*="st-key-tcard_"] [data-testid="stColumn"]:nth-of-type(1) .stButton > button {
        border: 1px solid var(--accent);
        color: var(--accent);
    }
    [class*="st-key-tcard_"] [data-testid="stColumn"]:nth-of-type(1) .stButton > button:hover {
        border-color: var(--accent-dark); color: var(--accent-dark); background: var(--accent-light);
    }
    [class*="st-key-tcard_"] [data-testid="stColumn"]:nth-of-type(2) .stButton > button {
        border: 1px solid var(--gray-200);
        color: var(--dark);
    }
    [class*="st-key-tcard_"] [data-testid="stColumn"]:nth-of-type(2) .stButton > button:hover {
        border-color: var(--gray-400); background: var(--gray-100);
    }

    /* ── 빈 상태 ── */
    .empty-state {
        text-align: center;
        color: var(--gray-600);
        font-size: 0.92rem;
        line-height: 1.8;
        background: var(--gray-100);
        border: 1px solid var(--gray-200);
        border-radius: var(--radius-md);
        padding: 32px 16px;
        margin: 16px 0;
    }

    /* ── 차트 영역 ── */
    .chart-container {
        background: var(--white);
        border: 1px solid var(--gray-200);
        border-radius: var(--radius-md);
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
        border-radius: 4px; overflow: hidden; display: flex;
    }
    .chart-bar-segment {
        height: 100%; transition: width 0.5s ease;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.65rem; color: var(--white); font-weight: 700; min-width: 0;
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
        gap: 0.5rem; margin-bottom: 1rem;
    }
    .report-box {
        padding: 1rem; text-align: center;
        background: var(--gray-100);
        border: 1px solid var(--gray-200);
        border-radius: var(--radius-md);
    }
    .report-number {
        font-family: var(--font-serif);
        font-size: 1.3rem; font-weight: 700;
    }
    .report-label { font-size: 0.68rem; font-weight: 500; color: var(--gray-400); letter-spacing: 1px; }

    /* ── 시간 차트 ── */
    .time-chart-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
    .time-chart-label { font-size: 0.75rem; min-width: 75px; text-align: right; color: var(--gray-600); white-space: nowrap; }
    .time-chart-bar {
        height: 16px; display: flex; align-items: center; border-radius: 4px;
        padding: 0 6px; font-size: 0.65rem; color: var(--white); font-weight: 500;
        white-space: nowrap; /* '기타' 행 라벨 겹침 해소 */
        transition: width 0.5s ease;
    }

    /* ── 달력 ── */
    .cal-container {
        background: var(--white); border: 1px solid var(--gray-200);
        border-radius: var(--radius-md);
        padding: 1.2rem;
    }
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }
    .cal-dow {
        text-align: center; font-size: 0.7rem; font-weight: 700;
        color: var(--gray-400); padding: 0.4rem 0;
        letter-spacing: 1px;
    }
    .cal-dow-sun { color: var(--red); }
    .cal-dow-sat { color: var(--blue); }
    .cal-day {
        text-align: center; padding: 0.4rem 0.1rem;
        min-height: 2.8rem; font-size: 0.85rem;
        color: var(--gray-600); cursor: pointer;
        border-radius: 6px;
        transition: var(--transition);
        font-variant-numeric: tabular-nums;
    }
    .cal-day:hover { background: var(--gray-100); }
    .cal-day-empty { cursor: default; }
    .cal-day-empty:hover { background: transparent; }
    .cal-day-today {
        background: var(--black); color: var(--white) !important; font-weight: 700;
    }
    .cal-day-today:hover { background: var(--dark); }
    .cal-day-selected { outline: 2px solid var(--black); outline-offset: -2px; }
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
        border-radius: var(--radius-md);
        padding: 0.8rem; margin-bottom: 0.4rem;
    }
    .week-day-card-today {
        border-left: 4px solid var(--black);
        background: var(--gray-100);
    }
    .week-day-header {
        font-family: var(--font-serif);
        font-size: 0.82rem; font-weight: 700; color: var(--black);
        margin-bottom: 8px;
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

    /* ── 메모 ── */
    .memo-item {
        background: var(--white);
        border: 1px solid var(--gray-200);
        border-radius: var(--radius);
        padding: 0.7rem; margin-bottom: 0.4rem;
        font-size: 0.82rem; color: var(--dark);
        transition: var(--transition);
    }
    .memo-item:hover { border-color: var(--gray-400); }
    .memo-time { font-size: 0.68rem; color: var(--gray-400); margin-top: 0.3rem; }

    .selected-date-header {
        font-family: var(--font-serif);
        font-size: 0.95rem; font-weight: 700; color: var(--black);
        padding: 0.5rem 0;
        border-bottom: 2px solid var(--black);
        margin-bottom: 0.5rem;
    }
    .filter-active {
        font-size: 0.78rem; color: var(--gray-600);
        font-weight: 500;
    }

    /* ── 로그인 ── */
    .login-wrap {
        text-align: center; padding: 40px 16px 40px 16px;
    }
    .login-wrap h1 {
        font-family: var(--font-serif);
        font-size: 1.9rem; font-weight: 700; color: var(--black);
        letter-spacing: -0.5px;
        margin: 0 0 8px 0;
    }
    .login-wrap p {
        color: var(--gray-400); font-size: 0.85rem; font-weight: 500;
        letter-spacing: 0.09em; text-transform: uppercase;
        text-indent: 0.09em; /* 자간 후행 여백으로 인한 좌측 편이 상쇄 → 광학 중심 일치 */
        margin: 0;
    }
    /* 로그인 폼(인증 게이트에서만 렌더): 가운데 단일 축, 최대폭 380px */
    .stApp:has(.login-wrap) .block-container {
        max-width: 412px;
        padding-left: 16px; padding-right: 16px;
    }
    .stApp:has(.login-wrap) .stTextInput { margin-bottom: 16px; }

    /* ── 모바일 (~390px 1열 확인 기준) ── */
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem; }
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .report-grid { grid-template-columns: 1fr; }
        .stat-number { font-size: 1.5rem; }
        .app-header h1 { font-size: 1.3rem; }
        .cal-day { min-height: 2.2rem; font-size: 0.75rem; }
        .cal-dot { width: 3px; height: 3px; }
        .task-header { flex-direction: column; align-items: flex-start; }
        .task-badges { margin-top: 0.3rem; }
        .task-title { font-size: 0.9rem; }
        .section-header { font-size: 0.98rem; }
    }
    @media (max-width: 480px) {
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .chart-bar-label, .time-chart-label { min-width: 65px; font-size: 0.7rem; white-space: nowrap; }
    }
</style>
""", unsafe_allow_html=True)

    # 카테고리 배지 색 — 분석 차트와 동일한 단일 소스(core.models.CATEGORY_COLORS)에서 생성.
    # 연한 틴트 배경(8%) + 동색 텍스트 + 연한 동색 보더(33%).
    cat_badge_css = "\n".join(
        f".badge-cat-{name} {{ background: {color}14; border-color: {color}55; color: {color}; }}"
        for name, color in CATEGORY_COLORS.items()
    )
    st.markdown(f"<style>{cat_badge_css}</style>", unsafe_allow_html=True)


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
        html += f'<div class="time-chart-row"><div class="time-chart-label">{CATEGORY_ICONS.get(cat,"")} {cat}</div><div class="time-chart-bar" style="width:{max(m/mx*100,8)}%;background:{color};">{format_duration_compact(m)}</div></div>'
    return html
