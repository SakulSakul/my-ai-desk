"""ui/calendar_view.py — 달력(월간/주간) [Phase 1-A, app.py 에서 순수 이동].

cal_year / cal_month / selected_date 는 이 화면 전용 session_state.
(stdlib calendar 와의 이름 충돌을 피해 모듈명은 calendar_view.)
"""
import streamlit as st
import calendar
from datetime import datetime, timedelta

from core.models import PRIORITIES, now_kst, parse_deadline_kst, get_urgency, build_task_date_map
from core.db import load_all_tasks
from ui.components import render_monthly_calendar, render_weekly_view


def render_calendar():
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
            st.markdown(f'<div style="text-align:center;font-family:var(--font-serif);font-size:1rem;font-weight:700;color:var(--black);margin-bottom:0.5rem;">{mon.strftime("%m/%d")} — {sun.strftime("%m/%d")} 이번 주</div>', unsafe_allow_html=True)
            st.markdown(render_weekly_view(tdm), unsafe_allow_html=True)
