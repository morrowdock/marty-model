# SPDX-License-Identifier: Apache-2.0
"""Tests for stage1/make_data.py and stage1/harness.py (fake engine, fake models)."""

import json
import os
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, os.path.join(HERE, "..", "stage1"))

import generate_components as gc  # noqa: E402
import generate_repairs as gr  # noqa: E402
import harness  # noqa: E402
import make_data as md  # noqa: E402

FAKE = os.path.join(HERE, "fake_engine.py")


def fake():
    return gc.Engine([sys.executable, FAKE, "--mode=ok"], FAKE)


def build(n=40, split="train", seed=1, seen=None):
    engine = fake()
    try:
        catalog = gr.load_catalog(engine)
        return md.build(engine, catalog, n, seed, split, "2026-11-07", "76104dea", None,
                        set() if seen is None else seen)
    finally:
        engine.close()


PROSE_WORDS = ("the ", "gear ", "turns", "Checked", "learner", "Show", "How", "Why")


class MakeData(unittest.TestCase):
    def test_rows_are_prose_free_chat_pairs(self):
        rows, metas = build(60)
        self.assertEqual(len(rows), 60)
        self.assertEqual({m["task"] for m in metas}, {"author.ratio", "author.params", "repair"})
        for row, meta in zip(rows, metas):
            self.assertEqual([m["role"] for m in row["messages"]], ["user", "assistant"])
            user, target = row["messages"][0]["content"], row["messages"][1]["content"]
            for word in PROSE_WORDS:
                self.assertNotIn(word, user)
                self.assertNotIn(word, target)
            doc = json.loads(target)
            self.assertNotIn("steps", doc)
            self.assertEqual(doc["title"], meta["component"])
            self.assertEqual(doc["parts"][0]["with"], meta["with"])
            self.assertFalse(meta["provenance"]["prose"])
            self.assertEqual(meta["provenance"]["clearance"], "cleared-stage1-local")
            self.assertEqual(meta["provenance"]["sceneSha256"], md.sha(target))
            self.assertTrue(user.startswith("task: author\n") or user.startswith("task: repair\n"))

    def test_task_mix_follows_the_weights(self):
        _, metas = build(120)
        counts = {}
        for m in metas:
            counts[m["task"]] = counts.get(m["task"], 0) + 1
        # Weights 6 : 2 : 4 (ratio : params : repair) of 12; allow sampling noise.
        self.assertGreater(counts["author.ratio"], 120 * 6 / 12 * 0.6)
        self.assertGreater(counts["repair"], 120 * 4 / 12 * 0.6)
        planetary = sum(1 for m in metas if m["task"] == "author.ratio" and m["component"] == "planetaryStage")
        spur = sum(1 for m in metas if m["task"] == "author.ratio" and m["component"] == "spurPair")
        self.assertLess(abs(planetary - spur), max(planetary, spur))  # same weight: neither dominates

    def test_ratio_targets_match_the_parameters(self):
        rows, metas = build(60)
        for row, meta in zip(rows, metas):
            if meta["task"] != "author.ratio":
                continue
            w = meta["with"]
            ratio = Fraction(*meta["want"]["ratio"])
            if meta["component"] == "spurPair":
                self.assertEqual(ratio, -Fraction(w["pinionTeeth"], w["wheelTeeth"]))
            else:
                self.assertEqual(ratio, Fraction(w["sunTeeth"], 2 * w["sunTeeth"] + 2 * w["planetTeeth"]))
            self.assertIn(f": {gc.frac_text(ratio)}\n", row["messages"][0]["content"])

    def test_repair_rows_carry_the_engine_reason(self):
        rows, metas = build(60)
        repairs = [(r, m) for r, m in zip(rows, metas) if m["task"] == "repair"]
        self.assertTrue(repairs)
        for row, meta in repairs:
            user = row["messages"][0]["content"]
            self.assertIn(f"reason: {meta['want']['reason']}\n", user)
            self.assertIn(meta["want"]["mutation"], md.REPAIR_MUTATIONS)
            refused = user.split("scene: ", 1)[1]
            self.assertNotEqual(refused, row["messages"][1]["content"])

    def test_splits_are_disjoint_and_deterministic(self):
        seen = set()
        train, _ = build(40, "train", seen=seen)
        dev, _ = build(20, "dev", seen=seen)
        targets = lambda rows: {r["messages"][1]["content"] for r in rows}  # noqa: E731
        self.assertFalse(targets(train) & targets(dev))
        again, _ = build(40, "train")
        self.assertEqual(train, again)

    def test_cli_writes_all_files_and_refuses_a_used_folder(self):
        with tempfile.TemporaryDirectory() as d:
            exe = os.path.join(d, "marty-solid")
            with open(exe, "w") as f:
                f.write(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" --mode=ok "$@"\n')
            os.chmod(exe, 0o755)
            out = os.path.join(d, "data")
            args = ["--engine", exe, "--engine-commit", "76104dea", "--out-dir", out, "--seed", "1",
                    "--train", "12", "--valid", "4", "--dev", "4", "--created", "2026-11-07"]
            import contextlib
            import io
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(md.main(args), 0)
            self.assertEqual(sorted(os.listdir(out)), sorted(
                ["SUMMARY.json"] + [s + x for s in ("train", "valid", "dev") for x in (".jsonl", ".meta.jsonl")]))
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                md.main(args)


def scene_for(meta, values=None):
    return md.scene(meta["component"], values if values is not None else meta["with"])


class Harness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.metas = build(40, "dev")

    def setUp(self):
        self.engine = fake()

    def tearDown(self):
        self.engine.close()

    def first(self, task, component=None):
        for row, meta in zip(self.rows, self.metas):
            if meta["task"] == task and (component is None or meta["component"] == component):
                return row["messages"][0]["content"], meta
        self.skipTest(f"no {task} item in this sample")

    def test_clean(self):
        self.assertEqual(harness.clean('<think>x</think>\n```json\n{"a":1}\n```\n'), '{"a":1}')
        self.assertEqual(harness.clean('  {"a":1}  '), '{"a":1}')

    def test_correct_first_try(self):
        user, meta = self.first("author.ratio", "spurPair")
        gen = lambda u: (scene_for(meta), {"seconds": 1.0, "outputTokens": 50, "peakMemoryGB": 2.0})  # noqa: E731
        r = harness.evaluate_item(meta, user, gen, self.engine.check)
        self.assertTrue(r["acceptedFirst"] and r["accepted"] and r["correct"])
        self.assertEqual(r["repairs"], 0)

    def test_other_valid_answer_with_same_ratio_is_correct(self):
        meta = {"id": "x", "task": "author.ratio", "component": "spurPair",
                "with": {"pinionTeeth": 12, "wheelTeeth": 36, "module": 2, "width": 10},
                "want": {"part": "gears.wheel", "ratio": [-1, 3]}}
        other = {"pinionTeeth": 13, "wheelTeeth": 39, "module": 2, "width": 10}  # also 1/3
        gen = lambda u: (scene_for(meta, other), {"seconds": 1.0})  # noqa: E731
        self.assertTrue(harness.evaluate_item(meta, "u", gen, self.engine.check)["correct"])
        wrong_module = dict(other, module=3)  # right ratio, but a fixed value changed
        gen = lambda u: (scene_for(meta, wrong_module), {"seconds": 1.0})  # noqa: E731
        self.assertFalse(harness.evaluate_item(meta, "u", gen, self.engine.check)["correct"])

    def test_repair_loop_uses_the_engine_reason(self):
        user, meta = self.first("author.params")
        bad = dict(meta["with"])
        name = sorted(bad)[0]
        bad[name] = 10_000  # out of range
        prompts = []

        def gen(u):
            prompts.append(u)
            return (scene_for(meta, bad) if len(prompts) == 1 else scene_for(meta)), {"seconds": 0.5}
        r = harness.evaluate_item(meta, user, gen, self.engine.check)
        self.assertFalse(r["acceptedFirst"])
        self.assertTrue(r["accepted"] and r["correct"])
        self.assertEqual(r["repairs"], 1)
        self.assertTrue(prompts[1].startswith(f"task: repair\nreason: component.param.range.{name}\n"))
        self.assertEqual(prompts[1], md.repair_user(f"component.param.range.{name}", meta["component"] and
                                                    md.IID[meta["component"]], scene_for(meta, bad)))

    def test_gives_up_after_three_repairs(self):
        user, meta = self.first("repair")
        gen = lambda u: ("not json", {"seconds": 0.1})  # noqa: E731
        r = harness.evaluate_item(meta, user, gen, self.engine.check)
        self.assertFalse(r["accepted"] or r["correct"])
        self.assertEqual(len(r["attempts"]), 4)

    def test_accepted_but_wrong_values_is_not_correct(self):
        user, meta = self.first("author.params")
        w = dict(meta["with"])
        name = sorted(w)[0]
        w[name] = w[name] + 1
        gen = lambda u: (scene_for(meta, w), {"seconds": 0.1})  # noqa: E731
        r = harness.evaluate_item(meta, user, gen, self.engine.check)
        if r["accepted"]:
            self.assertFalse(r["correct"])

    def test_summary(self):
        user, meta = self.first("author.ratio")
        good = harness.evaluate_item(meta, user, lambda u: (scene_for(meta), {"seconds": 2.0, "outputTokens": 40}),
                                     self.engine.check)
        bad = harness.evaluate_item(meta, user, lambda u: ("x", {"seconds": 1.0, "outputTokens": 1}),
                                    self.engine.check)
        s = harness.summarize([good, dict(bad, id="other")])["all"]
        self.assertEqual((s["n"], s["acceptedFirst"], s["acceptedWithin3"], s["correct"]), (2, 1, 1, 1))


class RepairFixes(unittest.TestCase):
    def test_integer_mutation_stays_in_range_at_the_maximum(self):
        spec = {"pinionTeeth": {"min": 12, "max": 100, "integer": True}}
        doc = {"parts": [{"id": "gears", "use": "spurPair", "with": {"pinionTeeth": 100}}]}
        import random
        mutated, reason = gr.m_integer(doc, spec, random.Random(0))
        self.assertEqual(mutated["parts"][0]["with"]["pinionTeeth"], 99.5)
        self.assertEqual(reason, "component.param.integer.pinionTeeth")

    def write_rows(self, folder, rows):
        path = os.path.join(folder, "ex.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        return path

    def test_read_examples_checks_hash_and_duplicate_ids(self):
        engine = fake()
        try:
            rows, _ = gc.generate(engine, 2, 1, ["spurPair"], "2026-11-07", "76104dea")
        finally:
            engine.close()
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(len(gr.read_examples(self.write_rows(d, rows), "76104dea")), 2)
        with tempfile.TemporaryDirectory() as d:
            bad = json.loads(json.dumps(rows[0]))
            bad["scene"] = bad["scene"].replace("gears", "gearz")
            with self.assertRaisesRegex(ValueError, "sceneSha256"):
                gr.read_examples(self.write_rows(d, [bad]), "76104dea")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "duplicate id"):
                gr.read_examples(self.write_rows(d, [rows[0], rows[0]]), "76104dea")
        with tempfile.TemporaryDirectory() as d:
            bad = json.loads(json.dumps(rows[0]))
            del bad["provenance"]["templateAuthor"]
            with self.assertRaises(ValueError):
                gr.read_examples(self.write_rows(d, [bad]), "76104dea")


if __name__ == "__main__":
    unittest.main()
