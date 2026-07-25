"""jobs/ 재시도 정책 검증 [§2-3] — 전부 mock, 실제 API 호출 없음.

07-23 daily_alarm 실패(단발 타임아웃 → 알림 유실)가 재발하지 않는지,
그리고 발송 경로가 중복 발송으로 번지지 않는지를 고정한다.
"""
from __future__ import annotations

import io
import json
import os
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "jobs"

# 워크플로와 동일한 import 경로(`python jobs/x.py` → jobs/ 가 sys.path[0])를 재현.
if str(JOBS) not in sys.path:
    sys.path.insert(0, str(JOBS))

# job 모듈들은 import 시점에 시크릿을 읽으므로 더미를 먼저 넣는다(실토큰 미사용).
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-anon")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-service")
os.environ.setdefault("KAKAO_REST_API_KEY", "fake-rest")
os.environ.setdefault("TELEGRAM_TOKEN", "fake-tg")
os.environ.setdefault("TELEGRAM_CHAT_ID", "12345")

import _http  # noqa: E402
import kakao_notify  # noqa: E402
import telegram_notify  # noqa: E402


class FakeResponse:
    """urlopen 컨텍스트 매니저 흉내."""

    def __init__(self, body: bytes = b"[]", status: int = 200):
        self.status, self._body = status, body

    def read(self, n: int | None = None):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def make_urlopen(outcomes, calls: list):
    """호출마다 outcomes 를 순서대로 소비 — 예외면 raise, 아니면 응답."""
    seq = list(outcomes)

    def _fake(req, timeout=None):
        calls.append({"timeout": timeout})
        outcome = seq.pop(0) if seq else FakeResponse()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return _fake


def http_error(code: int) -> HTTPError:
    return HTTPError("https://x", code, "err", {}, io.BytesIO(b"{}"))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """백오프 대기는 건너뛴다(테스트 속도) — 재시도 횟수 검증에는 영향 없음."""
    monkeypatch.setattr(_http.time, "sleep", lambda s: None)


# ── ① 타임아웃 2회 후 성공 ────────────────────────────────────────
def test_retries_then_succeeds(monkeypatch):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [TimeoutError("read timed out"), TimeoutError("read timed out"),
         FakeResponse(b'{"ok":true}')], calls))
    result = _http.urlopen_with_retry(object(), label="t")
    assert json.loads(result.body) == {"ok": True}
    assert len(calls) == 3, "3번째 시도에서 성공해야 한다"


# ── ② 3회 실패 시 예외 전파 (삼키지 않음) ─────────────────────────
def test_exhausts_and_raises(monkeypatch):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [TimeoutError("t"), TimeoutError("t"), TimeoutError("t")], calls))
    with pytest.raises(TimeoutError):
        _http.urlopen_with_retry(object(), label="t")
    assert len(calls) == 3, "시도는 정확히 3회"


def test_socket_timeout_and_urlerror_are_retryable(monkeypatch):
    for exc in (socket.timeout("t"), URLError("conn refused")):
        calls: list = []
        monkeypatch.setattr(_http, "urlopen", make_urlopen(
            [exc, FakeResponse(b"[]")], calls))
        _http.urlopen_with_retry(object(), label="t")
        assert len(calls) == 2, f"{type(exc).__name__} 는 재시도 대상"


# ── ③ 4xx 는 재시도 0회 (즉시 시끄럽게 실패) ──────────────────────
@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_4xx_not_retried(monkeypatch, code):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [http_error(code), FakeResponse(b"[]")], calls))
    with pytest.raises(HTTPError) as ei:
        _http.urlopen_with_retry(object(), label="t")
    assert ei.value.code == code
    assert len(calls) == 1, "자격증명·요청 오류는 재시도하면 안 된다"


def test_4xx_body_not_consumed(monkeypatch):
    """호출부가 exc.read() 로 진단할 수 있어야 한다 (KOE001 메시지 경로)."""
    monkeypatch.setattr(_http, "urlopen", make_urlopen([http_error(406)], []))
    with pytest.raises(HTTPError) as ei:
        _http.urlopen_with_retry(object(), label="t")
    assert ei.value.read() == b"{}", "본문이 미리 소비되면 진단이 죽는다"


