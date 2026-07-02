"""core/models.py — stdlib 전용 순수 함수·도메인 상수 [Phase 1-A, app.py 에서 순수 이동].

규칙: import 는 표준 라이브러리만. streamlit·supabase 금지.
시각 판정은 KST 단일 기준. (1-B 에서 jobs/ 가 이 모듈을 import 할 예정.)
"""
from datetime import datetime, timedelta, timezone
import calendar
from typing import Optional
from collections import Counter, defaultdict
import re

KST = timezone(timedelta(hours=9))

CATEGORIES = ["전체", "공정거래", "동반성장", "사회공헌", "환경", "기타"]
CATEGORY_COLORS = {
    "공정거래": "#1a1a1a",
    "동반성장": "#c8a26e",
    "사회공헌": "#3a7d5c",
    "환경": "#4a90a4",
    "기타": "#8c8c8c",
}
CATEGORY_ICONS = {
    "공정거래": "⚖️",
    "동반성장": "🤝",
    "사회공헌": "💛",
    "환경": "🌿",
    "기타": "📁",
}
PRIORITIES = {"높음": "🔴", "중간": "🟡", "낮음": "🟢"}
PRIORITY_ORDER = {"높음": 0, "중간": 1, "낮음": 2}

RECURRENCE_OPTIONS = {
    "없음": None, "매일": "daily", "매주": "weekly",
    "격주": "biweekly", "매월": "monthly",
}


def now_kst() -> datetime:
    return datetime.now(KST)

def format_dt(dt_str: Optional[str]) -> str:
    if not dt_str: return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%m/%d(%a) %H:%M")
    except (ValueError, TypeError):
        return dt_str

def parse_deadline_kst(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str: return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(KST)
    except (ValueError, TypeError):
        return None

def get_urgency(deadline_str: Optional[str]) -> tuple[str, str]:
    if not deadline_str: return "upcoming", ""
    deadline = parse_deadline_kst(deadline_str)
    if not deadline: return "upcoming", ""
    now = now_kst()
    diff = deadline - now
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        overdue_hours = abs(total_seconds) / 3600
        if overdue_hours < 24:
            return "overdue", f"⏰ {int(overdue_hours)}시간 초과"
        return "overdue", f"⏰ {int(overdue_hours / 24)}일 초과"
    deadline_date = deadline.date()
    today_date = now.date()
    day_diff = (deadline_date - today_date).days
    if day_diff == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            return "today", f"⚡ {diff.seconds // 60}분 남음"
        return "today", f"⚡ {hours}시간 남음"
    elif day_diff == 1:
        return "upcoming", "📅 내일 마감"
    else:
        return "upcoming", f"📅 {day_diff}일 남음"

def calc_duration(created_str, completed_str):
    if not created_str or not completed_str: return ""
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
    except: return ""

def calc_duration_minutes(start_str, end_str):
    if not start_str or not end_str: return 0.0
    try:
        s = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        return max((e - s).total_seconds() / 60, 0)
    except: return 0.0

def format_minutes(mins):
    if mins < 1: return "1분 미만"
    total = int(mins)
    d, h, m = total // 1440, (total % 1440) // 60, total % 60
    parts = []
    if d > 0: parts.append(f"{d}일")
    if h > 0: parts.append(f"{h}시간")
    if m > 0: parts.append(f"{m}분")
    return " ".join(parts) if parts else "1분 미만"

def calc_checklist_progress(description):
    if not description: return None
    total = checked = 0
    for line in description.split("\n"):
        s = line.strip()
        if s.startswith("- [ ]") or s.startswith("- [x]") or s.startswith("- [X]"):
            total += 1
            if s.startswith("- [x]") or s.startswith("- [X]"): checked += 1
    return (checked, total) if total > 0 else None

def parse_tags(tags_str):
    if not tags_str: return []
    cleaned = tags_str.replace("#", "")
    tags = re.split(r'[,\s]+', cleaned)
    return [t.strip() for t in tags if t.strip()]

def get_next_recurrence_date(current_deadline, recurrence):
    if recurrence == "daily": return current_deadline + timedelta(days=1)
    elif recurrence == "weekly": return current_deadline + timedelta(weeks=1)
    elif recurrence == "biweekly": return current_deadline + timedelta(weeks=2)
    elif recurrence == "monthly":
        month = current_deadline.month + 1
        year = current_deadline.year
        if month > 12: month, year = 1, year + 1
        day = min(current_deadline.day, calendar.monthrange(year, month)[1])
        return current_deadline.replace(year=year, month=month, day=day)
    return current_deadline

def build_task_date_map(tasks):
    dm = {}
    for t in tasks:
        dl = parse_deadline_kst(t.get("deadline"))
        if dl: dm.setdefault(dl.strftime("%Y-%m-%d"), []).append(t)
    return dm

def build_weekly_report(completed, all_tasks):
    now = now_kst(); mon = now.date()-timedelta(days=now.date().weekday()); sun = mon+timedelta(days=6)
    wc = [t for t in completed if (ca:=parse_deadline_kst(t.get("completed_at"))) and mon<=ca.date()<=sun]
    tm = sum(calc_duration_minutes(t.get("timer_started_at"),t.get("timer_ended_at")) for t in wc)
    cc = Counter(t.get("category","기타") for t in wc)
    dc = defaultdict(int)
    for t in wc:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca: dc[ca.strftime("%m/%d")] += 1
    return {"period":f"{mon.strftime('%m/%d')}~{sun.strftime('%m/%d')}","total_completed":len(wc),"total_minutes":tm,"cat_counts":dict(cc),"daily_counts":dict(dc)}

def build_monthly_report(completed, all_tasks):
    now = now_kst(); y,m = now.year, now.month
    mc = [t for t in completed if (ca:=parse_deadline_kst(t.get("completed_at"))) and ca.year==y and ca.month==m]
    tm = sum(calc_duration_minutes(t.get("timer_started_at"),t.get("timer_ended_at")) for t in mc)
    cc = Counter(t.get("category","기타") for t in mc)
    wc = defaultdict(int)
    for t in mc:
        ca = parse_deadline_kst(t.get("completed_at"))
        if ca: wc[f"{(ca.day-1)//7+1}주차"] += 1
    return {"period":f"{y}년 {m}월","total_completed":len(mc),"total_minutes":tm,"cat_counts":dict(cc),"weekly_counts":dict(wc)}
