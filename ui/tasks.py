"""ui/tasks.py — [전체] 탭: 검색·필터 / 업무 등록 폼 / 업무 목록(카테고리 탭) / 완료된 업무.

[Phase 1-A 순수 이동 → Phase 2 개편] 검색·필터는 구 사이드바에서 이 탭 상단으로 흡수.
filter_*/sort_by session_state 키와 위젯 키(quick_*/del_* 등)는 기존 그대로 유지.
"""
import streamlit as st
from datetime import datetime, time as dt_time

from core.models import (
    KST, CATEGORIES, CATEGORY_ICONS, PRIORITIES, PRIORITY_ORDER, RECURRENCE_OPTIONS,
    now_kst, format_dt, parse_deadline_kst, get_urgency,
    calc_duration, calc_duration_minutes, format_minutes,
    calc_checklist_progress, parse_tags,
)
from core.db import (
    load_tasks, add_task, complete_task, uncomplete_task, delete_task,
    update_task, start_timer, stop_timer, reset_timer, load_completed_tasks,
    load_all_tags,
)


def render_filters() -> str:
    """검색·필터·정렬 (구 사이드바 → [전체] 탭 상단 expander) [Phase 2]."""
    with st.expander("🔍 검색 & 필터", expanded=False):
        search_query = st.text_input("검색", placeholder="제목, 내용, 태그...", label_visibility="collapsed", key="search_input")
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
    return search_query


def render_all_tab():
    """[전체] 탭 합성: 필터 → 등록 폼 → 목록 → 완료 [Phase 2]."""
    search_query = render_filters()
    render_task_form()
    render_task_list(search_query)
    render_completed_tasks()


def render_task_form():
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


def render_task_list(search_query):
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


def render_completed_tasks():
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
