import streamlit as st
from datetime import datetime, timedelta, timezone, time as dt_time, date as dt_date
import calendar
from collections import Counter, defaultdict

from core.models import (
    KST, CATEGORIES, CATEGORY_COLORS, CATEGORY_ICONS, PRIORITIES,
    PRIORITY_ORDER, RECURRENCE_OPTIONS,
    now_kst, format_dt, parse_deadline_kst, get_urgency,
    calc_duration, calc_duration_minutes, format_minutes,
    calc_checklist_progress, parse_tags, get_next_recurrence_date,
    build_task_date_map, build_weekly_report, build_monthly_report,
)
# core.db import 시점에 Supabase 클라이언트가 생성된다(원본과 동일하게 set_page_config 이전).
from core.db import (
    load_tasks, load_all_tasks, add_task, complete_task, uncomplete_task,
    delete_task, update_task, start_timer, stop_timer, reset_timer,
    load_memos, add_memo, delete_memo, toggle_pin_memo,
    load_completed_today_count, load_completed_tasks, load_all_tags,
)
from ui.components import (
    inject_css, render_monthly_calendar, render_weekly_view,
    render_category_chart, render_time_chart,
)
from ui.sidebar import render_sidebar

# ============================================
# 설정
# ============================================
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

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
# CSS — ui/components.inject_css 로 이동
# ============================================
inject_css()


# ============================================
# 세션 상태 / 유틸
# ============================================
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
# 사이드바 — ui/sidebar.render_sidebar 로 이동
# ============================================
search_query = render_sidebar()


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

                # 원클릭 완료 + 상세 버튼
                ac1, ac2, ac3 = st.columns([1, 1, 4])
                with ac1:
                    if st.button("✅ 완료", key=f"quick_{tab_category}_{task['id']}", use_container_width=True):
                        complete_task(task)
                        st.toast("🎉 완료! 다음 회차 생성됨" if rec else "🎉 수고하셨습니다!")
                        st.balloons(); st.rerun()
                with ac2:
                    if st.button("✏️ 수정", key=f"edit_{tab_category}_{task['id']}", use_container_width=True):
                        st.session_state[f"editing_{task['id']}"] = True; st.rerun()

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
                    if st.button("🗑️ 삭제", key=f"del_{tab_category}_{task['id']}"): delete_task(task["id"]); st.toast("삭제됨."); st.rerun()

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
