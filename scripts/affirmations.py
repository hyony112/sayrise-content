#!/usr/bin/env python3
"""확언 목록 CSV(스프레드시트에서 내보낸 것)를 검사하고 앱용 JSON으로 바꾼다.

규칙은 앱의 AffirmationValidator.swift와 같다. 둘 중 하나를 바꾸면 다른 쪽도 바꾼다.

사용법:
  python3 content/scripts/affirmations.py build content/affirmations.csv --out SayRise/affirmations.json
  python3 scripts/affirmations.py build sheet.csv --out docs/affirmations.json --previous docs/affirmations.json   (sayrise-content 저장소의 배포 워크플로)
  python3 content/scripts/affirmations.py check SayRise/affirmations.json

build는 오류가 하나라도 있으면 아무것도 쓰지 않고 종료 코드 1로 끝난다.
--previous를 주면 내용이 바뀌었을 때만 version을 1 올린다(바뀌지 않으면 파일을 그대로 둔다).
"""
import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime, timezone

MIN_WORDS, MAX_WORDS = 6, 12
MAX_ONE_SYLLABLE_WORDS = 2
MIN_ACTIVE = 10
ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TEXT_PATTERN = re.compile(r"^[가-힣]+( [가-힣]+)*$")

# 시트의 머리글은 한국어나 영어 어느 쪽이어도 된다.
HEADERS = {
    "id": "id", "아이디": "id",
    "category": "category", "카테고리": "category",
    "text": "text", "확언": "text",
    "active": "active", "사용": "active",
}
TRUE_VALUES = {"y", "yes", "true", "1", "o", "사용", "예"}
FALSE_VALUES = {"n", "no", "false", "0", "x", "미사용", "아니오", ""}


def text_problems(text):
    """확언 문장 하나의 규칙 위반 목록 (기획서 5장 작성 규칙)."""
    problems = []
    if not TEXT_PATTERN.match(text):
        problems.append("한글과 띄어쓰기 한 칸만 쓸 수 있어요 (숫자·영어·문장부호·연속 공백 불가)")
        return problems
    words = text.split(" ")
    if not MIN_WORDS <= len(words) <= MAX_WORDS:
        problems.append(f"{MIN_WORDS}~{MAX_WORDS}어절이어야 해요 (지금 {len(words)}어절)")
    one = sum(1 for w in words if len(w) == 1)
    if one > MAX_ONE_SYLLABLE_WORDS:
        problems.append(f"한 글자 어절은 {MAX_ONE_SYLLABLE_WORDS}개까지예요 (지금 {one}개)")
    return problems


def read_rows(path):
    raw = open(path, encoding="utf-8-sig").read()
    reader = csv.reader(io.StringIO(raw))
    header = next(reader, None)
    if not header:
        raise SystemExit("빈 CSV예요.")
    columns = [HEADERS.get(h.strip().lower(), HEADERS.get(h.strip())) for h in header]
    missing = {"id", "category", "text", "active"} - set(columns)
    if missing:
        raise SystemExit(f"머리글에 {', '.join(sorted(missing))} 열이 없어요. (id, 카테고리, 확언, 사용)")
    rows = []
    for line_no, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        row = {col: (values[i].strip() if i < len(values) else "") for i, col in enumerate(columns) if col}
        row["_line"] = line_no
        rows.append(row)
    return rows


def validate(entries, where):
    """entries: [{id, category, text, active, _where}] → 오류 목록."""
    errors = []
    seen_ids, seen_texts = {}, {}
    for e in entries:
        loc = e["_where"]
        if not ID_PATTERN.match(e["id"]):
            errors.append(f"{loc}: id '{e['id']}'는 소문자·숫자·하이픈만 쓸 수 있어요")
        if e["id"] in seen_ids:
            errors.append(f"{loc}: id '{e['id']}'가 {seen_ids[e['id']]}와 겹쳐요")
        seen_ids.setdefault(e["id"], loc)
        if not e["category"]:
            errors.append(f"{loc}: 카테고리가 비어 있어요")
        for p in text_problems(e["text"]):
            errors.append(f"{loc}: {p} — “{e['text']}”")
        if e["active"]:
            if e["text"] in seen_texts:
                errors.append(f"{loc}: 같은 확언이 {seen_texts[e['text']]}에도 있어요")
            seen_texts.setdefault(e["text"], loc)
    active = sum(1 for e in entries if e["active"])
    if active < MIN_ACTIVE:
        errors.append(f"{where}: 사용 중인 확언이 {MIN_ACTIVE}개 이상이어야 해요 (지금 {active}개)")
    return errors


def entries_from_csv(path):
    entries, errors = [], []
    for row in read_rows(path):
        flag = row["active"].strip().lower()
        if flag in TRUE_VALUES:
            active = True
        elif flag in FALSE_VALUES:
            active = False
        else:
            errors.append(f"{row['_line']}행: 사용 값 '{row['active']}'를 알 수 없어요 (Y 또는 N)")
            active = False
        entries.append({
            "id": row["id"], "category": row["category"], "text": " ".join(row["text"].split()),
            "active": active, "_where": f"{row['_line']}행",
        })
    return entries, errors


def public(entries):
    return [{k: e[k] for k in ("id", "category", "text", "active")} for e in entries]


def cmd_build(args):
    entries, errors = entries_from_csv(args.csv)
    errors += validate(entries, args.csv)
    if args.previous:
        try:
            prev = json.load(open(args.previous, encoding="utf-8"))
            prev_ids = {a["id"]: a for a in prev.get("affirmations", [])}
            for e in entries:
                p = prev_ids.get(e["id"])
                if p and p["text"] != e["text"]:
                    print(f"참고: {e['_where']} '{e['id']}' 문장이 바뀌었어요. 기록에는 새 문장이 보여요.")
            for pid in prev_ids.keys() - {e["id"] for e in entries}:
                errors.append(f"id '{pid}'가 사라졌어요. 지우지 말고 사용을 N으로 바꿔 주세요 (기록이 이 id를 써요)")
        except FileNotFoundError:
            prev = None
    else:
        prev = None
    if errors:
        print(f"검사 실패 {len(errors)}건 — 아무것도 바꾸지 않았어요.", file=sys.stderr)
        for e in errors:
            print("  • " + e, file=sys.stderr)
        return 1

    items = public(entries)
    version = 1
    if prev is not None:
        if prev.get("affirmations") == items:
            print(f"바뀐 내용이 없어요 (version {prev.get('version')}).")
            return 0
        version = int(prev.get("version", 0)) + 1
    elif args.version:
        version = args.version
    doc = {
        "version": version,
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "affirmations": items,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    active = sum(1 for e in entries if e["active"])
    print(f"✓ {args.out}: version {version}, 확언 {len(items)}개 (사용 {active}개)")
    return 0


def cmd_check(args):
    doc = json.load(open(args.json, encoding="utf-8"))
    entries = [dict(a, _where=f"{i + 1}번째") for i, a in enumerate(doc.get("affirmations", []))]
    errors = validate(entries, args.json)
    if not isinstance(doc.get("version"), int):
        errors.append("version이 정수가 아니에요")
    for e in errors:
        print("  • " + e, file=sys.stderr)
    print("✓ 통과" if not errors else f"검사 실패 {len(errors)}건")
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("csv")
    b.add_argument("--out", required=True)
    b.add_argument("--previous")
    b.add_argument("--version", type=int)
    c = sub.add_parser("check")
    c.add_argument("json")
    args = parser.parse_args()
    return cmd_build(args) if args.cmd == "build" else cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
