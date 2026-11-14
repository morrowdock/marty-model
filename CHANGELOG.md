# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Require a changelog entry for user-facing pull requests.

## [0.1.0] - 2026-11-11

The first tagged release: a **planning release**. There are no model weights, no training runs and no training
data. Every change is a pull request in the [history of `main`](https://github.com/morrowdock/marty-model/commits/main).

### Added

- **The plan** ([PLAN.md](PLAN.md)): model size, base models and licences, fine-tuning, device budgets, evaluation,
  safety, release steps and costs.
- **The data rules** ([DATA.md](DATA.md)): the owner's decisions of 2026-11-07 (no text from a hosted AI model in
  training data; allowed sources; Stage 1 approved), provenance fields and the pipeline design.
- **A reference generator** ([pipeline/](pipeline/README.md)) that calls no model: engine-checked `author.solid`
  examples from four built-in components, and `repair.solid` examples by mutation. Pinned to MartyGraphics
  `d5f42c2`, `check --strict`, with an engine identity check. The same seed gives the same bytes. Its output is
  marked `"clearance": "excluded"`, because an AI agent wrote its sentence templates.
- **The Stage 1 harness** ([stage1/](stage1/README.md)): prose-free data, bounded QLoRA chunks with mlx-lm and an
  engine evaluation. It is not run in this release.
- Model and data card templates, the template slots for a person to write, the DCO checker, and dispatch-only
  hosted checks.

### Shown with real output

The [README](README.md) shows one generator run with `marty-solid` from `d5f42c2`: 40 examples kept, 13 scenes
refused with the engine's stable reason, byte-identical on a second run.

### Limits

- No model exists yet. Nothing here measures how well a small model can write scenes.
- The engine checks geometry and kinematics, not strength, torque or wear, and not whether an explanation is true.
- Generator output is never training data until human-written templates replace the AI-written ones.

### How it was made

AI agents (mainly Claude Opus 5.5) wrote the plan, the rules and the scripts under the direction of Collin Craig,
through pull requests with independent reviews by other AI models. The owner made the data and spending decisions.
