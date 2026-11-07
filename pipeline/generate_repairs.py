#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reference generator: engine-checked REPAIR examples by deliberate mutation. It calls
no AI model and writes no new prose.

Input: accepted examples from generate_components.py (task `author.solid`). For each
one it applies one small, known mistake to the scene (a parameter out of range, an
unknown parameter name, a non-whole tooth count, a misspelt component id, a bad step
reference, text over the limit, ...), runs the engine, and keeps the pair only when

  * the engine refuses the mutated scene with exactly the expected stable reason, and
  * the engine still accepts the original scene with the same ratios.

The repair example is: question + refused scene + engine reason -> the original scene
(the full corrected scene; v0.1 repairs are full scenes, see DATA.md 4.1).

Usage:
  python3 pipeline/generate_repairs.py --engine PATH/marty-solid --engine-commit 76104dea \\
      --examples examples.jsonl --seed 1 --out repairs.jsonl [--rejects rejects.jsonl] \\
      [--per-example 1] [--created YYYY-MM-DD]

Status: design reference; output inherits "clearance" from its source examples (DATA.md 0).
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_components as gc  # noqa: E402

SCHEMA = gc.SCHEMA
REJECT_SCHEMA = gc.REJECT_SCHEMA
NAME = "generate_repairs.py"
VERSION = "0.1.0"
MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024
MAX_EXAMPLES = 200_000
TITLE_MAX, SAY_MAX = gc.TITLE_MAX, gc.SAY_MAX


# ---------------------------------------------------------------- catalog


def load_catalog(engine):
    """{component id: {param name: spec}} from `<engine> components`."""
    try:
        done = subprocess.run(engine.cmd + ["components"], capture_output=True, timeout=engine.timeout, check=False)
        data = json.loads(done.stdout.decode("utf-8"))
        return {c["id"]: c["params"] for c in data["components"]}
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as e:
        raise RuntimeError(f"cannot read the component catalog from the engine: {e}")


# ---------------------------------------------------------------- mutations
#
# Each mutation takes (doc, params spec, rng) and returns (mutated doc, expected reason)
# or None when it does not apply to this scene. Docs are plain dicts; mutations copy.


def _use(doc):
    return doc["parts"][0]


def _pick(rng, names):
    return rng.choice(sorted(names)) if names else None


def m_range_high(doc, spec, rng):
    name = _pick(rng, _use(doc).get("with", {}))
    if name is None:
        return None
    _use(doc)["with"][name] = spec[name]["max"] + 1
    return doc, f"component.param.range.{name}"


def m_range_low(doc, spec, rng):
    name = _pick(rng, _use(doc).get("with", {}))
    if name is None:
        return None
    _use(doc)["with"][name] = spec[name]["min"] - 1
    return doc, f"component.param.range.{name}"


def m_integer(doc, spec, rng):
    name = _pick(rng, [n for n in _use(doc).get("with", {}) if spec[n].get("integer")])
    if name is None:
        return None
    _use(doc)["with"][name] = _use(doc)["with"][name] + 0.5
    return doc, f"component.param.integer.{name}"


def m_value_text(doc, spec, rng):
    name = _pick(rng, _use(doc).get("with", {}))
    if name is None:
        return None
    _use(doc)["with"][name] = gc.num_text(Fraction(str(_use(doc)["with"][name])))
    return doc, f"component.param.value.{name}"


def m_param_typo(doc, spec, rng):
    """Drop the last letter of a parameter name: pinionTeeth -> pinionTeet."""
    w = _use(doc).get("with", {})
    name = _pick(rng, [n for n in w if len(n) > 2 and n[:-1] not in spec])
    if name is None:
        return None
    _use(doc)["with"] = {(n[:-1] if n == name else n): v for n, v in w.items()}
    return doc, f"component.param.unknown.{name[:-1]}"


def m_param_outside_with(doc, spec, rng):
    """Write a parameter beside `use` instead of inside `with`."""
    w = _use(doc).get("with", {})
    name = _pick(rng, [n for n in w if n not in ("id", "use", "with", "at", "rot", "parent", "set")])
    if name is None:
        return None
    value = w.pop(name)
    _use(doc)[name] = value
    return doc, f"component.use.unknown.{name}"


def m_component_typo(doc, spec, rng):
    _use(doc)["use"] = _use(doc)["use"] + "s"
    return doc, f"component.unknown.{_use(doc)['use']}"


