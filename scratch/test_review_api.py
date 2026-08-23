"""Smoke test for POST /api/review — runs against a live server on :8000.

Backs up products.json (frontend + internal) before mutating and restores
them afterwards, so the real snapshot is left untouched.
"""

import json
import os
import shutil
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT_JSON = os.path.join(ROOT, "frontend", "data", "products.json")
INTERNAL_JSON = os.path.join(ROOT, "data", "processed", "products.json")
BASE = "http://127.0.0.1:8000"

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def post(payload):
    req = urllib.request.Request(
        BASE + "/api/review",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def product_key(p):
    for f in ("row_id", "mfg_part_num", "part_desc"):
        if p.get(f) is not None:
            return str(p[f])
    return "row"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    backups = [(FRONT_JSON, FRONT_JSON + ".bak"), (INTERNAL_JSON, INTERNAL_JSON + ".bak")]
    for src, bak in backups:
        if os.path.exists(src):
            shutil.copy(src, bak)

    try:
        products = load(FRONT_JSON)
        target = next(p for p in products if (p.get("descriptions") or {}))
        key = product_key(target)
        desc_key = next(iter(target["descriptions"]))
        original_value = target["descriptions"][desc_key]

        print(f"target product key: {key!r}")

        # 1. accept
        status, body = post({"key": key, "decision": "accept"})
        check("accept -> 200 ok", status == 200 and body.get("ok"), body)
        fresh = next(p for p in load(FRONT_JSON) if product_key(p) == key)
        check("accept persisted in frontend/data/products.json",
              fresh.get("review", {}).get("decision") == "accept")
        internal = next(p for p in load(INTERNAL_JSON) if product_key(p) == key)
        check("accept persisted in internal products.json",
              internal.get("review", {}).get("decision") == "accept")

        # 2. edit with corrected description value
        edited_descs = dict(target["descriptions"])
        edited_descs[desc_key] = "SMOKE-TEST-EDITED"
        status, body = post({"key": key, "decision": "edit",
                             "product": {"attributes": target.get("attributes", []),
                                         "descriptions": edited_descs,
                                         "classpath": "HACK>SHOULD>BE>IGNORED"}})
        check("edit -> 200 ok", status == 200 and body.get("ok"), body)
        fresh = next(p for p in load(FRONT_JSON) if product_key(p) == key)
        check("edited description persisted",
              fresh["descriptions"][desc_key] == "SMOKE-TEST-EDITED")
        check("non-whitelisted field NOT merged",
              fresh.get("classpath") == target.get("classpath"))
        check("edit decision recorded", fresh.get("review", {}).get("decision") == "edit")

        # 3. validation
        status, body = post({"key": key, "decision": "maybe"})
        check("invalid decision -> 400", status == 400, body)
        status, body = post({"decision": "accept"})
        check("missing key -> 400", status == 400, body)
        status, body = post({"key": "does-not-exist-xyz", "decision": "accept"})
        check("unknown key -> 404", status == 404, body)

        # 4. value was really changed vs original
        check("original value differed", original_value != "SMOKE-TEST-EDITED")
    finally:
        for src, bak in backups:
            if os.path.exists(bak):
                shutil.move(bak, src)
        print("backups restored")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
