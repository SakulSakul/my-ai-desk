"""jobs/kakao_notify.py — 카카오톡 '나에게 보내기' 아침 브리핑 [Path 2, 심의 수정본].

refresh token 저장소: Supabase 테이블(app_secrets). 워크플로 안 Secrets:write PAT 불필요.
- 시작 시 Supabase에서 refresh token 로드 → 갱신 → 새 토큰이 오면 Supabase에 되쓴다.
- stdlib urllib 만 사용(무의존).

3차 심의 수정:
  [write 검증·재시도] write_secret 을 Prefer: return=representation 으로 바꿔 '갱신된 행'을 확인.
        0행 no-op(키 부재)·저장 불일치를 잡고, 실패 시 재시도 후 시끄럽게 죽는다(_die).
        → 새 토큰을 조용히 잃는 사각지대 제거. (단, 최종 실패 시 새 토큰 값은 회수 불가 → 수동 재발급.)
  [전송 확인] send_kakao 가 카카오 응답의 result_code 를 확인 → 200인데 미도달인 경우를 실패로 승격.

토큰 회전 원리(카카오): refresh token 유효기간 ~2개월, 만료 1개월 이내에 갱신을 호출하면
새 refresh token 이 함께 반환된다. cron 이 매일 돌면 이 조건을 항상 만족 → 영구 유지.

환경변수(GitHub Secrets):
  SUPABASE_URL
  SUPABASE_KEY               anon 키 (tasks 조회)
  SUPABASE_SERVICE_ROLE_KEY  service_role 키 (app_secrets 읽기/쓰기 전용)
  KAKAO_REST_API_KEY
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]                       # anon
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]

KST = timezone(timedelta(hours=9))
SECRET_KEY_NAME = "kakao_refresh_token"


def _die(msg: str) -> None:
    print(f"[kakao] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def supabase_get(table: str, params: str = "", key: str | None = None):
    key = key or SUPABASE_KEY
    req = Request(f"{SUPABASE_URL}/rest/v1/{table}?{params}")
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Accept", "application/json")
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def read_secret(name: str) -> str:
    rows = supabase_get("app_secrets", f"key=eq.{name}&select=value",
                        key=SUPABASE_SERVICE_ROLE_KEY)
    if not rows:
        _die(f"app_secrets 에 '{name}' 없음 — app_secrets.sql 로 시드 먼저 할 것")
    return rows[0]["value"]


def write_secret(name: str, value: str, retries: int = 3) -> None:
    """PATCH app_secrets 후 '갱신된 행'을 확인(return=representation).

    0행 갱신(키 부재)·값 불일치를 실패로 처리하고, 일시 오류는 재시도한다.
    최종 실패 시 _die 로 시끄럽게 죽어 워크플로 실패 → 실패 알림이 발화한다.
    """
    body = json.dumps({
        "value": value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).encode()
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(f"{SUPABASE_URL}/rest/v1/app_secrets?key=eq.{name}",
                          data=body, method="PATCH")
            req.add_header("apikey", SUPABASE_SERVICE_ROLE_KEY)
            req.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_ROLE_KEY}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Prefer", "return=representation")  # 갱신된 행 반환 → 검증용
            with urlopen(req, timeout=15) as resp:
                updated = json.loads(resp.read().decode() or "[]")
            if not updated:
                raise RuntimeError(f"PATCH가 0행 갱신 (key='{name}' 부재?) — 저장 안 됨")
            if updated[0].get("value") != value:
                raise RuntimeError("저장 후 값 불일치 (write-after-read 검증 실패)")
            print(f"[kakao] refresh token 저장·검증 완료 (attempt {attempt})")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"[kakao] WARN: write_secret 실패 attempt {attempt}: {exc}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 * attempt)
    _die(f"refresh token 저장 {retries}회 실패: {last_err} — 새 토큰 유실. "
         f"카카오 토큰 재발급 후 app_secrets 를 수동 갱신해야 함")


def get_access_token(refresh_token: str):
    """refresh token 으로 access token 재발급. 새 refresh token 은 만료 임박 시에만 반환됨."""
    data = urlencode({
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": refresh_token,
    }).encode()
    req = Request("https://kauth.kakao.com/oauth/token", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
    return result["access_token"], result.get("refresh_token")


def send_kakao(message: str, access_token: str):
    template = json.dumps({
        "object_type": "text",
        "text": message[:200],
        "link": {"web_url": "", "mobile_web_url": ""},
    })
    data = urlencode({"template_object": template}).encode()
    req = Request("https://kapi.kakao.com/v2/api/talk/memo/default/send", data=data)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
    # 200 이어도 result_code != 0 이면 미도달 → 실패로 승격(조용한 미도달 방지)
    if result.get("result_code") not in (0, "0"):
        _die(f"카카오 발송 응답 이상: {result}")
    return result


def build_message() -> str:
    now = datetime.now(KST)
    today_str = now.strftime("%Y-%m-%d")
    today_display = now.strftime("%m월 %d일 (%a)")
    tasks = supabase_get("tasks", "is_completed=eq.false&order=deadline.asc.nullslast")
    if not tasks:
        return (f"☀️ {today_display} 좋은 아침!\n\n"
                f"📋 오늘 등록된 업무가 없습니다.\n여유로운 하루 보내세요! 🎉")

    overdue, today_tasks, upcoming, no_deadline = [], [], [], []
    for t in tasks:
        dl = t.get("deadline")
        if not dl:
            no_deadline.append(t)
            continue
        try:
            deadline = datetime.fromisoformat(dl.replace("Z", "+00:00")).astimezone(KST)
            dd = deadline.strftime("%Y-%m-%d")
            if deadline < now:
                overdue.append(t)
            elif dd == today_str:
                today_tasks.append(t)
            elif (deadline - now).days <= 3:
                upcoming.append(t)
        except Exception:
            no_deadline.append(t)

    def fmt(t, f):
        dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00")).astimezone(KST)
        return f" • {t['title']} {dl.strftime(f)}"

    lines = [f"☀️ {today_display} 업무 브리핑\n"]
    if overdue:
        lines.append(f"🚨 기한 초과 ({len(overdue)}건)")
        lines += [fmt(t, "%m/%d") for t in overdue[:3]]
        lines.append("")
    if today_tasks:
        lines.append(f"📌 오늘 마감 ({len(today_tasks)}건)")
        lines += [fmt(t, "%H:%M") for t in today_tasks[:3]]
        lines.append("")
    if upcoming:
        lines.append(f"📅 3일 이내 ({len(upcoming)}건)")
        lines += [fmt(t, "%m/%d") for t in upcoming[:3]]
        lines.append("")
    lines.append(f"전체 진행 중: {len(tasks)}건\n오늘도 화이팅! 💪")
    return "\n".join(lines)


def main() -> None:
    refresh_token = read_secret(SECRET_KEY_NAME)

    try:
        access_token, new_refresh = get_access_token(refresh_token)
    except HTTPError as e:
        detail = e.read().decode(errors="replace")[:200]
        _die(f"토큰 갱신 실패 HTTP {e.code}: {detail} "
             f"(refresh token 만료면 재발급 후 app_secrets 갱신 필요)")
    except URLError as e:
        _die(f"토큰 갱신 네트워크 실패: {e.reason}")

    # 새 refresh token 은 send 이전에 검증 저장(저장 실패 시 여기서 죽어 실패 알림 발화).
    if new_refresh:
        print("[kakao] 새 refresh token 감지 — Supabase(app_secrets)에 저장")
        write_secret(SECRET_KEY_NAME, new_refresh)

    send_kakao(build_message(), access_token)
    print(f"[kakao] OK: 발송 완료 {datetime.now(KST).isoformat()}")


if __name__ == "__main__":
    main()
