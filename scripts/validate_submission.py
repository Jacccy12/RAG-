#!/usr/bin/env python3
"""Validate submission CSV against question_public.csv."""
from __future__ import annotations

import ast
import csv
import json
import re
import sys
from pathlib import Path


def load_question_ids(path: Path) -> set[int]:
    ids = set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ids.add(int(row["id"]))
    return ids


def parse_ret(ret: str) -> tuple[str | None, list[str] | None, str | None]:
    """Return (text, images, error). Plain text if no trailing list."""
    ret = (ret or "").strip()
    if not ret:
        return None, None, "empty"
    # Pattern: "text", ["id1", "id2"]
    m = re.match(r'^("(?:[^"\\]|\\.)*")\s*,\s*(\[[^\]]*\])\s*$', ret, re.S)
    if m:
        try:
            text = json.loads(m.group(1))
            images = ast.literal_eval(m.group(2))
            if not isinstance(images, list):
                return text, None, "image part not list"
            return text, images, None
        except (json.JSONDecodeError, SyntaxError, ValueError) as e:
            return None, None, f"parse error: {e}"
    # Plain string only
    if ret.startswith('"') and ret.endswith('"'):
        try:
            return json.loads(ret), [], None
        except json.JSONDecodeError as e:
            return None, None, f"json error: {e}"
    return ret, [], None


def validate(path: Path, question_ids: set[int], valid_image_ids: set[str] | None) -> None:
    rows: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append((int(row["id"]), row.get("ret", "")))

    sub_ids = {i for i, _ in rows}
    print(f"\n=== {path.name} ===")
    print(f"rows: {len(rows)}, questions: {len(question_ids)}")
    print(f"missing: {sorted(question_ids - sub_ids)}")
    print(f"extra: {sorted(sub_ids - question_ids)}")

    issues = {
        "empty": [],
        "references": [],
        "debug_paths": [],
        "parse_error": [],
        "pic_mismatch": [],
        "invalid_image": [],
        "short_cn": [],
        "short_en": [],
        "no_pic_ops": [],
    }

    for qid, ret in rows:
        if "### References" in ret or "### Reference" in ret:
            issues["references"].append(qid)
        if "RAG-Anything" in ret or "data/txt" in ret or "data\\txt" in ret:
            issues["debug_paths"].append(qid)

        text, images, err = parse_ret(ret)
        if err == "empty":
            issues["empty"].append(qid)
            continue
        if err:
            issues["parse_error"].append((qid, err))
            continue

        assert text is not None
        if images is None:
            continue

        pic_n = text.count("<PIC>")
        if images and pic_n == 0:
            issues["pic_mismatch"].append(qid)
        if pic_n > 0 and not images:
            issues["pic_mismatch"].append(qid)
        if pic_n > 0 and pic_n != len(images):
            issues["pic_mismatch"].append(qid)

        if valid_image_ids:
            for img in images:
                if img not in valid_image_ids:
                    issues["invalid_image"].append((qid, img))

        t = text.strip()
        if len(t) < 30 and re.search(r"[\u4e00-\u9fff]", t):
            issues["short_cn"].append(qid)
        elif len(t) < 40 and not re.search(r"[\u4e00-\u9fff]", t):
            issues["short_en"].append(qid)

    for k, v in issues.items():
        if v:
            sample = v[:8]
            more = f" (+{len(v)-8} more)" if len(v) > 8 else ""
            print(f"{k}: {len(v)} {sample}{more}")

    with_images = sum(1 for _, r in rows if parse_ret(r)[1] and parse_ret(r)[1])
    print(f"with image list: {with_images}")


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    q_path = repo / "data" / "question_public.csv"
    data_dir = repo / "data"
    image_ids = {
        p.stem
        for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    }
    q_ids = load_question_ids(q_path)
    for name in sys.argv[1:] or ["submission0.27.csv", "submission0.27.optimized.csv"]:
        p = repo / "data" / name
        if p.is_file():
            validate(p, q_ids, image_ids)


if __name__ == "__main__":
    main()
