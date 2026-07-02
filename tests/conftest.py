"""Phase 1-A 테스트 공용 픽스처.

핵심: supabase.create_client 를 세션 시작 시점에 가짜 클라이언트로 치환한다.
app.py(및 이후 core/db.py)는 실행 시 `from supabase import create_client` 를
바인딩하므로, 패키지 속성을 먼저 갈아끼우면 실제 네트워크 없이 전 시나리오를
구동할 수 있다. 실제 시크릿은 어디에도 사용하지 않는다(§1-5).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

KST = timezone(timedelta(hours=9))

DUMMY_SECRETS = {
    "SUPABASE_URL": "https://fake.supabase.co",
    "SUPABASE_KEY": "fake-anon-key",
    "APP_PASSWORD": "pw-test",
}


class _FakeQuery:
    """supabase-py 쿼리 빌더 체인 흉내: table().select/insert/update/delete + eq/gte/order/limit."""

    def __init__(self, client: "FakeSupabase", table: str):
        self._c = client
        self._table = table
        self._op = None
        self._payload = None
        self._filters: list[tuple[str, str, object]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._count = None

    def select(self, *_cols, count=None):
        self._op = "select"
        self._count = count
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _match(self, row) -> bool:
        for op, col, val in self._filters:
            cell = row.get(col)
            if op == "eq" and cell != val:
                return False
            if op == "gte" and (cell is None or cell < val):
                return False
        return True

    def execute(self):
        rows = self._c.tables.setdefault(self._table, [])
        self._c.calls.append({
            "table": self._table, "op": self._op,
            "payload": self._payload, "filters": list(self._filters),
        })
        if self._op == "insert":
            payload = dict(self._payload)
            payload.setdefault("id", self._c._next_id())
            payload.setdefault("created_at", datetime.now(KST).isoformat())
            rows.append(payload)
            return SimpleNamespace(data=[payload], count=None)
        if self._op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self._payload)
            return SimpleNamespace(data=hit, count=None)
        if self._op == "delete":
            hit = [r for r in rows if self._match(r)]
            self._c.tables[self._table] = [r for r in rows if not self._match(r)]
            return SimpleNamespace(data=hit, count=None)
        # select
        hit = [dict(r) for r in rows if self._match(r)]
        if self._order:
            col, desc = self._order
            hit.sort(key=lambda r: (r.get(col) is None, r.get(col) or ""), reverse=desc)
        if self._limit is not None:
            hit = hit[: self._limit]
        count = len(hit) if self._count else None
        return SimpleNamespace(data=hit, count=count)


class FakeSupabase:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {"tasks": [], "memos": []}
        self.calls: list[dict] = []
        self._id = 1000

    def _next_id(self):
        self._id += 1
        return self._id

    def table(self, name):
        return _FakeQuery(self, name)

    def reset(self):
        self.tables = {"tasks": [], "memos": []}
        self.calls = []
        self._id = 1000

    def calls_of(self, table, op):
        return [c for c in self.calls if c["table"] == table and c["op"] == op]


FAKE = FakeSupabase()

# 세션 전체에서 supabase.create_client 를 가짜로 치환 (모든 import 전에 실행됨)
import supabase as _supabase_pkg  # noqa: E402

_supabase_pkg.create_client = lambda *_a, **_k: FAKE

# 이후 core/db.py 가 이미 import 된 상태로 재사용될 때를 대비한 방어 패치
try:  # pragma: no cover
    import core.db as _core_db

    _core_db.create_client = lambda *_a, **_k: FAKE
except ImportError:
    pass


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def seed_default(fake: FakeSupabase) -> dict:
    """스모크 시나리오용 기본 데이터. 마감은 '실제 현재 시각' 기준 상대값."""
    now = datetime.now(KST)
    tasks = [
        {"id": 1, "title": "기한초과 업무", "description": "- [ ] a\n- [x] b",
         "deadline": _iso(now - timedelta(days=1)), "category": "공정거래", "priority": "높음",
         "recurrence": None, "tags": "급함", "is_completed": False,
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None,
         "created_at": _iso(now - timedelta(days=3))},
        {"id": 2, "title": "오늘 마감 업무", "description": "",
         "deadline": _iso(now + timedelta(hours=3)), "category": "동반성장", "priority": "중간",
         "recurrence": None, "tags": "", "is_completed": False,
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None,
         "created_at": _iso(now - timedelta(days=2))},
        {"id": 3, "title": "사흘내 업무", "description": "",
         "deadline": _iso(now + timedelta(days=2)), "category": "환경", "priority": "낮음",
         "recurrence": None, "tags": "보고용", "is_completed": False,
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None,
         "created_at": _iso(now - timedelta(days=1))},
        {"id": 4, "title": "무기한 업무", "description": "",
         "deadline": None, "category": "기타", "priority": "중간",
         "recurrence": None, "tags": "", "is_completed": False,
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None,
         "created_at": _iso(now - timedelta(days=1))},
        {"id": 5, "title": "오늘 완료한 업무", "description": "",
         "deadline": _iso(now - timedelta(hours=2)), "category": "사회공헌", "priority": "중간",
         "recurrence": None, "tags": "", "is_completed": True,
         "completed_at": _iso(now - timedelta(hours=1)),
         "timer_started_at": _iso(now - timedelta(hours=2)),
         "timer_ended_at": _iso(now - timedelta(hours=1)),
         "created_at": _iso(now - timedelta(days=2))},
    ]
    memos = [
        {"id": 11, "content": "고정된 메모", "pinned": True, "created_at": _iso(now - timedelta(hours=5))},
        {"id": 12, "content": "일반 메모", "pinned": False, "created_at": _iso(now - timedelta(hours=4))},
    ]
    fake.tables["tasks"] = [dict(t) for t in tasks]
    fake.tables["memos"] = [dict(m) for m in memos]
    return {"tasks": tasks, "memos": memos}


@pytest.fixture()
def fake_db():
    FAKE.reset()
    seed = seed_default(FAKE)
    yield FAKE, seed
    FAKE.reset()
