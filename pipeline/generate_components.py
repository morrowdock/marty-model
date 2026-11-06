#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reference generator: engine-checked training examples from the MartyGraphics
built-in solid components. It calls no AI model.

For each example it samples component parameters, writes a learner question and a
scene (one `use` entry plus teaching steps) from fixed templates, runs the engine
(`marty-solid check`), and keeps the example only when the engine accepts the scene
AND every number the steps state agrees with the ratios the engine solved. Refused
scenes go to an optional rejects file with the engine's reason (later repair data).

Standard library only. Same arguments and seed give the same output bytes.

Usage:
  python3 pipeline/generate_components.py --engine PATH/marty-solid \\
      --engine-commit 76104dea --count 40 --seed 1 --out examples.jsonl \\
      [--rejects rejects.jsonl] [--components spurPair,planetaryStage] \\
      [--strict] [--created YYYY-MM-DD]

Status: design reference. Output is NOT cleared for training until the owner
decides the data-rights questions in DATA.md ("clearance": "pending-owner").
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
import tempfile
from fractions import Fraction

SCHEMA = "marty-model.example/0"
REJECT_SCHEMA = "marty-model.reject/0"
NAME = "generate_components.py"
VERSION = "0.1.0"
TITLE_MAX, SAY_MAX = 80, 240  # engine text limits (assembly.title, step.say)
RATIO_TOLERANCE = 1e-9


# ---------------------------------------------------------------- engine


