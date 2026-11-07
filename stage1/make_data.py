#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Stage 1 data: engine-generated, machine-format examples with NO prose.

Owner decision 2026-11-07: no text written by an AI company's model goes into training
data. So these examples contain only engine identifiers (component ids, parameter
names, part ids, refusal reasons), numbers and scene JSON. There is no system prompt,
no question sentence and no teaching step. The scene title is the component id.

Tasks (the user turn is a few `key: value` lines; the assistant turn is scene JSON):

  author.ratio   spurPair / planetaryStage with a target ratio for one part; the
                 model must choose tooth counts that the engine accepts and that solve
                 to exactly that ratio (several answers can be right).
  author.params  sliderCrank / propeller with explicit parameter values.
  repair         a refused scene (one mutation from generate_repairs.py) plus the
                 engine's reason; the target is the accepted scene.

Every target scene passes `marty-solid check`; every ratio target equals the ratio
the engine solved. Output: mlx-lm chat-format JSON Lines (`{"messages": [...]}`) for
train / valid / dev, plus a parallel `*.meta.jsonl` with provenance and the fields the
evaluator needs. Same arguments give the same bytes.

Usage:
  python3 stage1/make_data.py --engine PATH/marty-solid --engine-commit 76104dea \\
      --out-dir DIR --seed 1 [--train 1300] [--valid 100] [--dev 100] [--created YYYY-MM-DD]
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
import generate_components as gc  # noqa: E402
import generate_repairs as gr  # noqa: E402

NAME = "stage1/make_data.py"
VERSION = "0.1.0"
SCHEMA = "marty-model.stage1/0"
# Mutations that apply to step-free scenes (no highlights, no step text).
REPAIR_MUTATIONS = ["param.rangeHigh", "param.rangeLow", "param.integer", "param.valueText", "param.typo",
                    "param.outsideWith", "component.typo", "text.titleLong"]
# Share of each task in a split: (task, component) -> weight.
MIX = [("author.ratio", "spurPair", 3), ("author.ratio", "planetaryStage", 3),
       ("author.params", "sliderCrank", 1), ("author.params", "propeller", 1), ("repair", None, 4)]
IID = {"spurPair": "gears", "planetaryStage": "stage", "sliderCrank": "engine", "propeller": "prop"}


def scene(component, values):
    doc = {"v": 1, "kind": "assembly", "title": component, "units": "mm",
           "parts": [{"id": IID[component], "use": component, "with": values}]}
    return json.dumps(doc, separators=(",", ":"))


def compact_with(values):
    return json.dumps(values, separators=(",", ":"))


def sample_author(rng, task, component):
    """Return (user text, scene text, target dict) for one author example, before the engine check."""
    iid = IID[component]
    if component == "spurPair":
        values = gc.spur_pair(rng)
        target = (f"{iid}.wheel", -Fraction(values["pinionTeeth"], values["wheelTeeth"]))
        fixed = {k: values[k] for k in ("module", "width")}
    elif component == "planetaryStage":
        values = gc.planetary(rng)
        s, pl = values["sunTeeth"], values["planetTeeth"]
        target = (f"{iid}.carrier", Fraction(s, 2 * s + 2 * pl))
        fixed = {k: values[k] for k in ("planets", "module", "width")}
    elif component == "sliderCrank":
        values, target, fixed = gc.slider_crank(rng), None, None
    else:
        values, target, fixed = gc.propeller(rng), None, None
    if task == "author.ratio":
        part, ratio = target
        user = f"task: author\ncomponent: {component}\nratio {part}: {gc.frac_text(ratio)}\nwith: {compact_with(fixed)}"
        want = {"part": part, "ratio": [ratio.numerator, ratio.denominator]}
    else:
        user = f"task: author\ncomponent: {component}\nwith: {compact_with(values)}"
        want = {"with": values}
    return user, scene(component, values), want, values


