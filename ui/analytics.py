"""ui/analytics.py — 업무 현황·시간 분석 + 히스토리·리포트 [Phase 1-A, app.py 에서 순수 이동]."""
import streamlit as st

from core.models import (
    CATEGORY_COLORS, CATEGORY_ICONS,
    format_dt, parse_deadline_kst, calc_duration, calc_duration_minutes,
    format_minutes, parse_tags, build_weekly_report, build_monthly_report,
)
from core.db import load_all_tasks
from ui.components import render_category_chart, render_time_chart


def render_analytics(all_active, all_completed):
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
