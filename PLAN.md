# Marty model plan

Status: plan, 2026-11-06. No training, no weights downloaded, no paid compute.
Every stage after Stage 0 needs owner approval first (see [Stages and approvals](#stages-and-approvals)).

## 1. Goal and the job the model must do

The Marty model reads a learning question and writes a MartyGraphics scene: compact
JSON (today a solid assembly, usually built from library components with `use`
entries) plus short teaching steps. The Marty agent loop runs the engine
(`marty-solid check`, later `--strict`) on every output. The engine refuses a wrong
scene with a stable reason; the model repairs it, at most 3 times. The model also
says "not supported" for questions the engine cannot show.

So the model needs four skills, in this order of importance:

1. Write valid, compact scene JSON for the current format and component catalog.
2. Repair a refused scene from the engine's reason (a full corrected scene in v0.1; a
   short patch from v0.2).
3. Write short, true explanation steps whose numbers equal the engine's solved numbers,
   and label what is not modelled.
4. Refuse honestly when the question is out of scope.

It does **not** need broad world knowledge, long reasoning or long context. That is
why a small model can be enough.

**Typical sizes.** Measured: a component scene with 4 to 6 steps from the reference
[generator](pipeline/README.md) (engine 76104dea) is 670 to 960 bytes; the component catalog is
about 3.8 KB; a hand-written full scene is 3.7 KB (53 lines). Estimated (no tokenizer
run yet, about 3 bytes per token for JSON): a scene is about 250 to 350 output tokens
and the catalog about 1,200 tokens, which can sit in a cached prompt prefix. Stage 1
measures token counts with the chosen tokenizer.

## 2. Model size options

Approximate 4-bit weight sizes from MLX community builds (see
[licence research](#4-base-model-candidates-and-licences)); add a few hundred MB for
the KV cache and runtime.

| Class | Parameters | 4-bit weights | Runs on | Fit for the job |
| --- | --- | --- | --- | --- |
| Tiny | 0.8–2B | 0.7–1.3 GB | any M-series iPad or Mac | Fast. JSON syntax is learnable; explanations and repairs are weaker. Good as a draft model or fallback. |
| **Small (recommended)** | **3–4B** | **1.8–2.3 GB** | **iPad with 8 GB RAM, M-series Mac with 8 GB+ (to be measured)** | **Best balance: strong enough for repair and short explanations, fits on device.** |
| Medium | 7–9B | 4.5–5.5 GB | Macs with 16 GB+; not a safe iPad target | Better explanations; too big for the iPad budget and for local training on the 8 GB mini. |

Speed is limited by memory bandwidth. The public llama.cpp Apple silicon benchmark
([discussion 4167](https://github.com/ggml-org/llama.cpp/discussions/4167)) measures
a 7B model at 4 bits generating about 14 tokens/s on M1, 22 on M2, 24 on M4 and 50 on
M4 Pro. Our estimate (not measured) for a 3B model is about twice that: about 30
tokens/s on M1, so a 400-token scene takes about 13 s on M1 and about 8 s on M4.
Prompt prefill on a cache miss (about 1,200 prefix tokens) adds seconds on M1. iPad
speed is not measured yet.

## 3. Latency and memory budgets

| Budget | Target | Why |
| --- | --- | --- |
| Model + KV cache, iPad | ≤ 3 GB resident | leaves room for the app, the engine (up to about 200 MB at its mesh limit, peaks about twice that) and the renderer on an 8 GB iPad |
| Model + KV cache, Mac with 8 GB | ≤ 3 GB resident | same as the iPad |
| Model + KV cache, Mac with 16 GB+ | ≤ 6 GB resident | leaves half of a 16 GB Mac free |
| First scene, end to end | p50 ≤ 10 s, p95 ≤ 20 s on M2-class | a learner waits for one answer |
| Accepted scene incl. repairs | p95 ≤ 30 s | the coordinator's eval target |
| Engine check | ≤ 0.2 s | measured: 0.15 s for a 13-part planetary scene on the M1 mini |

How we meet them:

* **Short outputs.** Train on component `use` scenes (about 300 tokens), not on
  hand-built geometry.
* **Repairs as patches (from v0.2).** The engine accepts patches
  (`MGSolidParser.applying`), so a repair can be tens of tokens instead of a full
  scene. v0.1 repairs rewrite the scene (about 300 tokens) until the engine CLI can
  check a patch.
* **Cached prefix.** Format rules and the catalog go in a fixed system prefix whose KV
  cache is reused across questions.
* **Constrained decoding.** A JSON grammar during decoding removes most syntax
  errors, so most engine refusals are about content (truncated or off-schema output
  can still be refused). Both runtimes are reported to support grammar-constrained
  decoding; we confirm this and choose one at Stage 1.
* **No reasoning tokens.** Granite 4.2 and Qwen3.5 can emit "thinking" text. We turn
  it off and train in the non-thinking format, or the latency budget fails.
* **Measure on the device.** Memory and latency numbers in the model card come from
  real runs on named devices, not from estimates like the ones above. On an 8 GB iPad
  the per-app memory limit is below the device RAM; the app probably needs the
  increased-memory-limit entitlement. We measure the real limit with
  `os_proc_available_memory` before we choose the size.
* **Download size.** A 2 GB model is too big to bundle in the app; it needs an
  on-demand download (for example Background Assets).

## 4. Base model candidates and licences

Checked on 2026-11-06 from the official model cards and licence pages. We must check
again at the revision we download, and record the revision hash.

| Family | Sizes in range | Licence | Redistribute fine-tunes | Conditions that flow down | Notes |
| --- | --- | --- | --- | --- | --- |
| [IBM Granite 4.2](https://huggingface.co/ibm-granite/granite-4.2-3b) | 3B, 8B | Apache-2.0 | yes | Apache §4 notices only | dense standard architecture; IBM publishes MLX 4-bit and 8-bit builds; 128K context; released 2026-08-25 |
| [Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-4B) | 0.8B, 2B, 4B, 9B | Apache-2.0 | yes | Apache §4 only | best size spread; hybrid attention and vision encoder: MLX/llama.cpp training support must be checked |
| [Gemma 4](https://ai.google.dev/gemma/docs/gemma_4_license) | E2B (~5B total), E4B (~8B total) | Apache-2.0 | yes | Apache §4 only | built for edge devices, but real size is larger than the name. Gemma 3/3n are under the older [Gemma Terms](https://ai.google.dev/gemma/terms) with a flow-down use policy: do not use those |
| [SmolLM3](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) | 3B | Apache-2.0 | yes | Apache §4 only | open pretraining data mixture |
| [OLMo 3](https://huggingface.co/allenai/Olmo-3-1025-7B) | 7B | Apache-2.0 | yes | Apache §4 only (the card states research and education as intended use; not a licence condition) | fully open data and code; smallest is 7B |
| [Ministral 3](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512) | 3B, 8B | Apache-2.0 | yes | Apache §4 only | includes a vision encoder |
| [Phi-4-mini](https://huggingface.co/microsoft/Phi-4-mini-instruct) | 3.8B | MIT | yes | MIT notice | dated Feb 2025 |
| [Llama 3.2](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE) | 1B, 3B | Llama 3.2 Community License | with conditions | "Built with Llama", name must start with "Llama", [use policy](https://www.llama.com/llama3_2/use-policy) flows down | **avoid**: not a clean fit for an Apache-2.0 project |

Apple's Foundation Models adapter toolkit is **not** a fit: it needs separate
developer terms, an adapter works with one system-model version only, and open
redistribution of adapters is not addressed. Its developer page
([link](https://developer.apple.com/apple-intelligence/foundation-models-adapter/))
also says toolkit 26.0.0 is the last release.

**Pretraining contamination.** No base model's pretraining data can be proven free of
public MartyGraphics text. Per the coordinator, the sealed sets are recent and not
public, so this risk is low; we cannot check it ourselves. The model card will say so.

## 5. Fine-tuning method

**LoRA on a 4-bit base (QLoRA), with [mlx-lm](https://github.com/ml-explore/mlx-lm)
(MIT) on Apple silicon.** mlx-lm trains LoRA, DoRA and full fine-tunes. When the base
is quantised it trains QLoRA automatically, and `mlx_lm.fuse` merges the adapter into
the base model ([LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)).

Starting settings, to be tuned on our development split: rank 16, alpha 32, all
attention and MLP projections, 2 to 3 epochs, learning rate 1e-4 with cosine decay,
loss on the answer tokens only. **Sequence length:** a repair example holds the prefix
(about 1,200 tokens if the catalog is included), the question, the refused scene, the
reason and the corrected scene (v0.1) or patch (v0.2), so 2,048 tokens is
tight. We choose between (a) training without
the catalog in each example, so the model learns the catalog, and (b) 4,096 tokens
with the catalog, at about twice the cost. Stage 1 measures both.

| Option | For | Against |
| --- | --- | --- |
| **Local, mlx-lm on the mini (recommended first)** | no cash cost; data and weights stay on our machine; same software family as on-device inference | the mini is an **M1 with 8 GB RAM and about 23 GB free disk**, shared with other heavy jobs; our estimate is that a 3B QLoRA fits in memory but is slow, and 7B+ does not fit. Rough time estimate: 15,000 examples × 600 tokens (option (a): no catalog in each example) × 3 epochs ≈ 27 M tokens; at 100 to 300 training tokens/s on M1 that is about 1 to 3 days of exclusive heavy-gate time. Stage 1 measures the real rate |
| Cloud GPU (fallback) | fast; any size | costs money; data leaves our machine; needs an account and credentials (owner only) |

Cloud reference prices (secondary sources, check the provider page before any
approval): on-demand H100 about $2.89/h (RunPod Secure Cloud, PCIe; source dated
2026-07-18) to $4.29/h (Lambda, SXM; October 2026)
([Spheron, RunPod](https://www.spheron.network/blog/runpod-h100-pricing-2026/),
[Spheron, Lambda](https://www.spheron.network/blog/lambda-cloud-h100-pricing-2026/),
[IntuitionLabs](https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison)).
A 3–4B LoRA run on about 15,000 short examples is our estimate of 1 to 2 GPU-hours.

## 6. On-device inference

* **Runtime:** MLX Swift on iPad and Mac (same weights format as training), with
  llama.cpp (GGUF) as the fallback. We check both runtimes' licences and grammar
  (constrained decoding) support at Stage 1, before we depend on them.
* **Format:** 4-bit weights, adapter fused. With owner approval, we also publish the
  unfused adapter. Fusing into a 4-bit base and quantising again can lose quality; the
  cleaner path fuses into the bf16 base (one more download of about 6 to 8 GB, part
  of the Stage 2 approval). mlx-lm exports GGUF only for Llama- and
  Mistral-style models, so a llama.cpp fallback for Granite or Qwen3.5 needs
  llama.cpp's own converter; we check this at Stage 1.
* **Integration:** the model is one more backend for the Marty agent loop, behind the
  same tool interface as hosted models. The app chooses the backend; the engine check
  is the same for all.

## 7. Evaluation

**Sealed sets, run by the coordinator.** The MartyGraphics coordinator owns the sealed
held-out sets and runs them with its harness (fresh model per question, public docs
only, at most 3 repairs, everything recorded). This project never sees those
questions or answers. We get only total scores and the receipts' hashes, never
per-item results. **One sealed run per release candidate, and at most three release
candidates per sealed-set version**, so we cannot tune against the sealed sets.
**Overlap check:** blind, as [DATA.md](DATA.md) §4 describes: the
coordinator returns only the number of overlapping distinct items in a dataset
version (at least 1,000 items, fixed and hashed before the check, never built from an
earlier count), never items or a filtered file; if it is above 0 we discard the whole
version; at most 3 checks per sealed-set version. A per-item answer would let us
rebuild the sealed sets, so we do not ask for one.

**Metrics** (the same as the coordinator's existing Prompt→3D runs, so results compare):

| Metric | How | Target for a first release |
| --- | --- | --- |
| Engine acceptance within 3 repairs | engine | ≥ 90% of in-scope questions |
| Acceptance on the first try; mean repairs | engine | report; no target |
| Mechanics correct | blind grader against the solved scene | ≥ the hosted baseline on the same set |
| Explanation without a critical factual error | blind grader | ≥ 95% |
| Stated numbers equal solved numbers | automatic (compare step text to engine ratios) | 100% of accepted scenes |
| Honest refusal on out-of-scope questions | blind grader | ≥ 90% |
| Latency p50 / p95 and peak memory | measured by us on named devices (not part of the sealed run) | §3 budgets |

**Blind graders** see the question, the accepted scene, the engine report and the
explanation, not which system wrote it. The baseline is a hosted small model on the
same set and harness. For reference, the coordinator's published 50-question run with
Claude Haiku 5.5 had all 40 in-scope questions accepted within three repairs, 29 of 40
fully correct in mechanics and 46 of 50 explanations without a critical error
([MartyGraphics README](https://github.com/morrowdock/martygraphics#readme)).

**Our own development split.** For tuning we use only data we generate: held-out
seeds, held-out parameter ranges and, to test generalisation, one whole component held
out of training. These are development sets, not the sealed sets, and never stand in
for them in a release claim. We also measure on it what fine-tuning can damage
(catastrophic forgetting): honest refusals and explanation quality, before and after
training.

## 8. Safety and honesty labelling

* **The engine is the gate.** A scene that the engine refused is never shown as
  checked. The app labels unchecked output.
* **Truth labels.** Every scene says what the engine checked and what it did not model
  (strength, friction, losses, air flow). Our generator writes this as the last step
  today; when the engine reports truth tiers, the scene uses the engine's value.
* **Numbers from the engine.** Training text states only numbers that the engine
  solved or that follow by exact arithmetic from the scene. The automatic number check
  enforces this at evaluation time.
* **Scope.** The model refuses topics the engine cannot show and does not invent
  geometry. Harmful requests (for example weapon mechanisms) are refused; we will ask
  the coordinator to add a small red-team set to the sealed evaluation.
* **Learners.** Many users may be young. No personal data in training. Learner
  corrections only with recorded consent (a parent or guardian for under-18s); see
  [DATA.md](DATA.md).
* **Model card.** Every release lists known failure modes with examples taken from our
  development split (never from sealed results), and the limits of the checks.
* **Engine version.** Each model is tied to one engine commit and format version. A
  format change in MartyGraphics means a new evaluation, and maybe new training.

## 9. Release plan

| Release | Contents | Gate |
| --- | --- | --- |
| v0.0 (now) | plan, data rules, reference generator | reviewed PRs |
| v0.1 research preview | LoRA adapter + fused 4-bit MLX file, model card, data card, training config, all hashes | the coordinator's sealed run meets every quality target in §7; latency and memory are measured by us on the dev split on named Macs (M1 and one newer chip) and meet the §3 Mac budgets; owner approves publishing |
| v0.2 | adds repair-by-patch and compose training, more components | same, plus §3 iPad budgets measured on a named iPad |
| v1.0 | default on-device backend in Marty | learner study and owner decision |

Weights go to a public model host only after owner approval: publishing weights cannot
be undone. Every release file gets a SHA-256 and a Gitleaks scan of the repository.

## 10. Costs

| Stage | Cash | Other |
| --- | --- | --- |
| 0. Plan and data pipeline (now) | $0 | agent time |
| 1. Baseline bake-off (no training) | $0 | install mlx-lm in a project virtual environment; download two 4-bit bases (about 2 to 2.5 GB each); a few hours of mini time in the heavy gate |
| 2. First LoRA runs, local | $0 cash; small electricity cost | estimated 1 to 3 days of exclusive mini time per full run (one heavy job at a time); disk: about 5 GB of bases + 10 GB of checkpoints + 6 to 8 GB for a bf16 base + the virtual environment, against about 23 GB free on a shared machine, so old checkpoints must be deleted or moved |
| 2b. Same, cloud fallback | about $20 to $50 for a bake-off of several 1 to 2 GPU-hour runs, at the prices above | a cloud account and credentials (owner only) |
| 3. Sealed evaluation and grading | uses the coordinator's existing subscription (spending by another party) | coordinator time |
| 4. Release | $0 (public model hosting is free) | owner account on the model host |

## 11. Recommendation (one path)

1. **Base: IBM Granite 4.2 3B** (Apache-2.0, dense standard architecture, official MLX
   builds), with **Qwen3.5-4B** as the only challenger. Pick the winner at Stage 1 on
   our development split, then keep one.
2. **Method: QLoRA with mlx-lm on the mini**, rank 16, loss on answers only. Use cloud
   only if the mini is too slow, with owner approval and a cost cap.
3. **Data: engine-checked programmatic examples plus repair pairs** from the reference
   generator, after the owner decides the data-rights questions in [DATA.md](DATA.md).
4. **Device: 4-bit MLX Swift with constrained JSON decoding**, cached prefix, repairs
   as patches from v0.2.
5. **Gate: the coordinator's sealed sets** with blind grading; publish only when the
   targets in §7 are met.

## Stages and approvals

| Stage | Needs owner approval for |
| --- | --- |
| 0. Plan, data rules, generator | nothing (this repository) |
| 1. Baseline bake-off | installing mlx-lm (MIT) in a virtual environment; downloading two 4-bit base models; mini time |
| 2. Training | starting training runs; downloading the bf16 base for fusing; disk use; cloud spending if used (with a cap) |
| 3. Evaluation | sending model outputs to the coordinator for the sealed run; the coordinator's use of its subscription for grading |
| 4. Release | publishing weights and datasets (cannot be undone) |

The data-rights questions in [DATA.md](DATA.md) must be decided before Stage 2.
