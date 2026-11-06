# SPDX-License-Identifier: Apache-2.0
"""Tests for pipeline/generate_components.py.

Unit tests use tests/fake_engine.py. The integration test runs the real engine only
when MARTY_SOLID (binary path) and MARTY_SOLID_COMMIT are set; otherwise it skips.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))

import generate_components as g  # noqa: E402

FAKE = os.path.join(HERE, "fake_engine.py")
ALL = list(g.RECIPES)


def fake(mode="ok"):
    return g.Engine([sys.executable, FAKE, f"--mode={mode}"], FAKE)


def run(engine, count=12, seed=7, components=ALL):
    try:
        return g.generate(engine, count, seed, components, "2026-11-06", "76104dea")
    finally:
        engine.close()


class TextHelpers(unittest.TestCase):
    def test_fractions(self):
        self.assertEqual(g.frac_text(Fraction(12, 36)), "1/3")
        self.assertEqual(g.frac_text(Fraction(6, 2)), "3")
        self.assertEqual(g.factor_text(Fraction(36, 14)), "18/7 ≈ 2.571")
        self.assertEqual(g.ratio_text(16, 36), "16/36 = 4/9")
        self.assertEqual(g.ratio_text(13, 40), "13/40")

    def test_num_text_is_exact(self):
        self.assertEqual(g.num_text(Fraction(3, 2)), "1.5")
        self.assertEqual(g.num_text(48), "48")
        self.assertEqual(g.num_text(Fraction(199 * 5, 4)), "248.75")  # (39 + 160) x 2.5 / 2
        self.assertEqual(g.num_text(Fraction(-1, 8)), "-0.125")
        self.assertEqual(g.num_text(Fraction(1, 20)), "0.05")
        with self.assertRaises(ValueError):
            g.num_text(Fraction(1, 3))

    def test_every_centre_distance_is_exact(self):
        for m in (1, 1.5, 2, 2.5, 3):
            for teeth in range(12 + 16, 40 + 160 + 1):
                value = teeth * Fraction(str(m)) / 2
                self.assertEqual(Fraction(g.num_text(value)), value)


class Generate(unittest.TestCase):
    def test_deterministic(self):
        a, ra = run(fake())
        b, rb = run(fake())
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(json.dumps(ra, sort_keys=True), json.dumps(rb, sort_keys=True))
        c, _ = run(fake(), seed=8)
        self.assertNotEqual([x["scene"] for x in a], [x["scene"] for x in c])

    def test_examples_are_complete_and_within_limits(self):
        examples, _ = run(fake(), count=40)
        self.assertEqual(len(examples), 40)
        self.assertEqual(len({e["id"] for e in examples}), 40)
        self.assertEqual({e["provenance"]["component"] for e in examples}, set(ALL))
        for e in examples:
            self.assertEqual(e["schema"], g.SCHEMA)
            p = e["provenance"]
            for key in ("source", "authorKind", "licence", "clearance", "generator", "engine", "created",
                        "sceneSha256", "component", "with"):
                self.assertIn(key, p)
            self.assertEqual(p["authorKind"], "program")
            self.assertEqual(p["templateAuthor"], g.TEMPLATE_AUTHOR)
            self.assertEqual(e["check"]["engineVerified"], sorted(e["check"]["ratios"].keys() & set(e["check"]["engineVerified"])))
            self.assertEqual(p["clearance"], "pending-owner")
            self.assertEqual(len(p["engine"]["checkerSha256"]), 64)
            self.assertTrue(e["check"]["ok"])
            doc = json.loads(e["scene"])
            self.assertLessEqual(len(doc["title"]), g.TITLE_MAX)
            self.assertTrue(all(len(s["say"]) <= g.SAY_MAX for s in doc["steps"]))
            self.assertEqual(doc["parts"][0]["with"], p["with"])
            self.assertLess(len(e["scene"].encode()), 64 * 1024)

    def test_stated_ratio_matches_solved_ratio(self):
        examples, _ = run(fake(), count=8, components=["spurPair"])
        for e in examples:
            w = e["provenance"]["with"]
            p, wt = w["pinionTeeth"], w["wheelTeeth"]
            self.assertIn(f"turns {g.ratio_text(p, wt)} of a turn", e["scene"])
            self.assertTrue(g.ratio_text(p, wt).endswith(g.frac_text(Fraction(p, wt))))
            self.assertAlmostEqual(e["check"]["ratios"]["gears.wheel"], -p / wt, places=12)

    def test_derived_numbers_are_right_and_stated(self):
        examples, _ = run(fake(), count=60)
        for e in examples:
            w, d, scene = e["provenance"]["with"], e["check"]["derived"], e["scene"]
            comp = e["provenance"]["component"]
            for text in d.values():
                self.assertIn(text, scene)
            if comp == "spurPair":
                m = Fraction(str(w["module"]))
                self.assertEqual(Fraction(d["centreDistanceMM"]), (w["pinionTeeth"] + w["wheelTeeth"]) * m / 2)
                self.assertIn(f"= {d['centreDistanceMM']} mm", scene)
            elif comp == "planetaryStage":
                self.assertEqual(int(d["ringTeeth"]), w["sunTeeth"] + 2 * w["planetTeeth"])
            elif comp == "sliderCrank":
                self.assertEqual(int(d["strokeMM"]), 2 * w["radius"])
            elif comp == "propeller":
                root, tip = int(d["rootAngleDeg"]), int(d["tipAngleDeg"])
                self.assertEqual(root, -w["pitch"])
                self.assertGreater(root, tip)
                self.assertGreater(tip, 0)

    def test_engine_refusal_is_recorded_not_emitted(self):
        examples, rejects = run(fake(), count=20, components=["planetaryStage"])
        self.assertTrue(rejects, "seed 7 should sample at least one spacing refusal")
        for r in rejects:
            self.assertEqual(r["schema"], g.REJECT_SCHEMA)
            self.assertEqual(r["reason"], "component.check.spacing")
        for e in examples:
            w = e["provenance"]["with"]
            self.assertEqual((2 * w["sunTeeth"] + 2 * w["planetTeeth"]) % w["planets"], 0)

    def test_ratio_mismatch_is_rejected(self):
        examples, rejects = run(fake("wrong"), count=3)
        self.assertEqual(examples, [])
        self.assertIn("generator.ratioMismatch", {r["reason"] for r in rejects})

    def test_bad_engine_output_is_rejected(self):
        for mode, reason in (("garbage", "engine.output"), ("exit", "engine.exit")):
            examples, rejects = run(fake(mode), count=2, components=["spurPair"])
            self.assertEqual(examples, [])
            self.assertEqual({r["reason"] for r in rejects}, {reason})

    def test_timeout_is_rejected(self):
        engine = g.Engine([sys.executable, FAKE, "--mode=sleep"], FAKE, timeout=1)
        try:
            self.assertEqual(engine.check("{}")["reason"], "engine.timeout")
        finally:
            engine.close()


def wrapper(folder, mode="ok"):
    """An executable stand-in for the marty-solid binary, for CLI tests."""
    path = os.path.join(folder, "marty-solid")
    with open(path, "w") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" --mode={mode} "$@"\n')
    os.chmod(path, 0o755)
    return path


class CLI(unittest.TestCase):
    def cli_error(self, args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            g.main(args)
        self.assertEqual(cm.exception.code, 2)
        return err.getvalue()

    def base(self, d):
        return ["--engine", wrapper(d), "--engine-commit", "76104dea", "--count", "4", "--seed", "3",
                "--created", "2026-11-06"]

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            out, rej = os.path.join(d, "ex.jsonl"), os.path.join(d, "rej.jsonl")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(g.main(self.base(d) + ["--out", out, "--rejects", rej]), 0)
            with open(out, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f]
            self.assertEqual(len(rows), 4)
            gen = rows[0]["provenance"]["generator"]
            self.assertEqual(len(gen["sha256"]), 64)
            self.assertIn("dirty", gen)

    def test_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.jsonl")
            open(out, "w").close()
            self.assertIn("refusing to overwrite", self.cli_error(self.base(d) + ["--out", out]))

    def test_checks_paths_before_running(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.jsonl")
            self.assertIn("must be different", self.cli_error(self.base(d) + ["--out", out, "--rejects", out]))
            missing = os.path.join(d, "nope", "x.jsonl")
            self.assertIn("does not exist", self.cli_error(self.base(d) + ["--out", missing]))

    def test_bad_date(self):
        with tempfile.TemporaryDirectory() as d:
            args = self.base(d) + ["--out", os.path.join(d, "x.jsonl"), "--created", "2026-02-30"]
            self.assertIn("--created", self.cli_error(args))


@unittest.skipUnless(os.environ.get("MARTY_SOLID") and os.environ.get("MARTY_SOLID_COMMIT"),
                     "set MARTY_SOLID and MARTY_SOLID_COMMIT to run against the real engine")
class RealEngine(unittest.TestCase):
    def test_real_engine_accepts_every_emitted_scene(self):
        binary, commit = os.environ["MARTY_SOLID"], os.environ["MARTY_SOLID_COMMIT"]
        with tempfile.TemporaryDirectory() as d:
            out, rej = os.path.join(d, "ex.jsonl"), os.path.join(d, "rej.jsonl")
            code = g.main(["--engine", binary, "--engine-commit", commit, "--count", "24", "--seed", "1",
                           "--out", out, "--rejects", rej, "--created", "2026-11-06"])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as f:
                examples = [json.loads(line) for line in f]
            with open(rej, encoding="utf-8") as f:
                rejects = [json.loads(line) for line in f]
        self.assertEqual(len(examples), 24)
        self.assertEqual({e["provenance"]["component"] for e in examples}, set(ALL))
        # Rejects are engine refusals with stable reasons, never generator text/ratio bugs.
        for r in rejects:
            self.assertNotIn(r["reason"], ("generator.ratioMismatch", "engine.output", "engine.exit",
                                           "engine.timeout"), r)
        # Re-check every emitted scene in a fresh engine: same verdict, same ratios.
        engine = g.Engine([binary], binary)
        try:
            for e in examples:
                report = engine.check(e["scene"])
                self.assertTrue(report["ok"], (e["id"], report.get("reason")))
                self.assertEqual(report["ratios"], e["check"]["ratios"])
        finally:
            engine.close()


if __name__ == "__main__":
    unittest.main()
