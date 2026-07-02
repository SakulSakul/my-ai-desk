"""ui/sidebar.py — 사이드바: 퀵 메모 + 검색/필터 [Phase 1-A, app.py 에서 순수 이동].

filter_category / filter_priority / filter_tag / sort_by 는 session_state 에 기록되어
ui/tasks.py(업무 목록)가 소비한다. 검색어는 위젯 반환값이므로 함수 반환으로 전달.
"""
import streamlit as st

from core.models import CATEGORIES, PRIORITIES, format_dt
from core.db import add_memo, load_memos, toggle_pin_memo, delete_memo, load_all_tags


def render_sidebar() -> str:
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
    return search_query
