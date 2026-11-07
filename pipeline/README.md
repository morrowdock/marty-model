# Data pipeline (reference)

`generate_components.py` makes engine-checked examples from the MartyGraphics built-in
solid components. It calls no AI model and uses only the Python standard library.

**Status:** design reference. Its sentence templates were written by an AI agent, so
by the owner's decision of 2026-11-07 its output is **never training data**: every
example carries `"clearance": "excluded"` and `templateAuthor` (see
[DATA.md](../DATA.md) §0). Human-written templates
([docs/TEMPLATE-SLOTS.md](../docs/TEMPLATE-SLOTS.md)) will replace them.

## What it does

1. Samples parameters for one of four built-in components (`spurPair`,
   `planetaryStage`, `sliderCrank`, `propeller`) from a seeded random generator.
2. Writes a learner question, a title and teaching steps from fixed templates. Every
   number in the text comes from the parameters by exact arithmetic (fractions and
   exact decimals). The one rounded number is a speed factor's decimal, always written
   after the exact fraction and marked "≈" (for example `18/7 ≈ 2.571`). The last step
   says what the engine checked and what it did not model.
3. Runs `marty-solid check` on the scene.
4. Keeps the example only when the engine accepts it **and** each ratio that the text
   states equals the ratio the engine solved (within 1e-9). Otherwise the scene goes
   to the rejects file with the engine's stable reason (for example
   `component.check.spacing`) or `generator.ratioMismatch`.

Which numbers the engine checks: the gear ratios (spur wheel, planetary carrier) are
engine-solved and compared (`check.engineVerified`). Other stated numbers (centre
distance, ring teeth, speed factor, stroke, blade angles) are exact arithmetic on the
parameters; the engine does not report them, so each example lists them in
`check.derived`. For the slider-crank and the propeller only the input drive is
engine-solved. `generator.dirty` is true when the script file differs from the git
commit; the script's SHA-256 is recorded either way.

Same arguments and seed give the same bytes. Output files are never overwritten.

## Run

The engine binary comes from MartyGraphics `Examples/Solid3D` (`swift build -c
release`). The pipeline is pinned to MartyGraphics `d5f42c2` (public PR #30) and runs
`check --strict` by default (`--no-strict` for an older checker). From `d5f42c2` every
report carries `engine` (version, report format and `executableSHA256`); the scripts
refuse a report whose `executableSHA256` is not the hash of the binary they ran
(`engine.identity`) and record the identity in provenance. The engine does not know its
git commit, so `--engine-commit` still records it.

```sh
mkdir -p out
python3 pipeline/generate_components.py --engine PATH/marty-solid --engine-commit d5f42c2e6124487d53f046171526d26d2128330d \
  --count 40 --seed 1 --created 2026-11-06 --out out/examples.jsonl --rejects out/rejects.jsonl
```

It prints a summary to stderr, for example
`{"checkerSha256": "7b5a…", "examples": 40, "rejectReasons": {"component.check.spacing": 6, …}, "rejects": 13}`.
Give `--created` for byte-identical output (the default is today's date).

## Record format (`marty-model.example/0`)

One JSON object per line:

| Field | Meaning |
| --- | --- |
| `id` | `cmp-s<seed>-<n>` |
| `task` | `author.solid` |
| `question` | the learner question (input) |
| `scene` | the scene JSON text (target), compact, one `use` entry plus steps |
| `provenance` | `source`, `authorKind` (`program`), `licence`, `clearance` (`excluded`), `clearanceReason`, `templateAuthor`, `component`, `with`, `generator` (name, version, seed, script `sha256`, git `commit`, `dirty`), `engine` (commit, `checkerSha256`), `created`, `sceneSha256` |
| `check` | `command`, `ok`, `reason`, `ratios`, `parts`, `triangles` from the engine; `engineVerified` (ratios compared with the text); `derived` (other stated numbers, exact arithmetic) |

Rejects (`marty-model.reject/0`) keep `component`, `with`, `scene`, `reason`, `part`
(and the exit code and start of stderr for engine faults).
They are raw material for later rule-based repair examples (refused scene + reason →
fixed scene with new parameters); the mutation repairs below do not use them.

## Repair examples (`generate_repairs.py`)

Makes `repair.solid` examples from accepted `author.solid` examples by **mutation**.
It calls no AI model and writes no new text: the refused scene is the original with
one known mistake, and the target is the original accepted scene (a full corrected
scene, as v0.1 needs; patches come later).

| Mutation | Mistake | Engine reason |
| --- | --- | --- |
| `param.rangeHigh` / `param.rangeLow` | a parameter one above its maximum / one below its minimum | `component.param.range.<name>` |
| `param.integer` | a whole-number parameter + 0.5 | `component.param.integer.<name>` |
| `param.valueText` | a number written as text (`"24"`) | `component.param.value.<name>` |
| `param.typo` | last letter of a parameter name dropped | `component.param.unknown.<typo>` |
| `param.outsideWith` | a parameter written beside `use` instead of in `with` | `component.use.unknown.<name>` |
| `component.typo` | an `s` added to the component id | `component.unknown.<typo>` |
| `ref.anchorTypo` | an `s` added to a highlighted id (`gears.inputs`) | `ref.unknown.<ref>` |
| `text.titleLong` | the title repeated past 80 characters | `assembly.title` |
| `text.sayLong` | one step repeated past 240 characters | `step.say` |

A pair is kept only when the engine refuses the mutated scene with **exactly** the
reason in the table and still accepts the original with the same ratios. Otherwise it
goes to the rejects file (`repair.mutationAccepted`, `repair.unexpectedReason`,
`repair.targetChanged`, `repair.componentNotInCatalog`). An unexpected reason, a changed
target, a component missing from the catalog, or no repairs at all makes the run exit 1. Parameter ranges come from `marty-solid components` (the engine's catalog). Input
examples must carry exactly the `--engine-commit` string given here (same spelling, short
or full) and a matching `sceneSha256`; ids must be unique; input files are bounded (256 MiB, 128 KiB
per line, 200,000 examples).

```sh
python3 pipeline/generate_repairs.py --engine PATH/marty-solid --engine-commit d5f42c2e6124487d53f046171526d26d2128330d \
  --examples out/examples.jsonl --seed 1 --per-example 2 --created 2026-11-06 --out out/repairs.jsonl
```

Each record has `question`, `refused` (scene text), `reason` and `part` (from the
engine) as input, and `scene` (the original) as target. `provenance` adds `mutation`,
`fromExample`, `fromSceneSha256` and `refusedSha256`, and inherits `clearance`,
`clearanceReason` and `templateAuthor` from the source example.

## Tests

```sh
python3 -m unittest discover -s tests                     # fake engine only
MARTY_SOLID=PATH/marty-solid MARTY_SOLID_COMMIT=d5f42c2e6124487d53f046171526d26d2128330d \
  python3 -m unittest discover -s tests                   # adds the real-engine test
```