def repair_user(reason, part, refused):
    return f"task: repair\nreason: {reason}\npart: {part}\nscene: {refused}"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(engine, catalog, n, seed, split, created, engine_commit, generator, seen_scenes, seen_users=None):
    """n examples for one split. `seen_scenes` and `seen_users` (sets of sha256 of the target
    scene and of the user text) keep splits disjoint: no dev prompt equals a train prompt."""
    seen_users = set() if seen_users is None else seen_users
    rng = random.Random(f"{seed}:{split}")
    weights = [w for *_, w in MIX]
    rows, metas, attempts = [], [], 0
    slot = None  # the (task, component) being filled; kept until it succeeds, so refusals do not skew the mix
    while len(rows) < n and attempts < n * 40:
        attempts += 1
        if slot is None:
            task, component, _ = rng.choices(MIX, weights=weights)[0]
            if task == "repair":
                component = rng.choice(sorted(IID))
            slot = (task, component)
        task, component = slot
        if task == "repair":
            base_task = "author.ratio" if component in ("spurPair", "planetaryStage") else "author.params"
            _, target_scene, _, values = sample_author(rng, base_task, component)
        else:
            user, target_scene, want, values = sample_author(rng, task, component)
        if sha(target_scene) in seen_scenes:
            continue
        report = engine.check(target_scene)
        if not report.get("ok"):
            continue  # an invalid sample: the engine is the judge; nothing is emitted
        if task == "author.ratio":
            got = (report.get("ratios") or {}).get(want["part"])
            if gc.ratio_mismatch({want["part"]: Fraction(*want["ratio"])}, {want["part"]: got}) is not None:
                raise RuntimeError(f"generator bug: solved ratio {got} != {want} for {target_scene}")
        if task == "repair":
            doc = json.loads(target_scene)
            mutation = rng.choice(REPAIR_MUTATIONS)
            if component not in catalog:
                raise RuntimeError(f"component {component} is not in the engine catalog")
            result = gr.MUTATIONS[mutation](doc, catalog[component], rng)
            if result is None:
                continue
            mutated, expected = result
            refused = gr.compact(mutated)
            refusal = engine.check(refused)
            if refusal.get("ok") or refusal.get("reason") != expected:
                continue  # keep only exact, known refusals
            user = repair_user(refusal["reason"], refusal.get("part"), refused)
            want = {"reason": refusal["reason"], "mutation": mutation}
        if sha(user) in seen_users:
            continue  # the same prompt (for example the same ratio) already exists in some split
        slot = None
        seen_scenes.add(sha(target_scene))
        seen_users.add(sha(user))
        rows.append({"messages": [{"role": "user", "content": user},
                                  {"role": "assistant", "content": target_scene}]})
        metas.append({
            "schema": SCHEMA, "id": f"s1-{split}-s{seed}-{len(metas):05d}", "split": split, "task": task,
            "component": component, "want": want, "with": values,
            "provenance": {"source": "programmatic.stage1", "authorKind": "program", "prose": False,
                           "licence": "Apache-2.0", "clearance": "cleared-stage1-local",
                           "clearanceReason": "owner approval 2026-11-07: local Stage 1 comparison only, not for release",
                           "generator": {"name": NAME, "version": VERSION, "seed": seed, **(generator or {})},
                           "engine": {"commit": engine_commit, "checkerSha256": engine.sha256},
                           "created": created, "sceneSha256": sha(target_scene)},
        })
    if len(rows) < n:
        raise RuntimeError(f"{split}: only {len(rows)} of {n} examples after {attempts} attempts")
    return rows, metas


def write(path, rows):
    with open(path, "x", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engine", required=True)
    ap.add_argument("--engine-commit", required=True)
    ap.add_argument("--out-dir", required=True, help="new or empty folder (outside the repository)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--train", type=int, default=1300)
    ap.add_argument("--valid", type=int, default=100)
    ap.add_argument("--dev", type=int, default=100)
    ap.add_argument("--created", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{7,40}", a.engine_commit):
        ap.error("--engine-commit must be 7-40 lowercase hex characters")
    for name in ("train", "valid", "dev"):
        if not 1 <= getattr(a, name) <= 50_000:
            ap.error(f"--{name} must be 1..50000")
    if os.path.exists(a.out_dir) and (not os.path.isdir(a.out_dir) or os.listdir(a.out_dir)):
        ap.error(f"{a.out_dir} is not empty; refusing to overwrite")
    os.makedirs(a.out_dir, exist_ok=True)

    engine = gc.Engine([a.engine], a.engine)
    seen, seen_users = set(), set()
    summary = {"engineCommit": a.engine_commit, "checkerSha256": engine.sha256, "seed": a.seed, "files": {}}
    try:
        catalog = gr.load_catalog(engine)
        ident = gc.generator_identity(__file__)
        for split in ("train", "valid", "dev"):
            rows, metas = build(engine, catalog, getattr(a, split), a.seed, split, a.created, a.engine_commit,
                                ident, seen, seen_users)
            for suffix, data in ((".jsonl", rows), (".meta.jsonl", metas)):
                path = os.path.join(a.out_dir, split + suffix)
                write(path, data)
                with open(path, "rb") as f:
                    summary["files"][split + suffix] = {"rows": len(data), "sha256": hashlib.sha256(f.read()).hexdigest()}
            counts = {}
            for m in metas:
                key = m["task"] + ":" + m["component"]
                counts[key] = counts.get(key, 0) + 1
            summary[split] = counts
    finally:
        engine.close()
    with open(os.path.join(a.out_dir, "SUMMARY.json"), "x", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print(json.dumps(summary, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
