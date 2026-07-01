"""
My AI Desk - 텔레그램 매일 아침 알림
GitHub Actions에서 매일 아침 실행되어, 오늘 할 일을 텔레그램으로 보내줍니다.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote

# ============================================
# 환경 변수에서 설정값 읽기 (GitHub Secrets)
# ============================================
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

KST = timezone(timedelta(hours=9))


def supabase_get(table, params=""):
    """Supabase REST API로 데이터 조회"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())


def send_telegram(message):
    """텔레그램 봇으로 메시지 발송"""
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        f"/sendMessage?chat_id={TELEGRAM_CHAT_ID}"
        f"&text={quote(message)}&parse_mode=HTML"
    )
    req = Request(url)
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    now = datetime.now(KST)
    today_str = now.strftime("%Y-%m-%d")
    today_display = now.strftime("%m월 %d일 (%a)")

    # 1) 미완료 업무 전체 가져오기
    tasks = supabase_get(
        "tasks",
        "is_completed=eq.false&order=deadline.asc.nullslast"
    )

    if not tasks:
        message = (
            f"☀️ <b>{today_display} 좋은 아침!</b>\n\n"
            f"📋 오늘 등록된 업무가 없습니다.\n"
            f"여유로운 하루 보내세요! 🎉"
        )
        send_telegram(message)
        return

    # 2) 분류: 기한초과 / 오늘마감 / 다가오는 업무
    overdue = []
    today_tasks = []
    upcoming = []
    no_deadline = []

    for t in tasks:
        dl = t.get("deadline")
        if not dl:
            no_deadline.append(t)
            continue

        try:
            deadline = datetime.fromisoformat(dl.replace("Z", "+00:00")).astimezone(KST)
            deadline_date = deadline.strftime("%Y-%m-%d")

            if deadline < now:
                overdue.append(t)
            elif deadline_date == today_str:
                today_tasks.append(t)
            elif (deadline - now).days <= 3:
                upcoming.append(t)
        except:
            no_deadline.append(t)

    # 3) 메시지 구성
    lines = [f"☀️ <b>{today_display} 업무 브리핑</b>\n"]

    if overdue:
        lines.append(f"🚨 <b>기한 초과 ({len(overdue)}건)</b>")
        for t in overdue[:5]:
            dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
            lines.append(f"  • {t['title']}  ⏰ {dl.strftime('%m/%d %H:%M')}")
        lines.append("")

    if today_tasks:
        lines.append(f"📌 <b>오늘 마감 ({len(today_tasks)}건)</b>")
        for t in today_tasks:
            dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
            lines.append(f"  • {t['title']}  ⏰ {dl.strftime('%H:%M')}")
        lines.append("")

    if upcoming:
        lines.append(f"📅 <b>3일 이내 ({len(upcoming)}건)</b>")
        for t in upcoming[:5]:
            dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
            lines.append(f"  • {t['title']}  📅 {dl.strftime('%m/%d')}")
        lines.append("")

    if no_deadline:
        lines.append(f"📝 <b>마감일 미지정 ({len(no_deadline)}건)</b>")
        for t in no_deadline[:3]:
            lines.append(f"  • {t['title']}")
        lines.append("")

    total = len(tasks)
    lines.append(f"──────────────")
    lines.append(f"전체 진행 중: {total}건")
    lines.append(f"오늘도 화이팅! 💪")

    message = "\n".join(lines)
    send_telegram(message)
    print(f"[OK] 알림 발송 완료: {now.isoformat()}")


if __name__ == "__main__":
    main()