# ── ④ 5xx·429 는 재시도 발생 ──────────────────────────────────────
@pytest.mark.parametrize("code", [500, 502, 503, 429])
def test_5xx_and_429_retried(monkeypatch, code):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [http_error(code), FakeResponse(b"[]")], calls))
    _http.urlopen_with_retry(object(), label="t")
    assert len(calls) == 2, f"HTTP {code} 는 재시도 대상"


# ── ⑤ 발송 경로는 타임아웃이어도 1회만 호출 (중복 발송 금지) ──────
def test_send_kakao_single_attempt(monkeypatch):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen([TimeoutError("t")], calls))
    with pytest.raises(TimeoutError):
        kakao_notify.send_kakao("메시지", "fake-access-token")
    assert len(calls) == 1, "카카오 발송은 재시도하면 중복 발송이 된다"


def test_send_telegram_single_attempt(monkeypatch):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen([TimeoutError("t")], calls))
    with pytest.raises(TimeoutError):
        telegram_notify.send_telegram("메시지")
    assert len(calls) == 1, "텔레그램 발송은 재시도하면 중복 발송이 된다"


# ── 회귀: 07-23 실패 지점이 이제 살아남는지 ───────────────────────
def test_supabase_get_survives_single_timeout(monkeypatch):
    """07-23 #113 재현: 첫 조회가 읽기 타임아웃 → 예전엔 알림 전체 유실."""
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [TimeoutError("The read operation timed out"),
         FakeResponse('[{"id":1,"title":"업무"}]'.encode())], calls))
    rows = kakao_notify.supabase_get("tasks", "is_completed=eq.false")
    assert rows == [{"id": 1, "title": "업무"}]
    assert len(calls) == 2


def test_telegram_supabase_get_retries(monkeypatch):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [TimeoutError("t"), FakeResponse(b"[]")], calls))
    assert telegram_notify.supabase_get("tasks") == []
    assert len(calls) == 2


# ── 타임아웃·예산 계약 ────────────────────────────────────────────
def test_timeout_raised_to_20s(monkeypatch):
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen([FakeResponse(b"[]")], calls))
    _http.urlopen_with_retry(object(), label="t")
    assert calls[0]["timeout"] == 20.0, "타임아웃 15→20초"


def test_worst_case_within_one_minute():
    """시도별 타임아웃 × 횟수 + 백오프가 60초를 넘지 않아야 한다."""
    worst = _http.DEFAULT_TIMEOUT * _http.DEFAULT_ATTEMPTS + sum(_http.BACKOFF)
    assert worst > _http.TOTAL_BUDGET, "예산 clamp 가 없으면 63초 — 이 전제가 깨지면 테스트 갱신"
    assert _http.TOTAL_BUDGET <= 60.0, "최악 총소요 1분 이내"


def test_budget_clamps_timeout(monkeypatch):
    """남은 예산이 적으면 시도별 타임아웃이 그만큼 줄어든다."""
    calls: list = []
    monkeypatch.setattr(_http, "urlopen", make_urlopen([FakeResponse(b"[]")], calls))
    _http.urlopen_with_retry(object(), label="t", budget=5.0)
    assert calls[0]["timeout"] <= 5.0


# ── 재시도 로그(조용한 재시도 금지) ───────────────────────────────
def test_retry_logs_to_stderr(monkeypatch, capsys):
    monkeypatch.setattr(_http, "urlopen", make_urlopen(
        [TimeoutError("t"), FakeResponse(b"[]")], []))
    _http.urlopen_with_retry(object(), label="supabase_get(tasks)")
    err = capsys.readouterr().err
    assert "supabase_get(tasks)" in err and "재시도" in err


# ── ⑥ jobs/ 전 모듈 stdlib-only ───────────────────────────────────
def test_jobs_are_stdlib_only():
    import ast

    allowed_local = {"_http"}
    for path in sorted(JOBS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            for name in names:
                if name in allowed_local or name == "__future__":
                    continue
                assert name in sys.stdlib_module_names, \
                    f"{path.name}: 비표준 import '{name}' — jobs/ 는 stdlib-only"