def m_anchor_typo(doc, spec, rng):
    """Misspell one highlighted anchor: gears.input -> gears.inputs."""
    iid = _use(doc)["id"]
    spots = [(i, j) for i, step in enumerate(doc.get("steps", []))
             for j, ref in enumerate(step.get("highlight", [])) if ref.startswith(iid + ".")]
    if not spots:
        return None
    i, j = rng.choice(spots)
    ref = doc["steps"][i]["highlight"][j] + "s"
    doc["steps"][i]["highlight"][j] = ref
    return doc, f"ref.unknown.{ref}"


def m_title_long(doc, spec, rng):
    title = doc["title"]
    while len(title) <= TITLE_MAX:
        title = f"{title}: {doc['title']}"
    doc["title"] = title
    return doc, "assembly.title"


def m_say_long(doc, spec, rng):
    steps = doc.get("steps", [])
    if not steps:
        return None
    i = rng.randrange(len(steps))
    say = steps[i]["say"]
    while len(say) <= SAY_MAX:
        say = f"{say} {steps[i]['say']}"
    steps[i]["say"] = say
    return doc, "step.say"


MUTATIONS = {
    "param.rangeHigh": m_range_high,
    "param.rangeLow": m_range_low,
    "param.integer": m_integer,
    "param.valueText": m_value_text,
    "param.typo": m_param_typo,
    "param.outsideWith": m_param_outside_with,
    "component.typo": m_component_typo,
    "ref.anchorTypo": m_anchor_typo,
    "text.titleLong": m_title_long,
    "text.sayLong": m_say_long,
}


# ---------------------------------------------------------------- input


def read_examples(path, engine_commit):
    """Accepted author.solid examples, validated and bounded. Raises ValueError on bad input."""
    if os.path.getsize(path) > MAX_INPUT_BYTES:
        raise ValueError(f"{path}: larger than {MAX_INPUT_BYTES} bytes")
    rows = []
    with open(path, "rb") as f:
        for number, raw in enumerate(f, 1):
            if len(raw) > MAX_LINE_BYTES:
                raise ValueError(f"{path}:{number}: line longer than {MAX_LINE_BYTES} bytes")
            if len(rows) >= MAX_EXAMPLES:
                raise ValueError(f"{path}: more than {MAX_EXAMPLES} examples")
            try:
                row = json.loads(raw.decode("utf-8"))
                ok = (row["schema"] == SCHEMA and row["task"] == "author.solid" and row["check"]["ok"] is True
                      and isinstance(row["scene"], str) and isinstance(row["question"], str))
                commit = row["provenance"]["engine"]["commit"]
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as e:
                raise ValueError(f"{path}:{number}: not an accepted {SCHEMA} author.solid example ({e})")
            if not ok:
                raise ValueError(f"{path}:{number}: not an accepted {SCHEMA} author.solid example")
            if commit != engine_commit:
                raise ValueError(f"{path}:{number}: example was checked at engine {commit}, not {engine_commit}")
            rows.append(row)
    return rows


# ---------------------------------------------------------------- generation


