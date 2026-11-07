# SPDX-License-Identifier: Apache-2.0
"""Tests for pipeline/generate_repairs.py.

Unit tests use tests/fake_engine.py (it implements the format rules the mutations
touch). The integration test runs the real engine only when MARTY_SOLID and
MARTY_SOLID_COMMIT are set; otherwise it skips.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))

import generate_components as gc  # noqa: E402
import generate_repairs as gr  # noqa: E402

FAKE = os.path.join(HERE, "fake_engine.py")


def fake(mode="ok"):
    return gc.Engine([sys.executable, FAKE, f"--mode={mode}"], FAKE)


def examples(count=12, seed=5, commit="76104dea"):
    engine = fake()
    try:
        rows, _ = gc.generate(engine, count, seed, list(gc.RECIPES), "2026-11-06", commit)
    finally:
        engine.close()
    return rows


def run(rows, mode="ok", seed=3, per_example=3):
    engine = fake(mode)
    try:
        catalog = gr.load_catalog(engine)
        return gr.generate(engine, catalog, rows, seed, per_example, "2026-11-06", "76104dea")
    finally:
        engine.close()


class Mutations(unittest.TestCase):
    def test_every_mutation_changes_the_scene_and_names_its_reason(self):
        rows = examples(8)
        engine = fake()
        try:
            catalog = gr.load_catalog(engine)
        finally:
            engine.close()
        import random
        for name, mutate in sorted(gr.MUTATIONS.items()):
            applied = 0
            for row in rows:
                doc = json.loads(row["scene"])
                result = mutate(doc, catalog[row["provenance"]["component"]], random.Random(1))
                if result is None:
                    continue
                applied += 1
                mutated, reason = result
                self.assertNotEqual(gr.compact(mutated), row["scene"], name)
                self.assertRegex(reason, r"^[A-Za-z0-9_.]+$", name)
            self.assertGreater(applied, 0, f"{name} never applied")


class Generate(unittest.TestCase):
    def test_pairs_are_refused_then_fixed(self):
        rows = examples(12)
        repairs, rejects = run(rows)
        self.assertGreater(len(repairs), 20)
        self.assertEqual([r for r in rejects if r["reason"] != "repair.mutationAccepted"], [])
        by_id = {r["id"]: r for r in rows}
        for r in repairs:
            self.assertEqual(r["task"], "repair.solid")
            src = by_id[r["provenance"]["fromExample"]]
            self.assertEqual(r["scene"], src["scene"])  # target = the accepted original
            self.assertEqual(r["question"], src["question"])
            self.assertNotEqual(r["refused"], r["scene"])
            self.assertEqual(r["check"]["refused"]["reason"], r["reason"])
            self.assertTrue(r["check"]["target"]["ok"])
            p = r["provenance"]
            self.assertEqual(p["clearance"], "pending-owner")
            self.assertEqual(p["templateAuthor"], gc.TEMPLATE_AUTHOR)
            self.assertEqual(p["source"], "programmatic.mutation")
            self.assertIn(p["mutation"], gr.MUTATIONS)
            self.assertEqual(p["refusedSha256"], gr.sha(r["refused"]))
            self.assertEqual(p["sceneSha256"], gr.sha(r["scene"]))
        self.assertGreaterEqual(len({r["provenance"]["mutation"] for r in repairs}), 8)

    def test_deterministic(self):
        rows = examples(6)
        a, ra = run(rows)
        b, rb = run(rows)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(json.dumps(ra, sort_keys=True), json.dumps(rb, sort_keys=True))

    def test_mutation_the_engine_accepts_is_dropped(self):
        repairs, rejects = run(examples(3), mode="accept")
        self.assertEqual(repairs, [])
        self.assertEqual({r["reason"] for r in rejects}, {"repair.mutationAccepted"})

    def test_target_must_still_pass_with_same_ratios(self):
        repairs, rejects = run(examples(3), mode="wrong")
        self.assertEqual(repairs, [])
        self.assertEqual({r["reason"] for r in rejects}, {"repair.targetChanged"})


def wrapper(folder):
    path = os.path.join(folder, "marty-solid")
    with open(path, "w") as f:
        f.write(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" --mode=ok "$@"\n')
    os.chmod(path, 0o755)
    return path


class CLI(unittest.TestCase):
    def write_examples(self, folder, rows):
        path = os.path.join(folder, "ex.jsonl")
        gc.write_jsonl(path, rows)
        return path

    def cli_error(self, args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            gr.main(args)
        self.assertEqual(cm.exception.code, 2)
        return err.getvalue()

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            ex = self.write_examples(d, examples(4))
            out = os.path.join(d, "rep.jsonl")
            with contextlib.redirect_stderr(io.StringIO()):
                code = gr.main(["--engine", wrapper(d), "--engine-commit", "76104dea", "--examples", ex,
                                "--seed", "1", "--per-example", "2", "--out", out, "--created", "2026-11-06"])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f]
            self.assertTrue(rows)
            self.assertEqual(len(rows[0]["provenance"]["generator"]["sha256"]), 64)

    def test_refuses_examples_from_another_engine(self):
        with tempfile.TemporaryDirectory() as d:
            ex = self.write_examples(d, examples(2, commit="aaaaaaa"))
            msg = self.cli_error(["--engine", wrapper(d), "--engine-commit", "76104dea", "--examples", ex,
                                  "--seed", "1", "--out", os.path.join(d, "o.jsonl")])
            self.assertIn("checked at engine aaaaaaa", msg)

    def test_refuses_bad_input_lines(self):
        with tempfile.TemporaryDirectory() as d:
            ex = os.path.join(d, "ex.jsonl")
            with open(ex, "w") as f:
                f.write('{"schema": "x"}\n')
            msg = self.cli_error(["--engine", wrapper(d), "--engine-commit", "76104dea", "--examples", ex,
                                  "--seed", "1", "--out", os.path.join(d, "o.jsonl")])
            self.assertIn("ex.jsonl:1", msg)

    def test_refuses_same_file_for_input_and_output(self):
        with tempfile.TemporaryDirectory() as d:
            ex = self.write_examples(d, examples(1))
            msg = self.cli_error(["--engine", wrapper(d), "--engine-commit", "76104dea", "--examples", ex,
                                  "--seed", "1", "--out", ex])
            self.assertIn("different files", msg)


@unittest.skipUnless(os.environ.get("MARTY_SOLID") and os.environ.get("MARTY_SOLID_COMMIT"),
                     "set MARTY_SOLID and MARTY_SOLID_COMMIT to run against the real engine")
class RealEngine(unittest.TestCase):
    def test_real_engine_refuses_each_mutation_with_the_expected_reason(self):
        binary, commit = os.environ["MARTY_SOLID"], os.environ["MARTY_SOLID_COMMIT"]
        engine = gc.Engine([binary], binary)
        try:
            rows, _ = gc.generate(engine, 16, 2, list(gc.RECIPES), "2026-11-06", commit)
            catalog = gr.load_catalog(engine)
            repairs, rejects = gr.generate(engine, catalog, rows, 4, len(gr.MUTATIONS), "2026-11-06", commit)
        finally:
            engine.close()
        # Every applicable mutation gives exactly the stable reason we expect.
        self.assertEqual([r for r in rejects if r["reason"] != "repair.mutationAccepted"], [])
        self.assertEqual(rejects, [])
        self.assertEqual({r["provenance"]["mutation"] for r in repairs}, set(gr.MUTATIONS))


if __name__ == "__main__":
    unittest.main()
