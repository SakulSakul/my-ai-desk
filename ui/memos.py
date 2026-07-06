"""ui/memos.py — [메모] 탭: 퀵 메모 [Phase 2, 사이드바에서 이동].

기능은 1-A의 ui/sidebar.py 퀵 메모와 동일(작성/고정 작성/목록/고정 토글/삭제).
위젯 키(pin_*/del_memo_*)는 기존 그대로 유지.
"""
import streamlit as st

from core.models import format_dt
from core.db import add_memo, load_memos, toggle_pin_memo, delete_memo


def render_memos():
    st.markdown('<div class="section-header">📝 퀵 메모</div>', unsafe_allow_html=True)
    memo_input = st.text_area("메모", placeholder="번뜩이는 아이디어, URL, 메모...", height=80, label_visibility="collapsed", key="memo_input")
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
                bs = "border-color:var(--accent);" if is_pinned else ""
                st.markdown(f'<div class="memo-item" style="{bs}">{memo["content"][:120]}{"..." if len(memo["content"])>120 else ""}<div class="memo-time">{format_dt(memo["created_at"])}</div></div>', unsafe_allow_html=True)
            with cp:
                if st.button("📌", key=f"pin_{memo['id']}", help="고정 토글"): toggle_pin_memo(memo['id'], is_pinned); st.rerun()
            with cd:
                if st.button("🗑", key=f"del_memo_{memo['id']}", help="삭제"): delete_memo(memo['id']); st.rerun()

    st.markdown("---")
    st.markdown('<div style="text-align:center;font-size:0.7rem;color:var(--gray-400);letter-spacing:1px;">MY AI DESK v3.0<br>CSR EDITION</div>', unsafe_allow_html=True)
