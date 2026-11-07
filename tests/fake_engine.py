# SPDX-License-Identifier: Apache-2.0
"""A tiny stand-in for `marty-solid check` used by the unit tests.

It knows only the built-in component ids and the closed-form ratios the generator
uses. It is NOT an engine: real checks come from the integration test.

Usage: python3 fake_engine.py [--mode=ok|wrong|garbage|exit|sleep|accept|badid|nosha|noid] check FILE.json [--strict]
       python3 fake_engine.py components
"""

import hashlib
import json
import sys
import time


# A small copy of the real catalog (MartyGraphics 76104dea) for the four components.
CATALOG = {"format": "martygraphics.solid.components/1", "components": [
    {"id": "spurPair", "parts": ["pinion", "wheel"], "anchors": {"input": "pinion", "output": "wheel"},
     "params": {"pinionTeeth": {"default": 12, "min": 12, "max": 100, "integer": True},
                "wheelTeeth": {"default": 36, "min": 12, "max": 200, "integer": True},
                "module": {"default": 2, "min": 0.5, "max": 10}, "width": {"default": 10, "min": 2, "max": 100}}},
    {"id": "planetaryStage", "parts": ["sun", "ring", "carrier", "planet"],
     "anchors": {"input": "sun", "output": "carrier"},
     "params": {"sunTeeth": {"default": 24, "min": 12, "max": 80, "integer": True},
                "planetTeeth": {"default": 18, "min": 12, "max": 60, "integer": True},
                "planets": {"default": 3, "min": 2, "max": 6, "integer": True},
                "module": {"default": 2, "min": 0.5, "max": 10}, "width": {"default": 12, "min": 2, "max": 100}}},
    {"id": "sliderCrank", "parts": ["frame", "crank", "piston", "rod"],
     "anchors": {"input": "crank", "output": "piston"},
     "params": {"radius": {"default": 18, "min": 8, "max": 100}, "rod": {"default": 62, "min": 30, "max": 400},
                "piston": {"default": 14, "min": 5, "max": 60}}},
    {"id": "propeller", "parts": ["hub", "blade"], "anchors": {"input": "hub"},
     "params": {"blades": {"default": 3, "min": 2, "max": 8, "integer": True},
                "span": {"default": 110, "min": 20, "max": 1000}, "chord": {"default": 34, "min": 5, "max": 400},
                "pitch": {"default": -40, "min": -80, "max": 80}, "twist": {"default": 28, "min": -60, "max": 60},
                "hub": {"default": 12, "min": 4, "max": 200}}},
]}
BY_ID = {c["id"]: c for c in CATALOG["components"]}
USE_KEYS = {"id", "use", "with", "at", "rot", "parent", "set"}


def validate(doc):
    """The few format rules the repair mutations touch: (reason, part) or (None, None)."""
    if len(doc.get("title", "")) > 80:
        return "assembly.title", None
    for step in doc.get("steps", []):
        if len(step.get("say", "")) > 240:
            return "step.say", None
    part = doc["parts"][0]
    iid = part["id"]
    entry = BY_ID.get(part.get("use"))
    if entry is None:
        return f"component.unknown.{part.get('use')}", iid
    for key in sorted(part):
        if key not in USE_KEYS:
            return f"component.use.unknown.{key}", iid
    for name, value in sorted(part.get("with", {}).items()):
        spec = entry["params"].get(name)
        if spec is None:
            return f"component.param.unknown.{name}", iid
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"component.param.value.{name}", iid
        if not spec["min"] <= value <= spec["max"]:
            return f"component.param.range.{name}", iid
        if spec.get("integer") and value != int(value):
            return f"component.param.integer.{name}", iid
    names = {iid} | {f"{iid}.{p}" for p in entry["parts"]} | {f"{iid}.{a}" for a in entry["anchors"]}
    for step in doc.get("steps", []):
        for ref in step.get("highlight", []):
            if ref not in names:
                return f"ref.unknown.{ref}", None
    return None, None


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
    mode, exe = "ok", __file__
    while argv and argv[0].startswith("--"):
        flag = argv.pop(0)
        if flag.startswith("--mode="):
            mode = flag.split("=", 1)[1]
        elif flag.startswith("--exe="):  # a wrapper script that runs this file: report ITS hash
            exe = flag.split("=", 1)[1]
    if mode == "garbage":
        print("not json")
        return 0
    if mode == "sleep":
        time.sleep(5)
    if argv == ["components"]:
        print(json.dumps(CATALOG))
        return 0
    assert argv[0] == "check" and argv[2:] in ([], ["--strict"]), argv
    with open(argv[1], encoding="utf-8") as f:
        doc = json.load(f)
    reason, part = validate(doc)
    ratios = None
    if reason is None:
        ratios, reason = report(doc)
        part = None if reason is None else doc["parts"][0]["id"]
    if mode == "wrong" and ratios:
        ratios = {k: v * 1.01 for k, v in ratios.items()}
    if mode == "accept":  # an engine that accepts everything (to test mutation checks)
        reason, part, ratios = None, None, ratios or {}
    ok = reason is None
    with open(exe, "rb") as me:
        own = hashlib.sha256(me.read()).hexdigest()
    identity = {"name": "MartyGraphics", "version": "fake", "reportFormat": 1,
                "executableSHA256": "0" * 64 if mode == "badid" else own}
    if mode == "nosha":
        del identity["executableSHA256"]
    result = {"ok": ok, "reason": reason, "part": part, "ratios": ratios, "parts": 2, "triangles": 100,
              "engine": identity}
    if mode == "noid":  # an older checker: no engine identity
        del result["engine"]
    print(json.dumps(result))
    if mode == "exit":
        return 0 if not ok else 1  # exit status disagrees with the report
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
