"""core/db.py — Supabase 클라이언트 생성 + 모든 DB CRUD 함수 [Phase 1-A, app.py 에서 순수 이동]."""
import streamlit as st
from supabase import create_client

from core.models import now_kst, parse_deadline_kst, parse_tags, get_next_recurrence_date

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "여기에_수파베이스_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "여기에_수파베이스_ANON_KEY")


@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Supabase 연결 실패: {e}")
        return None

supabase = init_supabase()


def safe_db_call(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            st.error(f"데이터베이스 오류: {e}")
            return None
    return wrapper

@safe_db_call
def load_tasks(show_completed=False, search_query="", category="전체", priority="전체", tag_filter=""):
    query = supabase.table("tasks").select("*")
    if not show_completed: query = query.eq("is_completed", False)
    if category != "전체": query = query.eq("category", category)
    if priority != "전체": query = query.eq("priority", priority)
    query = query.order("deadline", desc=False)
    result = query.execute()
    tasks = result.data or []
    if search_query:
        q = search_query.lower()
        tasks = [t for t in tasks if q in (t.get("title") or "").lower() or q in (t.get("description") or "").lower() or q in (t.get("category") or "").lower() or q in (t.get("tags") or "").lower()]
    if tag_filter:
        tf = tag_filter.lower().replace("#", "").strip()
        tasks = [t for t in tasks if tf in (t.get("tags") or "").lower()]
    return tasks

@safe_db_call
def load_all_tasks():
    return (supabase.table("tasks").select("*").order("deadline", desc=False).execute()).data or []

@safe_db_call
def add_task(title, description, deadline, category, priority="중간", recurrence=None, tags=""):
    data = {"title": title, "description": description, "deadline": deadline.isoformat() if deadline else None, "category": category, "priority": priority, "recurrence": recurrence, "tags": tags, "is_completed": False, "timer_started_at": now_kst().isoformat()}
    supabase.table("tasks").insert(data).execute()

@safe_db_call
def complete_task(task):
    now = now_kst().isoformat()
    update_data = {"is_completed": True, "completed_at": now}
    if task.get("timer_started_at") and not task.get("timer_ended_at"):
        update_data["timer_ended_at"] = now
    supabase.table("tasks").update(update_data).eq("id", task["id"]).execute()
    recurrence = task.get("recurrence")
    if recurrence and task.get("deadline"):
        deadline = parse_deadline_kst(task["deadline"])
        if deadline:
            next_deadline = get_next_recurrence_date(deadline, recurrence)
            desc = (task.get("description") or "").replace("- [x]", "- [ ]").replace("- [X]", "- [ ]")
            add_task(task["title"], desc, next_deadline, task.get("category", "기타"), task.get("priority", "중간"), recurrence, task.get("tags", ""))

@safe_db_call
def uncomplete_task(task_id): supabase.table("tasks").update({"is_completed": False, "completed_at": None}).eq("id", task_id).execute()
@safe_db_call
def delete_task(task_id): supabase.table("tasks").delete().eq("id", task_id).execute()
@safe_db_call
def update_task(task_id, title, description, deadline, category, priority="중간", recurrence=None, tags=""):
    supabase.table("tasks").update({"title": title, "description": description, "deadline": deadline.isoformat() if deadline else None, "category": category, "priority": priority, "recurrence": recurrence, "tags": tags}).eq("id", task_id).execute()
@safe_db_call
def start_timer(task_id): supabase.table("tasks").update({"timer_started_at": now_kst().isoformat(), "timer_ended_at": None}).eq("id", task_id).execute()
@safe_db_call
def stop_timer(task_id): supabase.table("tasks").update({"timer_ended_at": now_kst().isoformat()}).eq("id", task_id).execute()
@safe_db_call
def reset_timer(task_id): supabase.table("tasks").update({"timer_started_at": None, "timer_ended_at": None}).eq("id", task_id).execute()
@safe_db_call
def load_memos(): return (supabase.table("memos").select("*").order("created_at", desc=True).limit(50).execute()).data or []
@safe_db_call
def add_memo(content, pinned=False): supabase.table("memos").insert({"content": content, "pinned": pinned}).execute()
@safe_db_call
def delete_memo(memo_id): supabase.table("memos").delete().eq("id", memo_id).execute()
@safe_db_call
def toggle_pin_memo(memo_id, pinned): supabase.table("memos").update({"pinned": not pinned}).eq("id", memo_id).execute()
@safe_db_call
def load_completed_today_count():
    r = supabase.table("tasks").select("id", count="exact").eq("is_completed", True).gte("completed_at", now_kst().replace(hour=0, minute=0, second=0).isoformat()).execute()
    return r.count or 0
@safe_db_call
def load_completed_tasks(limit=100): return (supabase.table("tasks").select("*").eq("is_completed", True).order("completed_at", desc=True).limit(limit).execute()).data or []
@safe_db_call
def load_all_tags():
    result = supabase.table("tasks").select("tags").execute()
    all_tags = []
    for row in (result.data or []): all_tags.extend(parse_tags(row.get("tags")))
    return list(set(all_tags))
