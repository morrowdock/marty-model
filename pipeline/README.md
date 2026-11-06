# Data pipeline (reference)

`generate_components.py` makes engine-checked examples from the MartyGraphics built-in
solid components. It calls no AI model and uses only the Python standard library.

**Status:** design reference. Its output carries `"clearance": "pending-owner"` and is
**not cleared for training** until the owner decides the data-rights questions (the
templates and this script were written by an AI agent; see `DATA.md` when it lands).

## What it does

1. Samples parameters for one of four built-in components (`spurPair`,
   `planetaryStage`, `sliderCrank`, `propeller`) from a seeded random generator.
2. Writes a learner question, a title and teaching steps from fixed templates. Every
   number in the text comes from the parameters by exact arithmetic (fractions, not
   floats), and every step ends with what the engine checked and what it did not model.
3. Runs `marty-solid check` on the scene.
4. Keeps the example only when the engine accepts it **and** each ratio that the text
   states equals the ratio the engine solved (within 1e-9). Otherwise the scene goes
   to the rejects file with the engine's stable reason (for example
   `component.check.spacing`) or `generator.ratioMismatch`.

Same arguments and seed give the same bytes. Output files are never overwritten.

## Run

The engine binary comes from MartyGraphics `Examples/Solid3D` (`swift build -c
release`; run heavy builds through the shared heavy-build gate on the mini).

```sh
python3 pipeline/generate_components.py --engine PATH/marty-solid --engine-commit 76104dea \
  --count 40 --seed 1 --out out/examples.jsonl --rejects out/rejects.jsonl
```

It prints a summary to stderr, for example
`{"examples": 40, "rejects": 13, "rejectReasons": {"component.check.spacing": 6, ...}}`.

## Record format (`marty-model.example/0`)

One JSON object per line:

| Field | Meaning |
| --- | --- |
| `id` | `cmp-s<seed>-<n>` |
| `task` | `author.solid` |
| `question` | the learner question (input) |
| `scene` | the scene JSON text (target), compact, one `use` entry plus steps |
| `provenance` | `source`, `authorKind` (`program`), `licence`, `clearance`, `component`, `with`, `generator` (name, version, seed, commit), `engine` (commit, `checkerSha256`), `created`, `sceneSha256` |
| `check` | `command`, `ok`, `reason`, `ratios`, `parts`, `triangles` from the engine |

Rejects (`marty-model.reject/0`) keep `component`, `with`, `scene`, `reason`, `part`.
They are raw material for repair examples (refused scene + reason → fixed scene).

## Tests

```sh
python3 -m unittest discover -s tests                     # fake engine only
MARTY_SOLID=PATH/marty-solid MARTY_SOLID_COMMIT=76104dea \
  python3 -m unittest discover -s tests                   # adds the real-engine test
```
