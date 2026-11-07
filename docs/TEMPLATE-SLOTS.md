# Template slots for human-written sentences

Status: request to the owner, 2026-11-07. **This file contains no sentences on
purpose.** The owner decided that no text written by an AI company's model goes into
training data. The sentence templates in `pipeline/generate_components.py` were
written by an AI agent, so a person must write new ones. This file lists each slot:
what it is for, where it appears, its limits and the placeholders it may use.

## How to deliver

Write the sentences yourself (or have another person write them), then either:

* commit `pipeline/templates/human-v1.json` with a DCO sign-off, in the format at the
  end of this file, or
* put the sentences in a dated entry in the coordinator's `ACTIVE-BACKLOG.md` (the
  shared work queue outside this repository), addressed to the Marty model thread. The thread copies them into that file **unchanged** and records you as the
  author.

Please say who wrote them (a name or handle for provenance). The thread does not edit,
complete or "improve" your sentences; if one fails a limit below, the thread tells you
which one and why.

## Rules for every slot

* Plain, simple English for learners (short sentences, one idea each).
* State only numbers given by placeholders. Do not type a number yourself (the
  generator computes every number exactly, and the engine checks the gear ratios).
* Do not claim checks that the engine does not make. What the engine checks: shapes
  (closed meshes), joints, tooth meshing, the solved gear ratios, and the crank-rod
  motion. For the propeller it checks only closed shapes and joints. What it does
  **not** check: strength, friction, losses, wear, air flow and thrust. The "honesty"
  slots say this in the writer's own words.
* No brand names, no people, no mention of AI.
* A title: at most 80 characters after the placeholders are filled. A step: at most
  240 characters. Keep a step to one or two sentences.
* Placeholders are written in braces, exactly as listed, for example `{p}`.
* Where a slot asks for "1 to 3 variants", one is enough; more variants give more
  varied training questions.
* The "Topic" column only names what the slot is about. The "Facts" column lists
  facts the slot must state, in technical shorthand. Neither is wording to copy.

## Spur gear pair (`spurPair`)

Placeholders: `{p}` pinion teeth, `{w}` wheel teeth, `{m}` module in mm,
`{ratio}` the turns ratio as a fraction (for example `16/36 = 4/9`), `{factor}` the
speed reduction factor (for example `9/4 ≈ 2.25`), `{centre}` the centre distance in mm,
`{sum}` the expression `({p} + {w}) × {m} / 2`.

| Slot | Topic | Facts | Placeholders |
| --- | --- | --- | --- |
| `spur.question` (1–3 variants) | learner question | — | `{p}`, `{w}`; optional `{m}` |
| `spur.title` | scene title | — | `{p}`, `{w}` |
| `spur.step1` | parts shown | equal module | `{p}`, `{w}`, `{m}` |
| `spur.step2` | input part | — | `{p}` |
| `spur.step3` | output part | output direction: opposite | `{ratio}` |
| `spur.step4` | result | speed factor; centre distance formula | `{factor}`, `{sum}`, `{centre}` |
| `spur.honesty` | limits of the check | see the rules above | none |

## Planetary gear stage (`planetaryStage`)

Placeholders: `{s}` sun teeth, `{pl}` planet teeth, `{n}` number of planets, `{r}` ring
teeth, `{carrier}` carrier turns per sun turn as a fraction, `{factor}` the speed
reduction factor.

| Slot | Topic | Facts | Placeholders |
| --- | --- | --- | --- |
| `planetary.question` (1–3 variants) | learner question | — | `{s}`; optional `{pl}`, `{n}` |
| `planetary.title` | scene title | — | `{s}`, `{n}`, `{r}` |
| `planetary.step1` | parts shown | ring held fixed | `{n}`, `{s}`, `{r}` |
| `planetary.step2` | input part | input: sun | none |
| `planetary.step3` | planets | ring teeth = sun teeth + 2 × planet teeth | `{pl}`, `{s}`, `{r}` |
| `planetary.step4` | output part | output: carrier; direction: same as input | `{s}`, `{r}`, `{carrier}` |
| `planetary.step5` | result (exploded view) | speed factor | `{factor}` |
| `planetary.honesty` | limits of the check | see the rules above | none |

## Slider-crank (`sliderCrank`)

Placeholders: `{r}` crank radius in mm, `{rod}` connecting rod length in mm, `{stroke}`
piston stroke in mm.

| Slot | Topic | Facts | Placeholders |
| --- | --- | --- | --- |
| `crank.question` (1–3 variants) | learner question | — | `{r}` or `{rod}` |
| `crank.title` | scene title | — | `{r}`, `{rod}` |
| `crank.step1` | purpose of the mechanism | input: rotation; output: linear reciprocation | none |
| `crank.step2` | input part | crank pin path radius | `{r}` |
| `crank.step3` | link part | rod length | `{rod}` |
| `crank.step4` | result | stroke = 2 × crank radius, per crank turn | `{r}`, `{stroke}` |
| `crank.honesty` | limits of the check | see the rules above | none |

## Propeller (`propeller`)

Placeholders: `{n}` number of blades, `{span}` blade length in mm, `{root}` blade angle
at the root in degrees, `{tip}` blade angle at the tip in degrees (always smaller).

| Slot | Topic | Facts | Placeholders |
| --- | --- | --- | --- |
| `propeller.question` (1–3 variants) | learner question | — | `{n}`; optional `{span}` |
| `propeller.title` | scene title | — | `{n}`, `{span}` |
| `propeller.step1` | parts shown | blade count; blade length | `{n}`, `{span}` |
| `propeller.step2` | input part | input: hub | `{n}` |
| `propeller.step3` | blade shape | root angle > tip angle; one cause, in the writer's words | `{root}`, `{tip}` |
| `propeller.honesty` | limits of the check | see the rules above (propeller line) | none |

## Honest refusal (new, for questions the engine cannot show)

Placeholders: `{topic}` what was asked, `{missing}` the missing engine feature,
`{nearest}` the nearest thing the engine can show. Their values come from the
`refusal.topics` list, which a person also writes.

| Slot | Topic | Facts | Placeholders |
| --- | --- | --- | --- |
| `refusal.answer` (1–3 variants) | out-of-scope answer | not supported yet; what is missing; nearest supported scene | `{topic}`, `{missing}`; optional `{nearest}` |
| `refusal.topics` (a list, 5 or more rows) | the placeholder values | one row per kind of question the engine cannot show yet, with `topic`, `missing`, `nearest` | — (short phrases written by a person; the thread may not write this list) |

## File format

```json
{
  "format": "marty-model.templates/1",
  "author": "<name or handle>",
  "written": "YYYY-MM-DD",
  "licence": "Apache-2.0",
  "slots": {
    "spur.question": ["…", "…"],
    "spur.title": "…",
    "spur.step1": "…",
    "refusal.topics": [{"topic": "…", "missing": "…", "nearest": "…"}]
  }
}
```

Every slot listed above needs a value (a list for the slots marked "1–3 variants").
The generator will check each sentence for the limits and placeholders above before it
uses the file, and will record `templateAuthor` as `human.<author>`.
