# Marty model

A plan for a small, fast, open model that writes **checked**
[MartyGraphics](https://github.com/morrowdock/martygraphics) scenes and lessons for
learning questions. It must be cheap enough to run on an iPad or a Mac.

**Status: planning.** This repository has no model weights, no training runs and no
training data yet. It holds the plan, the data rules, the project rules, the card
templates and a small reference data generator.

## Real output today: engine-checked examples, no model

The reference generator ([pipeline/README.md](pipeline/README.md)) calls no AI model.
It fills fixed templates from seeded parameters and keeps an example only when
`marty-solid check --strict` accepts the scene **and** every ratio the text states
equals the ratio the engine solved. One run on 2026-11-11, from a checkout of this
repository at `588875f` (main before this release notes change), with `marty-solid`
built from MartyGraphics `d5f42c2` (executable SHA-256 `60e08a95…7be28`):

```sh
python3 pipeline/generate_components.py --engine PATH/marty-solid \
  --engine-commit d5f42c2e6124487d53f046171526d26d2128330d \
  --count 40 --seed 1 --created 2026-11-06 --out out/examples.jsonl --rejects out/rejects.jsonl
```

```json
{"checkerSha256": "60e08a9513892a17ce358183f69d24096cd9e87fed39f3fccba3a0bef5d7be28", "examples": 40,
 "rejectReasons": {"component.check.planetsClear": 2, "component.check.rodLength": 4,
                   "component.check.spacing": 6, "constraint.gearMesh.interference": 1}, "rejects": 13}
```

40 examples were kept (14 spur pairs, 13 propellers, 9 slider-cranks, 4 planetary
stages) and 13 sampled scenes were refused with the engine's stable reason. A second
run gave byte-identical files. Each record names the generator's git commit, so a run
from another commit gives the same examples with a different file hash. One kept example (`cmp-s1-00001`):

| | |
| --- | --- |
| Question | "How does a planetary gear set with a 36-tooth sun and 26-tooth planets reduce speed?" |
| Scene | One `planetaryStage` (sun 36, planets 26 × 4, module 2), six teaching steps |
| Text says | "the carrier turns 36 / (36 + 88) = 9/31 of a turn per sun turn" |
| Engine solved | carrier 0.2903225806… = 9/31 (`engineVerified`: carrier, sun); 7 parts, 75,080 triangles |
| Not engine-checked | ring teeth 88 and speed factor 31/9: exact arithmetic on the parameters (`derived`) |

One refused sample: sun 15, planets 12 × 3, module 1.5 → `constraint.gearMesh.interference`
on `stage.planet1`.

**This output is not training data.** An AI agent wrote the sentence templates, so by
the owner's decision every example carries `"clearance": "excluded"`
([DATA.md](DATA.md) §0). Human-written templates will replace them.

## Why a small model can be enough

MartyGraphics is a deterministic engine. It checks the mechanical constraints in a
scene (gear ratios, centre distances, tooth phase, closed meshes, text limits) and
refuses a wrong scene with a stable reason, for example `constraint.gearMesh.phase`. The
[Marty](https://github.com/morrowdock/marty) agent loop gives that reason back to the
model, and the model repairs the scene. Because the engine is the safety net, the model
only has to be good at authoring. It does not have to be a large general model.

```
learner question ──► Marty model ──► scene JSON ──► MartyGraphics engine
                          ▲                               │
                          └──── stable refusal reason ◄───┘ (repair, at most 3 times)
                                                          │
                                                accepted scene + solved numbers
```

The engine checks geometry and kinematics. It does not check strength, torque or
wear, and it does not check that an explanation is true. So we also measure factual correctness with blind graders.

## Documents

| File | What it holds |
| --- | --- |
| [PLAN.md](PLAN.md) | Model size, base models and licences, fine-tuning, device budgets, evaluation, safety, release plan, costs and the recommended path |
| [DATA.md](DATA.md) | Data rules, owner questions on data rights, sources and provider terms, the pipeline, provenance schema |
| [pipeline/README.md](pipeline/README.md) | Reference generator: engine-checked examples from the built-in components (no model calls) |
| [docs/templates/MODEL-CARD.md](docs/templates/MODEL-CARD.md) | Template for each released model |
| [docs/templates/DATA-CARD.md](docs/templates/DATA-CARD.md) | Template for each released dataset |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute (DCO sign-off, data rules) |
| [SECURITY.md](SECURITY.md) | How to report a vulnerability |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Contributor Covenant 2.1 |
| [CHANGELOG.md](CHANGELOG.md) | Releases |

## Rules we keep

* No training run, weight download or paid compute before the owner approves it, with
  costs written down first.
* Every training example passes the engine and carries provenance (source, licence,
  generator, engine commit, checker hash).
* No personal data, no private course content, no credentials.
* We do not train on outputs of a provider whose terms forbid it.
* We never see the sealed evaluation sets. The MartyGraphics coordinator runs them.

## How it was made

AI agents (mainly Claude Opus 5.5) wrote the plan, the rules and the scripts under the
direction of Collin Craig, through pull requests with independent reviews by other AI
models. The owner made the data and
spending decisions.

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The names Morrowdock and Marty
and the logos are not licensed; see [TRADEMARKS.md](TRADEMARKS.md). Model weights, when they exist, will also carry the
licence terms of their base model; the model card will say which.