class Engine:
    """Runs `<cmd> check FILE` and returns the parsed JSON report.

    `cmd` is the argument list that starts the checker (normally just the binary
    path); `binary` is the file whose SHA-256 goes into provenance.
    """

    def __init__(self, cmd, binary, strict=False, timeout=60):
        self.cmd = list(cmd)
        self.strict = strict
        self.timeout = timeout
        with open(binary, "rb") as f:
            self.sha256 = hashlib.sha256(f.read()).hexdigest()
        self._dir = tempfile.TemporaryDirectory(prefix="marty-gen-")

    def close(self):
        self._dir.cleanup()

    @property
    def command_text(self):
        return "marty-solid check" + (" --strict" if self.strict else "")

    def check(self, scene_text):
        path = os.path.join(self._dir.name, "scene.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(scene_text)
        args = self.cmd + ["check", path] + (["--strict"] if self.strict else [])
        try:
            done = subprocess.run(args, capture_output=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "reason": "engine.timeout", "part": None}
        try:
            report = json.loads(done.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"ok": False, "reason": "engine.output", "part": None}
        if not isinstance(report, dict) or not isinstance(report.get("ok"), bool):
            return {"ok": False, "reason": "engine.output", "part": None}
        # The exit status and the report must agree; anything else is an engine fault.
        if report["ok"] != (done.returncode == 0):
            return {"ok": False, "reason": "engine.exit", "part": None}
        return report


# ---------------------------------------------------------------- text helpers


def frac_text(f):
    """Exact ratio text: '1/3', '2/7', '3'."""
    f = Fraction(f)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def num_text(x):
    """A length or factor without trailing zeros: 48, 1.5, 2.333."""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    return f"{float(x):.4g}"


def factor_text(f):
    """'3' for an exact factor, otherwise '36/14 ≈ 2.571'."""
    f = Fraction(f)
    return frac_text(f) if f.denominator == 1 else f"{frac_text(f)} ≈ {float(f):.4g}"


# ---------------------------------------------------------------- recipes
#
# A recipe samples parameters for one built-in component and writes the question,
# title and steps. `expected` maps engine part ids to the ratio (turns per input
# turn) that the text depends on; the generator keeps an example only when the
# engine's solved ratios match these exactly (within RATIO_TOLERANCE).


class Draft:
    def __init__(self, question, title, steps, expected):
        self.question, self.title, self.steps, self.expected = question, title, steps, expected


NOT_MODELLED = "Checked by the engine: shapes, joints{extra}. Not modelled: strength, friction and losses."


def spur_pair(rng):
    p = rng.randint(12, 40)
    w = rng.randint(p + 4, 160)
    m = rng.choice([1, 1.5, 2, 2.5, 3])
    width = rng.choice([6, 8, 10, 12])
    return {"pinionTeeth": p, "wheelTeeth": w, "module": m, "width": width}


def spur_pair_text(rng, iid, v):
    p, w, m = v["pinionTeeth"], v["wheelTeeth"], Fraction(str(v["module"]))
    ratio = Fraction(p, w)
    centre = (p + w) * m / 2
    question = rng.choice([
        f"How does a {p}-tooth gear turning a {w}-tooth gear change the speed?",
        f"Show a spur gear pair: a {p}-tooth pinion driving a {w}-tooth wheel, module {num_text(m)} mm.",
        f"Why does the bigger gear turn slower when a {p}-tooth gear drives a {w}-tooth gear?",
    ])
    title = f"Spur gear pair: {p} teeth driving {w} teeth"
    steps = [
        {"say": f"A {p}-tooth pinion drives a {w}-tooth wheel. Both have module {num_text(m)} mm, "
                "so their teeth are the same size and mesh.", "camera": "hero"},
        {"say": f"Input: the pinion turns. Each turn moves {p} teeth past the point where the gears touch.",
         "highlight": [f"{iid}.input"], "spin": 1},
        {"say": f"Output: the wheel turns {p}/{w} = {frac_text(ratio)} of a turn per pinion turn, "
                "in the opposite direction.", "highlight": [f"{iid}.output"], "spin": 1},
        {"say": f"So the wheel is {factor_text(1 / ratio)} times slower. The centre distance is "
                f"({p} + {w}) × {num_text(m)} / 2 = {num_text(centre)} mm.", "highlight": [iid]},
        {"say": NOT_MODELLED.format(extra=", tooth meshing and the ratio"), "camera": "iso"},
    ]
    return Draft(question, title, steps, {f"{iid}.pinion": Fraction(1), f"{iid}.wheel": -ratio})


def planetary(rng):
    return {"sunTeeth": rng.randint(12, 40), "planetTeeth": rng.randint(12, 30),
            "planets": rng.choice([3, 3, 3, 4, 5]), "module": rng.choice([1, 1.5, 2]),
            "width": rng.choice([8, 10, 12])}


def planetary_text(rng, iid, v):
    s, pl, n = v["sunTeeth"], v["planetTeeth"], v["planets"]
    r = s + 2 * pl
    carrier = Fraction(s, s + r)
    question = rng.choice([
        f"How does a planetary gear set with a {s}-tooth sun and {pl}-tooth planets reduce speed?",
        f"Show a planetary gearbox: {s}-tooth sun, {n} planets of {pl} teeth, fixed ring.",
        f"Explain a planetary gear stage where the ring is held and the sun ({s} teeth) is the input.",
    ])
    title = f"Planetary gear stage: {s}-tooth sun, {n} planets, {r}-tooth ring"
    steps = [
        {"say": f"{n} planet gears ride on a carrier between a {s}-tooth sun gear and a fixed "
                f"{r}-tooth ring gear.", "camera": "hero"},
        {"say": "Input: the sun gear turns.", "highlight": [f"{iid}.input"], "spin": 1},
        {"say": f"Each planet ({pl} teeth) meshes with the sun and rolls inside the fixed ring. "
                f"The ring has {s} + 2 × {pl} = {r} teeth.", "highlight": [f"{iid}.planet"], "spin": 1},
        {"say": f"Output: the carrier turns {s} / ({s} + {r}) = {frac_text(carrier)} of a turn per sun "
                "turn, in the same direction.", "highlight": [f"{iid}.output"], "spin": 1},
        {"say": f"So the carrier is {factor_text(1 / carrier)} times slower than the sun.", "explode": 1,
         "camera": "iso"},
        {"say": NOT_MODELLED.format(extra=", tooth meshing and the ratio")},
    ]
    return Draft(question, title, steps, {f"{iid}.sun": Fraction(1), f"{iid}.carrier": carrier})


def slider_crank(rng):
    return {"radius": rng.randint(10, 40), "rod": rng.randint(30, 200), "piston": rng.randint(8, 24)}


def slider_crank_text(rng, iid, v):
    r, rod = v["radius"], v["rod"]
    question = rng.choice([
        f"How does a slider-crank with a {r} mm crank turn rotation into back-and-forth motion?",
        f"Show a crank and connecting rod ({rod} mm) driving a piston.",
        f"What is the piston stroke of a slider-crank with crank radius {r} mm?",
    ])
    title = f"Slider-crank: {r} mm crank, {rod} mm rod"
    steps = [
        {"say": "A slider-crank changes turning motion into straight back-and-forth motion.", "camera": "hero"},
        {"say": f"Input: the crank turns. Its pin moves on a circle of radius {r} mm.",
         "highlight": [f"{iid}.input"], "spin": 1},
        {"say": f"The {rod} mm connecting rod joins the crank pin to the piston.",
         "highlight": [f"{iid}.rod"], "spin": 1},
        {"say": f"The piston slides on a straight line. Its stroke is 2 × {r} = {2 * r} mm for each "
                "crank turn.", "highlight": [f"{iid}.output"], "spin": 1},
        {"say": NOT_MODELLED.format(extra=" and the crank-rod linkage")},
    ]
    return Draft(question, title, steps, {f"{iid}.crank": Fraction(1)})


def propeller(rng):
    pitch = rng.randint(-60, -25)
    return {"blades": rng.randint(2, 6), "span": rng.choice([80, 100, 120, 150]),
            "chord": rng.choice([24, 30, 34, 40]), "pitch": pitch,
            "twist": rng.randint(8, -pitch - 8), "hub": rng.choice([10, 12, 16])}


def propeller_text(rng, iid, v):
    n, span, pitch, twist = v["blades"], v["span"], v["pitch"], v["twist"]
    tip = pitch + twist  # pitch < 0 and twist < -pitch, so tip < 0: same sign as the root
    question = rng.choice([
        f"Show a {n}-blade propeller and how its blades are twisted.",
        f"Why are propeller blades twisted? Use a {n}-blade propeller with {span} mm blades.",
        f"Show a propeller with {n} blades turning on its hub.",
    ])
    title = f"Propeller: {n} blades, {span} mm span"
    steps = [
        {"say": f"A propeller with {n} blades. Each blade is an airfoil {span} mm long.", "camera": "hero"},
        {"say": f"Input: the hub turns, and all {n} blades turn with it.",
         "highlight": [f"{iid}.input"], "spin": 1},
        {"say": f"The blade angle is {-pitch}° at the root and {-tip}° at the tip: steeper near the hub, "
                "flatter at the tip, because the tip moves faster.", "highlight": [f"{iid}.blade"]},
        {"say": "Checked by the engine: closed shapes and joints. Not modelled: air flow, thrust and strength."},
    ]
    return Draft(question, title, steps, {f"{iid}.hub": Fraction(1)})


RECIPES = {
    # component id: (instance id, sampler, text writer)
    "spurPair": ("gears", spur_pair, spur_pair_text),
    "planetaryStage": ("stage", planetary, planetary_text),
    "sliderCrank": ("engine", slider_crank, slider_crank_text),
    "propeller": ("prop", propeller, propeller_text),
}


# ---------------------------------------------------------------- generation


def scene_document(component, iid, values, draft):
    doc = {"v": 1, "kind": "assembly", "title": draft.title, "units": "mm",
           "parts": [{"id": iid, "use": component, "with": values}],
           "steps": draft.steps}
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))