def compact(doc):
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate(engine, catalog, examples, seed, per_example, created, engine_commit, generator=None):
    """Return (repairs, rejects) in a deterministic order."""
    rng = random.Random(seed)
    names = sorted(MUTATIONS)
    repairs, rejects = [], []
    for src in examples:
        original = src["scene"]
        component = src["provenance"]["component"]
        spec = catalog.get(component)
        if spec is None:
            rejects.append({"schema": REJECT_SCHEMA, "from": src["id"], "reason": "repair.componentNotInCatalog",
                            "component": component})
            continue
        # The original must still pass on this engine, with the ratios recorded in the example.
        target = engine.check(original)
        if not target.get("ok") or target.get("ratios") != src["check"]["ratios"]:
            rejects.append({"schema": REJECT_SCHEMA, "from": src["id"], "reason": "repair.targetChanged",
                            "engineReason": target.get("reason")})
            continue
        for mutation in rng.sample(names, k=min(per_example, len(names))):
            doc = json.loads(original)
            result = MUTATIONS[mutation](doc, spec, rng)
            if result is None:
                continue
            mutated, expected = result
            refused_text = compact(mutated)
            report = engine.check(refused_text)
            base = {"from": src["id"], "mutation": mutation, "refused": refused_text, "expected": expected}
            if report.get("ok"):
                rejects.append({"schema": REJECT_SCHEMA, **base, "reason": "repair.mutationAccepted"})
                continue
            if report.get("reason") != expected:
                rejects.append({"schema": REJECT_SCHEMA, **base, "reason": "repair.unexpectedReason",
                                "engineReason": report.get("reason")})
                continue
            prov = src["provenance"]
            repairs.append({
                "schema": SCHEMA,
                "id": f"rep-s{seed}-{len(repairs):05d}",
                "task": "repair.solid",
                "question": src["question"],
                "refused": refused_text,
                "reason": report["reason"],
                "part": report.get("part"),
                "scene": original,
                "provenance": {
                    "source": "programmatic.mutation",
                    "authorKind": "program",
                    "licence": prov["licence"],
                    "clearance": prov["clearance"],
                    "templateAuthor": prov["templateAuthor"],
                    "component": component,
                    "mutation": mutation,
                    "fromExample": src["id"],
                    "fromSceneSha256": prov["sceneSha256"],
                    "refusedSha256": sha(refused_text),
                    "sceneSha256": sha(original),
                    "generator": {"name": NAME, "version": VERSION, "seed": seed, **(generator or {})},
                    "engine": {"commit": engine_commit, "checkerSha256": engine.sha256},
                    "created": created,
                },
                "check": {"command": engine.COMMAND,
                          "refused": {"ok": False, "reason": report["reason"], "part": report.get("part")},
                          "target": {"ok": True, "ratios": target.get("ratios")}},
            })
    return repairs, rejects


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engine", required=True, help="path to the marty-solid binary")
    ap.add_argument("--engine-commit", required=True, help="MartyGraphics commit the binary was built from")
    ap.add_argument("--examples", required=True, help="accepted examples from generate_components.py")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--per-example", type=int, default=1, help=f"mutations per example (1..{len(MUTATIONS)})")
    ap.add_argument("--out", required=True, help="new JSON Lines file (must not exist)")
    ap.add_argument("--rejects", help="new JSON Lines file for dropped pairs (must not exist)")
    ap.add_argument("--created", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{7,40}", a.engine_commit):
        ap.error("--engine-commit must be 7-40 lowercase hex characters")
    try:
        if datetime.date.fromisoformat(a.created).isoformat() != a.created:
            raise ValueError
    except ValueError:
        ap.error("--created must be YYYY-MM-DD")
    if not 1 <= a.per_example <= len(MUTATIONS):
        ap.error(f"--per-example must be 1..{len(MUTATIONS)}")
    outputs = [p for p in (a.out, a.rejects) if p]
    if len({os.path.abspath(p) for p in outputs}) != len(outputs) or os.path.abspath(a.examples) in {
            os.path.abspath(p) for p in outputs}:
        ap.error("--examples, --out and --rejects must be different files")
    for path in outputs:
        if os.path.exists(path):
            ap.error(f"{path} exists; refusing to overwrite")
        if not os.path.isdir(os.path.dirname(os.path.abspath(path))):
            ap.error(f"folder for {path} does not exist")
    try:
        examples = read_examples(a.examples, a.engine_commit)
    except (OSError, ValueError) as e:
        ap.error(str(e))

    engine = gc.Engine([a.engine], a.engine)
    try:
        catalog = load_catalog(engine)
        repairs, rejects = generate(engine, catalog, examples, a.seed, a.per_example, a.created, a.engine_commit,
                                    generator=gc.generator_identity(__file__))
    finally:
        engine.close()
    gc.write_jsonl(a.out, repairs)
    if a.rejects:
        gc.write_jsonl(a.rejects, rejects)
    counts = {}
    for r in repairs:
        m = r["provenance"]["mutation"]
        counts[m] = counts.get(m, 0) + 1
    reasons = {}
    for r in rejects:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    print(json.dumps({"repairs": len(repairs), "byMutation": counts, "rejects": len(rejects),
                      "rejectReasons": reasons, "checkerSha256": engine.sha256}, sort_keys=True), file=sys.stderr)
    return 0 if repairs and not any(r["reason"] in ("repair.targetChanged", "repair.unexpectedReason")
                                    for r in rejects) else 1


if __name__ == "__main__":
    sys.exit(main())
