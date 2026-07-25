"""jobs/keepalive.py — Supabase 최소 핑 (무료티어 7일 pause 방지).

[v3.1 변경 — 심의 버그2 반영]
- supabase SDK + 매일 pip install 제거. **stdlib urllib만 사용(무의존)**.
  가디언(핑)은 지켜야 할 대상보다 단순해야 한다 — 매일 네트워크 설치·의존성 트리는
  그 자체가 새 실패점이다. Supabase REST 엔드포인트에 GET 한 방이면 충분.
- 느슨한 핀("supabase==2.*") 제거 → 설치할 것이 없으니 == 원칙 위반도 사라짐.

동작: {SUPABASE_URL}/rest/v1/{TABLE}?select=id&limit=1 로 가벼운 read.
- 2xx면 성공(활성 신호). 그 외/네트워크 오류면 exit 1 -> keepalive.yml이 텔레그램 알림.
- 조용한 실패 금지: 예외를 삼키지 말고 stderr로 남기고 죽는다.

환경변수(모두 GitHub Secrets에서 주입):
  SUPABASE_URL   예) https://xxxx.supabase.co
  SUPABASE_KEY   anon 또는 service_role 키
  KEEPALIVE_TABLE(선택, 기본 "tasks")

주의: pause 트리거가 'REST read 핑'을 활동으로 인정하는지는 외부 정책 의존(검증 대상).
      README-keepalive.md의 실측 절차로 확인할 것. (인정 안 하면 A·B 양쪽 생명선이 무너짐)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from _http import urlopen_with_retry  # 워크플로는 `python jobs/x.py` 실행 → jobs/ 가 sys.path[0]


def _fail(msg: str) -> None:
    print(f"[keepalive] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    table = os.environ.get("KEEPALIVE_TABLE", "tasks")
    if not url or not key:
        _fail("SUPABASE_URL / SUPABASE_KEY 누락 (시크릿 확인)")

    base = url.rstrip("/")
    endpoint = f"{base}/rest/v1/{table}?select=id&limit=1"
    req = urllib.request.Request(endpoint, method="GET")
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Accept", "application/json")

    try:
        # 핑(GET)은 멱등 — 재시도 적용. 가디언이 단발 지연으로 죽으면
        # 지키려던 대상(무료티어 pause 방지)이 무너진다.
        result = urlopen_with_retry(req, label="keepalive")
        status, body = result.status, result.body[:512]  # 본문은 확인용 소량만
    except urllib.error.HTTPError as exc:
        _fail(f"Supabase 핑 HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        _fail(f"Supabase 핑 네트워크 실패: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Supabase 핑 예외: {type(exc).__name__}: {exc}")

    if not (200 <= status < 300):
        _fail(f"Supabase 핑 비정상 상태코드: {status}")

    # 본문이 JSON 배열인지 가볍게 검증(테이블/권한 오설정 조기 발견)
    try:
        json.loads(body.decode("utf-8") or "[]")
    except Exception:  # noqa: BLE001
        print("[keepalive] WARN: 응답 본문 파싱 실패(핑 자체는 성공)", file=sys.stderr)

    print(f"[keepalive] OK: Supabase 핑 성공 (status={status}, table={table})")


if __name__ == "__main__":
    main()
