"""jobs/_http.py — 재시도 가능한 HTTP 유틸 (표준 라이브러리 전용).

배경: 2026-07-23 daily_alarm #113 실패 — kakao_notify.supabase_get 의 15초 읽기
타임아웃 **한 번**으로 그날 알림 전체가 유실됐다(텔레그램은 이미 발송된 뒤였다).
카카오 토큰 문제가 아니라 단발 네트워크 지연이었고, 재시도가 없던 것이 근본 원인이다.

정책 — 멱등성으로 갈린다:
  재시도 O · 조회(GET)·토큰 갱신(POST, 멱등)
      네트워크 오류(URLError/TimeoutError) · HTTP 5xx · 429
  재시도 X · HTTP 4xx (429 제외)
      자격증명·요청 오류는 재시도해도 같은 결과다. 즉시 시끄럽게 실패해야
      KOE011 류 진단이 살아있다. 예외 본문을 읽지 않고 그대로 전파해
      호출부의 기존 `exc.read()` 진단 로직을 보존한다.
  재시도 X · 발송(POST, 비멱등) — send_kakao / telegram sendMessage
      타임아웃이 나도 서버는 이미 발송했을 수 있다. 재시도는 곧 중복 발송이므로
      `urlopen_once` 로 단일 시도만 한다(타임아웃만 상향).

예산: 시도 3회 · 백오프 1s→2s · 시도별 타임아웃 20초.
      단순히 20×3+1+2 = 63초라 "최악 1분 이내" 요구를 넘기므로,
      전체 예산 60초를 두고 각 시도의 타임아웃을 남은 예산으로 clamp 한다.
"""
from __future__ import annotations

import socket
import sys
import time
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

DEFAULT_TIMEOUT = 20.0      # 기존 15초에서 상향 (단발 지연 흡수)
DEFAULT_ATTEMPTS = 3
TOTAL_BUDGET = 60.0         # 최악 총소요 상한
BACKOFF = (1.0, 2.0)        # 시도 사이 대기 (지수)
MIN_TIMEOUT = 1.0           # 이보다 적게 남았으면 시도할 가치가 없다


class HttpResult(NamedTuple):
    status: int
    body: bytes


def _log(msg: str) -> None:
    """재시도는 조용히 넘어가면 안 된다 — 로그가 없으면 장애가 은폐된다."""
    print(f"[http] {msg}", file=sys.stderr)


def _is_retryable_status(code: int) -> bool:
    return code >= 500 or code == 429


def urlopen_once(req, *, timeout: float = DEFAULT_TIMEOUT) -> HttpResult:
    """단일 시도. 재시도하면 안 되는 비멱등 요청(발송)에 쓴다."""
    with urlopen(req, timeout=timeout) as resp:
        return HttpResult(resp.status, resp.read())


def urlopen_with_retry(
    req,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    budget: float = TOTAL_BUDGET,
    label: str = "request",
) -> HttpResult:
    """멱등 요청(GET·토큰 갱신)용 재시도 래퍼.

    4xx(429 제외)는 재시도하지 않고 HTTPError 를 그대로 올린다.
    모든 시도가 실패하면 마지막 예외를 전파한다 — 삼키지 않는다.
    """
    deadline = time.monotonic() + budget
    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        remaining = deadline - time.monotonic()
        if remaining < MIN_TIMEOUT:
            _log(f"{label}: 예산 {budget:.0f}s 소진 — 시도 {attempt}/{attempts} 생략")
            break

        try:
            return urlopen_once(req, timeout=min(timeout, remaining))
        except HTTPError as exc:
            if not _is_retryable_status(exc.code):
                raise  # 본문 미소비 — 호출부가 exc.read() 로 진단할 수 있어야 한다
            last_exc, reason = exc, f"HTTP {exc.code}"
        except (TimeoutError, socket.timeout) as exc:
            last_exc, reason = exc, "timeout"
        except URLError as exc:
            last_exc, reason = exc, f"network: {exc.reason}"

        if attempt >= attempts:
            _log(f"{label}: 시도 {attempt}/{attempts} 실패({reason}) — 재시도 소진")
            break

        delay = BACKOFF[min(attempt - 1, len(BACKOFF) - 1)]
        if deadline - time.monotonic() <= delay + MIN_TIMEOUT:
            _log(f"{label}: 시도 {attempt}/{attempts} 실패({reason}) — 남은 예산 부족, 중단")
            break
        _log(f"{label}: 시도 {attempt}/{attempts} 실패({reason}) — {delay:.0f}s 후 재시도")
        time.sleep(delay)

    if last_exc is None:  # pragma: no cover — 예산 0 이하로 호출한 경우만
        raise RuntimeError(f"{label}: 시도 없이 종료 (budget={budget})")
    raise last_exc
