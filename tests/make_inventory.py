"""AST 기반 함수 인벤토리 추출 도구 [Phase 1-A 순수 이동 증명용].

사용법:
    python tests/make_inventory.py before   # app.py 단일 파일 → tests/inventory_before.json
    python tests/make_inventory.py after    # app.py + core/ + ui/ → tests/inventory_after.json

각 함수의 (이름, 인자 시그니처)를 기록한다. 이동 전/후 인벤토리를 대조해
"순수 이동"(함수 소실·시그니처 변경 없음)을 증명하는 기준선이다.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def signature_of(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    a = fn.args
    parts: list[str] = []
    pos_defaults = [None] * (len(a.posonlyargs) + len(a.args) - len(a.defaults)) + list(a.defaults)
    all_pos = list(a.posonlyargs) + list(a.args)
    for arg, default in zip(all_pos, pos_defaults):
        parts.append(arg.arg + ("=…" if default is not None else ""))
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(arg.arg + ("=…" if default is not None else ""))
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return f"({', '.join(parts)})"


def inventory_file(path: Path) -> list[dict]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 데코레이터로 감싸진 내부 wrapper(예: safe_db_call의 wrapper)는 제외
            if node.name == "wrapper":
                continue
            out.append({
                "name": node.name,
                "signature": signature_of(node),
                "file": str(path.relative_to(ROOT)),
            })
    return sorted(out, key=lambda d: (d["file"], d["name"]))


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "before"
    if mode == "before":
        files = [ROOT / "app.py"]
        out_path = ROOT / "tests" / "inventory_before.json"
    else:
        files = [ROOT / "app.py"]
        for pkg in ("core", "ui"):
            files.extend(sorted((ROOT / pkg).glob("*.py")))
        out_path = ROOT / "tests" / "inventory_after.json"
    inv = []
    for f in files:
        inv.extend(inventory_file(f))
    out_path.write_text(json.dumps(inv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{out_path.name}: {len(inv)} functions from {len(files)} files")


if __name__ == "__main__":
    main()
