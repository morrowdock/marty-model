# SPDX-License-Identifier: Apache-2.0
"""A tiny stand-in for `marty-solid check` used by the unit tests.

It knows only the built-in component ids and the closed-form ratios the generator
uses. It is NOT an engine: real checks come from the integration test.

Usage: python3 fake_engine.py [--mode=ok|wrong|garbage|exit] check FILE.json
"""

import json
import sys


def report(doc):
    part = doc["parts"][0]
    iid, comp, w = part["id"], part["use"], part.get("with", {})
    if comp == "spurPair":
        return {f"{iid}.pinion": 1, f"{iid}.wheel": -w["pinionTeeth"] / w["wheelTeeth"]}, None
    if comp == "planetaryStage":
        s, p, n = w["sunTeeth"], w["planetTeeth"], w["planets"]
        if (2 * s + 2 * p) % n:
            return None, "component.check.spacing"
        return {f"{iid}.sun": 1, f"{iid}.carrier": s / (2 * s + 2 * p)}, None
    if comp == "sliderCrank":
        return {f"{iid}.crank": 1}, None
    if comp == "propeller":
        return {f"{iid}.hub": 1}, None
    return None, f"component.unknown.{comp}"


def main(argv):
    mode = "ok"
    if argv and argv[0].startswith("--mode="):
        mode = argv.pop(0).split("=", 1)[1]
    if mode == "garbage":
        print("not json")
        return 0
    assert argv[0] == "check", argv
    with open(argv[1], encoding="utf-8") as f:
        doc = json.load(f)
    ratios, reason = report(doc)
    if mode == "wrong" and ratios:
        ratios = {k: v * 1.01 for k, v in ratios.items()}
    ok = reason is None
    print(json.dumps({"ok": ok, "reason": reason, "part": None if ok else doc["parts"][0]["id"],
                      "ratios": ratios, "parts": 2, "triangles": 100}))
    if mode == "exit":
        return 0 if not ok else 1  # exit status disagrees with the report
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
