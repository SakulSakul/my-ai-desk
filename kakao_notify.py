"""
My AI Desk - 카카오톡 매일 아침 알림
GitHub Actions에서 매일 아침 실행되어, 오늘 할 일을 카카오톡으로 보내줍니다.
"""

import os
import json
import subprocess
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = os.environ.get("GH_REPO", "")

KST = timezone(timedelta(hours=9))


def supabase_get(table, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_access_token():
    """Refresh token으로 access token 재발급. 새 refresh token이 있으면 함께 반환."""
    data = urlencode({
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }).encode()
    req = Request("https://kauth.kakao.com/oauth/token", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(req) as resp:
        result = json.loads(resp.read().decode())
    new_refresh_token = result.get("refresh_token")  # 만료 1달 전에만 반환됨
    return result["access_token"], new_refresh_token


def rotate_refresh_token(new_token):
    """GitHub Secret KAKAO_REFRESH_TOKEN 자동 갱신"""
    if not GH_TOKEN or not GH_REPO:
        print("[WARN] GH_TOKEN 또는 GH_REPO 없음 — 토큰 갱신 스킵")
        return
    result = subprocess.run(
        ["gh", "secret", "set", "KAKAO_REFRESH_TOKEN", "--body", new_token, "--repo", GH_REPO],
        env={**os.environ, "GH_TOKEN": GH_TOKEN},
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[OK] KAKAO_REFRESH_TOKEN 자동 갱신 완료")
    else:
        print(f"[WARN] 토큰 갱신 실패: {result.stderr}")


def send_kakao(message, access_token):
    """카카오톡 나에게 보내기"""
    template = json.dumps({
        "object_type": "text",
        "text": message[:200],
        "link": {"web_url": "", "mobile_web_url": ""},
    })
    data = urlencode({"template_object": template}).encode()
    req = Request("https://kapi.kakao.com/v2/api/talk/memo/default/send", data=data)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    now = datetime.now(KST)
    today_str = now.strftime("%Y-%m-%d")
    today_display = now.strftime("%m월 %d일 (%a)")

    tasks = supabase_get("tasks", "is_completed=eq.false&order=deadline.asc.nullslast")

    access_token, new_refresh_token = get_access_token()

    if new_refresh_token:
        print("[INFO] 새 refresh token 감지 — Secret 갱신 시도")
        rotate_refresh_token(new_refresh_token)

    if not tasks:
        message = f"☀️ {today_display} 좋은 아침!\n\n📋 오늘 등록된 업무가 없습니다.\n여유로운 하루 보내세요! 🎉"
        send_kakao(message, access_token)
        return

    overdue, today_tasks, upcoming, no_deadline = [], [], [], []

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

    lines = [f"☀️ {today_display} 업무 브리핑\n"]

    if overdue:
        lines.append(f"🚨 기한 초과 ({len(overdue)}건)")
        for t in overdue[:3]:
            dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
            lines.append(f"  • {t['title']} {dl.strftime('%m/%d')}")
        lines.append("")

    if today_tasks:
        lines.append(f"📌 오늘 마감 ({len(today_tasks)}건)")
        for t in today_tasks[:3]:
            dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
            lines.append(f"  • {t['title']} {dl.strftime('%H:%M')}")
        lines.append("")

    if upcoming:
        lines.append(f"📅 3일 이내 ({len(upcoming)}건)")
        for t in upcoming[:3]:
            dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
            lines.append(f"  • {t['title']} {dl.strftime('%m/%d')}")
        lines.append("")

    lines.append(f"전체 진행 중: {len(tasks)}건\n오늘도 화이팅! 💪")

    message = "\n".join(lines)
    send_kakao(message, access_token)
    print(f"[OK] 카카오톡 알림 발송 완료: {now.isoformat()}")


if __name__ == "__main__":
    main()
