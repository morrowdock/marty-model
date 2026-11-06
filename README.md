# Marty model

A plan for a small, fast, open model that writes **checked**
[MartyGraphics](https://github.com/morrowdock/martygraphics) scenes and lessons for
learning questions. It must be cheap enough to run on an iPad or a Mac.

**Status: planning.** This repository has no model weights, no training runs and no
training data yet. It holds the plan, the project rules and the card templates. The
data rules and a small reference data generator follow in the next pull requests.

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
| [docs/templates/MODEL-CARD.md](docs/templates/MODEL-CARD.md) | Template for each released model |
| [docs/templates/DATA-CARD.md](docs/templates/DATA-CARD.md) | Template for each released dataset |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute (DCO sign-off, data rules) |
| [SECURITY.md](SECURITY.md) | How to report a vulnerability |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Contributor Covenant 2.1 |

## Rules we keep

* No training run, weight download or paid compute before the owner approves it, with
  costs written down first.
* Every training example passes the engine and carries provenance (source, licence,
  generator, engine commit, checker hash).
* No personal data, no private course content, no credentials.
* We do not train on outputs of a provider whose terms forbid it.
* We never see the sealed evaluation sets. The MartyGraphics coordinator runs them.

## Licence

Apache-2.0. See [LICENSE](LICENSE). Model weights, when they exist, will also carry the
licence terms of their base model; the model card will say which.