def text_problems(draft):
    problems = []
    if len(draft.title) > TITLE_MAX:
        problems.append("text.title")
    for step in draft.steps:
        if len(step["say"]) > SAY_MAX:
            problems.append("text.say")
    return problems


def ratio_mismatch(expected, solved):
    """First part id whose solved ratio is missing or differs from the text's number, else None."""
    for part, want in sorted(expected.items()):
        got = solved.get(part)
        if not isinstance(got, (int, float)) or abs(float(want) - got) > RATIO_TOLERANCE:
            return part
    return None


def generate(engine, count, seed, components, created, engine_commit, generator_commit=None,
             max_attempts_per_example=20):
    """Return (examples, rejects): lists of dicts, in a deterministic order."""
    rng = random.Random(seed)
    examples, rejects, seen = [], [], set()
    attempts = 0
    while len(examples) < count and attempts < count * max_attempts_per_example:
        attempts += 1
        component = components[(attempts - 1) % len(components)]
        iid, sampler, writer = RECIPES[component]
        values = sampler(rng)
        key = (component, json.dumps(values, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        draft = writer(rng, iid, values)
        scene = scene_document(component, iid, values, draft)
        problems = text_problems(draft)
        if problems:  # a template bug: never let the engine be the first to notice
            raise ValueError(f"{component} {values}: {problems}")
        report = engine.check(scene)
        base = {"component": component, "with": values, "scene": scene,
                "sceneSha256": hashlib.sha256(scene.encode("utf-8")).hexdigest()}
        if not report["ok"]:
            rejects.append({"schema": REJECT_SCHEMA, "attempt": attempts, **base,
                            "reason": report.get("reason"), "part": report.get("part")})
            continue
        wrong = ratio_mismatch(draft.expected, report.get("ratios") or {})
        if wrong is not None:
            rejects.append({"schema": REJECT_SCHEMA, "attempt": attempts, **base,
                            "reason": "generator.ratioMismatch", "part": wrong})
            continue
        examples.append({
            "schema": SCHEMA,
            "id": f"cmp-s{seed}-{len(examples):05d}",
            "task": "author.solid",
            "question": draft.question,
            "scene": scene,
            "provenance": {
                "source": "programmatic.components",
                "authorKind": "program",
                "licence": "Apache-2.0",
                "clearance": "pending-owner",
                "component": component,
                "with": values,
                "generator": {"name": NAME, "version": VERSION, "seed": seed, "commit": generator_commit},
                "engine": {"commit": engine_commit, "checkerSha256": engine.sha256},
                "created": created,
                "sceneSha256": base["sceneSha256"],
            },
            "check": {"command": engine.command_text, "ok": True, "reason": None,
                      "ratios": report.get("ratios"), "parts": report.get("parts"),
                      "triangles": report.get("triangles")},
        })
    return examples, rejects


def write_jsonl(path, rows):
    # "x": never overwrite an existing dataset file.
    with open(path, "x", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def git_head(path):
    try:
        out = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=10, check=True).stdout.strip()
        return out if re.fullmatch(r"[0-9a-f]{40}", out) else None
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engine", required=True, help="path to the marty-solid binary")
    ap.add_argument("--engine-commit", required=True, help="MartyGraphics commit the binary was built from")
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True, help="new JSON Lines file (must not exist)")
    ap.add_argument("--rejects", help="new JSON Lines file for refused scenes (must not exist)")
    ap.add_argument("--components", default=",".join(RECIPES), help="comma-separated component ids")
    ap.add_argument("--strict", action="store_true", help="pass --strict to the checker")
    ap.add_argument("--created", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{7,40}", a.engine_commit):
        ap.error("--engine-commit must be 7-40 lowercase hex characters")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.created):
        ap.error("--created must be YYYY-MM-DD")
    if not 1 <= a.count <= 100_000:
        ap.error("--count must be 1..100000")
    components = [c for c in a.components.split(",") if c]
    unknown = [c for c in components if c not in RECIPES]
    if unknown or not components:
        ap.error(f"unknown components {unknown}; known: {sorted(RECIPES)}")
    for path in filter(None, [a.out, a.rejects]):
        if os.path.exists(path):
            ap.error(f"{path} exists; refusing to overwrite")

    engine = Engine([a.engine], a.engine, strict=a.strict)
    try:
        examples, rejects = generate(engine, a.count, a.seed, components, a.created, a.engine_commit,
                                     generator_commit=git_head(os.path.dirname(os.path.abspath(__file__))))
    finally:
        engine.close()
    write_jsonl(a.out, examples)
    if a.rejects:
        write_jsonl(a.rejects, rejects)
    reasons = {}
    for r in rejects:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    print(json.dumps({"examples": len(examples), "rejects": len(rejects), "rejectReasons": reasons,
                      "checkerSha256": engine.sha256}, sort_keys=True), file=sys.stderr)
    return 0 if len(examples) == a.count else 1


if __name__ == "__main__":
    sys.exit(main())
