"""골든 픽스처 생성기 [Phase 1-A §5-3].

원본 app.py 에서 분류/계산 순수 함수들을 AST 로 추출해 '고정 시각'으로 실행하고,
(입력 → 기대 출력)을 tests/golden_classification.json 으로 캡처한다.

이 픽스처는 core/models.py 추출 '이전'의 동작 스냅샷이다. 추출 후 동일 입력이
동일 출력을 내는지 tests/smoke_test.py 의 골든 테스트가 검증한다.

사용법: python tests/generate_golden.py <소스파일(기본 app.py)>
※ 기준선(main) 시점에 1회 실행해 커밋한다. 이후 재생성하지 말 것(스냅샷 오염 방지).
"""
from __future__ import annotations

import ast
import calendar
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
FROZEN_NOW = datetime(2025, 3, 12, 10, 0, 0, tzinfo=KST)  # 수요일 10:00 KST

TARGET_FUNCS = [
    "parse_deadline_kst", "get_urgency", "calc_duration", "calc_duration_minutes",
    "format_minutes", "calc_checklist_progress", "parse_tags",
    "get_next_recurrence_date", "build_task_date_map",
    "build_weekly_report", "build_monthly_report",
]


def extract_functions(source_path: Path) -> dict:
    """소스에서 대상 함수 정의만 추출해 고정 시각 환경에서 exec, 함수 dict 반환."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    segments = []
    src = source_path.read_text(encoding="utf-8")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in TARGET_FUNCS:
            segments.append(ast.get_source_segment(src, node))
    ns = {
        "datetime": datetime, "timedelta": timedelta, "timezone": timezone,
        "calendar": calendar, "re": re, "Counter": Counter, "defaultdict": defaultdict,
        "KST": KST, "Optional": type(None),
        "now_kst": lambda: FROZEN_NOW,  # 시각 고정(원본은 실제 현재 시각 사용)
    }
    exec(compile("from typing import Optional\n" + "\n\n".join(segments), str(source_path), "exec"), ns)
    return ns


def iso(dt: datetime) -> str:
    return dt.isoformat()


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "app.py"
    fns = extract_functions(source)
    N = FROZEN_NOW

    urgency_inputs = [
        None, "", "not-a-date",
        iso(N - timedelta(hours=2)),            # 2시간 초과
        iso(N - timedelta(hours=72)),           # 3일 초과
        iso(N + timedelta(hours=5)),            # 오늘, 5시간 남음
        iso(N + timedelta(minutes=30)),         # 오늘, 30분 남음
        "2025-03-12T01:00:00Z",                 # UTC 표기 → KST 10:00 = now
        iso(N + timedelta(days=1)),             # 내일
        iso(N + timedelta(days=3)),             # 3일 후
        iso(N + timedelta(days=10)),            # 10일 후
    ]

    checklist_inputs = [
        None, "", "메모만 있음",
        "- [ ] a\n- [x] b\n- [X] c",
        "서문\n- [ ] one\n  - [ ] 들여쓴 항목\n- [x] two",
    ]

    tags_inputs = [None, "", "#급함 #보고용", "a, b,,c", "#a,b  c"]

    recurrence_inputs = [
        (iso(datetime(2025, 1, 31, 18, 0, tzinfo=KST)), "monthly"),   # 월말 → 2/28
        (iso(datetime(2025, 12, 15, 9, 0, tzinfo=KST)), "monthly"),   # 연말 롤오버
        (iso(datetime(2025, 3, 12, 18, 0, tzinfo=KST)), "daily"),
        (iso(datetime(2025, 3, 12, 18, 0, tzinfo=KST)), "weekly"),
        (iso(datetime(2025, 3, 12, 18, 0, tzinfo=KST)), "biweekly"),
        (iso(datetime(2025, 3, 12, 18, 0, tzinfo=KST)), "unknown"),
    ]

    minutes_inputs = [0.2, 1, 59.9, 75, 1500, 2880]

    duration_inputs = [
        (None, None),
        (iso(N - timedelta(days=1, hours=2, minutes=5)), iso(N)),
        (iso(N), iso(N)),
        ("bad", iso(N)),
    ]

    sample_tasks = [
        {"id": 1, "title": "기한초과", "deadline": iso(N - timedelta(days=1)), "is_completed": False,
         "category": "공정거래", "priority": "높음",
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None},
        {"id": 2, "title": "오늘", "deadline": iso(N + timedelta(hours=4)), "is_completed": False,
         "category": "동반성장", "priority": "중간",
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None},
        {"id": 3, "title": "사흘내", "deadline": iso(N + timedelta(days=2)), "is_completed": False,
         "category": "환경", "priority": "낮음",
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None},
        {"id": 4, "title": "무기한", "deadline": None, "is_completed": False,
         "category": "기타", "priority": "중간",
         "completed_at": None, "timer_started_at": None, "timer_ended_at": None},
        {"id": 5, "title": "완료-이번주", "deadline": iso(N - timedelta(days=1)), "is_completed": True,
         "category": "사회공헌", "priority": "중간",
         "completed_at": iso(N - timedelta(days=1, hours=3)),
         "timer_started_at": iso(N - timedelta(days=1, hours=5)),
         "timer_ended_at": iso(N - timedelta(days=1, hours=3))},
        {"id": 6, "title": "완료-지난달", "deadline": None, "is_completed": True,
         "category": "공정거래", "priority": "높음",
         "completed_at": iso(N - timedelta(days=40)),
         "timer_started_at": None, "timer_ended_at": None},
    ]
    completed = [t for t in sample_tasks if t["is_completed"]]

    golden = {
        "frozen_now": iso(N),
        "get_urgency": [
            {"input": d, "output": list(fns["get_urgency"](d))} for d in urgency_inputs
        ],
        "calc_checklist_progress": [
            {"input": d, "output": (list(r) if (r := fns["calc_checklist_progress"](d)) else None)}
            for d in checklist_inputs
        ],
        "parse_tags": [
            {"input": d, "output": fns["parse_tags"](d)} for d in tags_inputs
        ],
        "get_next_recurrence_date": [
            {"input": [d, r], "output": iso(fns["get_next_recurrence_date"](datetime.fromisoformat(d), r))}
            for d, r in recurrence_inputs
        ],
        "format_minutes": [
            {"input": m, "output": fns["format_minutes"](m)} for m in minutes_inputs
        ],
        "calc_duration": [
            {"input": list(p), "output": fns["calc_duration"](*p)} for p in duration_inputs
        ],
        "calc_duration_minutes": [
            {"input": list(p), "output": fns["calc_duration_minutes"](*p)} for p in duration_inputs
        ],
        "build_task_date_map": {
            "input": sample_tasks,
            "output": {k: [t["id"] for t in v] for k, v in fns["build_task_date_map"](sample_tasks).items()},
        },
        "build_weekly_report": {
            "input": {"completed": completed},
            "output": fns["build_weekly_report"](completed, sample_tasks),
        },
        "build_monthly_report": {
            "input": {"completed": completed},
            "output": fns["build_monthly_report"](completed, sample_tasks),
        },
        "sample_tasks": sample_tasks,
    }

    out = ROOT / "tests" / "golden_classification.json"
    out.write_text(json.dumps(golden, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(v) for v in golden.values() if isinstance(v, list))
    print(f"golden_classification.json 생성: 케이스 {total}건 + 리포트/맵 3건 (source={source.name})")


if __name__ == "__main__":
    main()
