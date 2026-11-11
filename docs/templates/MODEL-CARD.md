<!--
Model card template for a Marty model release. Copy this file next to the release,
fill every field, and delete these comments. Write "none" or "not measured" rather
than leaving a field empty. Every number must point to a receipt (file + hash).
-->

# Marty model card: `<name>-<version>`

## Summary

| Field | Value |
| --- | --- |
| Name and version | `<name>-<version>` |
| Release date | `YYYY-MM-DD` |
| Release kind | LoRA adapter / merged weights / quantised file (format, bits) |
| Base model | `<org/model>` at revision `<commit or hash>` |
| Base model licence | `<licence name>` (`<URL>`), checked `YYYY-MM-DD` |
| Licence of this release | `<licence>`; base-model terms that flow down: `<list or none>` |
| Terms that flow down from training data | `<list or none>` (see the data cards) |
| Parameters | total `<n>`; trainable (adapter) `<n>` |
| Context length used in training | `<tokens>` |
| Files and hashes | `<file>`: sha256 `<hash>` (one line per file) |
| Contact | hello@morrowdock.app |

## Intended use

* **What it does:** writes MartyGraphics scene JSON (and short lesson text) for a
  learning question, inside the Marty agent loop, which runs the engine on every
  output.
* **Supported scene kinds:** `<list, for example solid assemblies from the built-in
  components>`
* **Out of scope:** `<list>`. The model must say "not supported" instead of inventing
  a scene for these.
* **Not for:** use without the engine check; safety-critical engineering; medical,
  legal or financial advice; any use that the base-model licence or acceptable-use
  policy forbids.

## Engine contract

* Engine: MartyGraphics commit `<sha>`, checker `<binary name>` sha256 `<hash>`.
* Check command: `marty-solid check FILE.json` (`--strict` when available).
* Repair loop: at most 3 repairs from the engine's stable reason (the Marty default;
  write the number used if it is different).
* An output that the engine refuses is never shown as a checked scene.

## Training

| Field | Value |
| --- | --- |
| Method | LoRA / QLoRA: rank `<r>`, alpha `<a>`, target modules `<list>`, dropout `<d>` |
| Framework and version | `<for example mlx-lm x.y.z>` |
| Hardware | `<device, memory>`; wall time `<h>` |
| Compute cost | `<amount and currency, or local electricity estimate>` |
| Datasets | `<dataset name-version>` (link to its data card), split sizes |
| Data sources by share | programmatic `<%>`, human-authored `<%>`, open-weight model `<%>`, other `<%>` |
| Seeds | `<seeds>` |
| Training config | `<file>` sha256 `<hash>` |

## Evaluation

All numbers come from sealed held-out sets run by the MartyGraphics coordinator. The
model builders never see these sets. Give the set id and hash, not the questions.

| Metric | Result | Target | Set (id, sha256) |
| --- | --- | --- | --- |
| Engine acceptance, first try | | | |
| Engine acceptance within 3 repairs | | ≥ 90% | |
| Mean repairs per accepted scene | | | |
| Mechanics correct (blind grader) | | | |
| Explanation without a critical factual error (blind grader) | | ≥ 95% | |
| Honest refusal on out-of-scope questions | | ≥ 90% | |
| Latency p50 / p95, `<device>` | | p95 < 30 s | |
| Peak memory, `<device>` | | | |

* Graders: `<who or which model; blind to which system wrote the output>`.
* Baselines on the same set: `<models and results>`.
* Receipts: `<path>` sha256 `<hash>`.
* Contamination: can the base model's own training data contain the sealed sets?
  `<no / unknown, and why>`. Did any of our training data come from the sealed sets?
  `<result of the coordinator's overlap check>`.

## Safety and honesty labelling

* Every scene the model writes is labelled with its truth tier (engine-checked numbers
  vs. schematic or illustrative parts). Today the scene title or steps carry this label;
  when the engine reports truth tiers, use the engine's value.
* The model labels parts it did not model ("not modelled") instead of hiding them.
* Known failure modes: `<list, with examples from our development split; never from
  sealed results>`.
* Content filters or refusals: `<what, how tested>`.

## Limitations

`<Plain list. Include: languages tested, scene kinds not covered, known factual
weak spots, device limits.>`

## Data rights statement

`<One paragraph: the sources of the training data and why we have the right to use
each source, with links to the data card and to the provider terms checked, with
dates. Name any open legal question.>`

## Changes from the previous version

`<list or "first release">`
