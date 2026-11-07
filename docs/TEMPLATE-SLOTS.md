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
* put the sentences in a dated `ACTIVE-BACKLOG.md` entry addressed to the Marty model
  thread. The thread copies them into that file **unchanged** and records you as the
  author.

Please say who wrote them (a name or handle for provenance). The thread does not edit,
complete or "improve" your sentences; if one fails a limit below, the thread tells you
which one and why.

## Rules for every slot

* Plain, simple English for learners (short sentences, one idea each).
* State only numbers given by placeholders. Do not type a number yourself (the
  generator computes every number exactly, and the engine checks the gear ratios).
* Do not claim checks that the engine does not make. The engine checks shapes, joints,
  tooth meshing, the solved gear ratios and the crank-rod motion. It does **not**
  check strength, friction, losses, wear, air flow or thrust.
* No brand names, no people, no mention of AI.
* A title: at most 80 characters after the placeholders are filled. A step: at most
  240 characters. Keep a step to one or two sentences.
* Placeholders are written in braces, exactly as listed, for example `{p}`.
* Where a slot asks for "1 to 3 variants", one is enough; more variants give more
  varied training questions.

## Spur gear pair (`spurPair`)

Placeholders: `{p}` pinion teeth, `{w}` wheel teeth, `{m}` module in mm,
`{ratio}` the turns ratio written as a fraction (for example `16/36 = 4/9`), `{factor}`
how many times slower the wheel turns (for example `9/4 ≈ 2.25`), `{centre}` the centre
distance in mm, `{sum}` the expression `({p} + {w}) × {m} / 2`.

| Slot | Purpose | Must include |
| --- | --- | --- |
| `spur.question` (1–3 variants) | the learner's question | `{p}` and `{w}`; may include `{m}` |
| `spur.title` | scene title | `{p}` and `{w}` |
| `spur.step1` | what the learner sees: two gears with the same tooth size | `{p}`, `{w}`, `{m}` |
| `spur.step2` | the input: the small gear turns | `{p}` |
| `spur.step3` | the output: how far the big gear turns per input turn, and its direction (opposite) | `{ratio}` |
| `spur.step4` | the speed result and the centre distance | `{factor}`, `{sum}`, `{centre}` |
| `spur.honesty` | what the engine checked and what it did not model | no placeholders |

## Planetary gear stage (`planetaryStage`)

Placeholders: `{s}` sun teeth, `{pl}` planet teeth, `{n}` number of planets, `{r}` ring
teeth (`{s} + 2 × {pl}`), `{carrier}` the carrier turns per sun turn as a fraction,
`{factor}` how many times slower the carrier turns.

| Slot | Purpose | Must include |
| --- | --- | --- |
| `planetary.question` (1–3 variants) | the learner's question | `{s}`; may include `{pl}`, `{n}` |
| `planetary.title` | scene title | `{s}`, `{n}`, `{r}` |
| `planetary.step1` | the parts: planets on a carrier between the sun and a fixed ring | `{n}`, `{s}`, `{r}` |
| `planetary.step2` | the input: the sun turns | none |
| `planetary.step3` | each planet meshes with the sun and rolls in the ring; how the ring tooth count follows | `{pl}`, `{s}`, `{r}` |
| `planetary.step4` | the output: carrier turns per sun turn, same direction | `{s}`, `{r}`, `{carrier}` |
| `planetary.step5` | the speed result (shown exploded) | `{factor}` |
| `planetary.honesty` | what the engine checked and what it did not model | no placeholders |

## Slider-crank (`sliderCrank`)

Placeholders: `{r}` crank radius in mm, `{rod}` connecting rod length in mm, `{stroke}`
piston stroke in mm (`2 × {r}`).

| Slot | Purpose | Must include |
| --- | --- | --- |
| `crank.question` (1–3 variants) | the learner's question | `{r}` or `{rod}` |
| `crank.title` | scene title | `{r}`, `{rod}` |
| `crank.step1` | what the mechanism does: turning motion to straight back-and-forth motion | none |
| `crank.step2` | the input: the crank turns; its pin moves on a circle | `{r}` |
| `crank.step3` | the rod joins the crank pin to the piston | `{rod}` |
| `crank.step4` | the piston stroke per crank turn | `{r}`, `{stroke}` |
| `crank.honesty` | what the engine checked and what it did not model | no placeholders |

## Propeller (`propeller`)

Placeholders: `{n}` number of blades, `{span}` blade length in mm, `{root}` blade angle
at the root in degrees, `{tip}` blade angle at the tip in degrees (always smaller).

| Slot | Purpose | Must include |
| --- | --- | --- |
| `propeller.question` (1–3 variants) | the learner's question | `{n}`; may include `{span}` |
| `propeller.title` | scene title | `{n}`, `{span}` |
| `propeller.step1` | what the learner sees: blades on a hub | `{n}`, `{span}` |
| `propeller.step2` | the input: the hub turns and the blades turn with it | `{n}` |
| `propeller.step3` | the blade is steeper at the root than at the tip; one short reason | `{root}`, `{tip}` |
| `propeller.honesty` | what the engine checked (closed shapes, joints) and what it did not model (air flow, thrust, strength) | no placeholders |

## Honest refusal (new, for questions the engine cannot show)

Placeholders: `{topic}` a short name of what was asked (for example "a bevel gear"),
`{missing}` the missing engine feature, `{nearest}` the nearest thing the engine can
show.

| Slot | Purpose | Must include |
| --- | --- | --- |
| `refusal.answer` (1–3 variants) | say plainly that this cannot be shown yet, name what is missing, offer the nearest supported scene | `{topic}`, `{missing}`; may include `{nearest}` |
| `refusal.topics` (a list, 5 or more rows) | the values for the placeholders: one row per kind of question the engine cannot show yet, each with `topic`, `missing` and `nearest` | short phrases, also written by a person (the thread may not write this list) |

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
