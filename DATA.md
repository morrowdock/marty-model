# Marty model data

Status: design, updated 2026-11-07 with the owner's decisions
([§0](#0-owner-decisions-2026-11-07)). No training dataset is cleared yet.

## 0. Owner decisions (2026-11-07)

1. **No AI-company text in training data.** No text written by a model of an AI
   company (Claude, OpenAI, Google or any other hosted model) goes into training data.
   This includes everything an AI agent wrote in this repository and in MartyGraphics:
   the generator's sentence templates, worked examples, component titles and `about`
   text, and docs.
2. **Allowed sources:** engine-generated examples (component ids, parameter names, part
   ids, refusal reasons, numbers and scene JSON computed by the engine and our programs);
   outputs of open-licence models whose licences allow training; and sentences written
   by a person, starting with the template slots in
   [docs/TEMPLATE-SLOTS.md](docs/TEMPLATE-SLOTS.md). The agent may not draft or
   "neutralise" those sentences; the owner writes or approves human-written ones.
3. **Q1–Q3 are closed.** We do not ask Anthropic or OpenAI for permission; we do not
   use their outputs (or any other AI company's). Q4 and Q5 stay open.
4. **Stage 1 approved:** mlx-lm in an isolated virtual environment, two 4-bit open
   bases (IBM Granite 4.2 3B, Qwen3.5-4B), and a first small local QLoRA comparison on
   engine-generated data only ([PLAN.md](PLAN.md) §5; the `stage1/` harness is planned in
   a separate pull request).

What this means for existing output: examples from `pipeline/generate_components.py`
use AI-written templates, so they now carry `"clearance": "excluded"` and are never
training data. Repair pairs made from them inherit `excluded`. Prose-free Stage 1 data
(planned `stage1/make_data.py`, separate pull request) carries `"prose": false`.

This is not legal advice. Where a question is legal, it is written down for the owner
instead of being decided here.

## 1. Rules

1. **Rights first.** We use a source only when we have a clear right to train on it
   and to publish the result under Apache-2.0.
2. **Engine check.** Every example passes `marty-solid check` (and `--strict` when the
   engine has it). An example that the engine refuses is never a training target. It
   can be the *input* of a repair example.
3. **Numbers from the engine.** Every stated ratio that the engine solves is compared
   with the engine's value. Every other stated number is a value in the scene or exact
   arithmetic on it (never rounded and shown as exact). Each example lists the two
   kinds separately (`check.engineVerified` and `check.derived`).
4. **Provenance on every example** ([§5](#5-provenance-schema)).
5. **No personal data, no private course content, no credentials.**
6. **No evaluation leakage.** We never read the sealed evaluation sets. Before a
   dataset is used, the MartyGraphics coordinator checks it for overlap with them
   using the blind procedure in [§4](#4-pipeline): we learn only a count over a set
   fixed in advance, not which items overlap.

## 2. Questions for the owner

Q1–Q3 were **closed by the owner on 2026-11-07** ([§0](#0-owner-decisions-2026-11-07)):
no AI-company text in training data, no permission requests. The text below is kept as
the record of why the question came up. Q4 and Q5 are still open.

**Q1 (closed 2026-11-07). Text and code written by Claude in this project and in MartyGraphics.**
Most MartyGraphics commits carry `Co-Authored-By: Claude Opus 5.5` (16 of the 23
commits on main at 76104dea), and this repository, including the generator and its
sentence templates, is written by a Claude agent. Anthropic's terms
([§3.1](#31-hosted-ai-providers)) **may** prohibit training an AI model on this text.
The Usage Policy page says "Use outputs to train an AI model … without prior
authorization from Anthropic" is not allowed, but that page shows an effective date of
2026-11-12, after we read it. The Consumer Terms §3 forbid using the Services to
develop competing products, "including to develop or train any artificial intelligence
or machine learning algorithms or models"; whether that covers a small, non-competing
model is a question for the owner. Our working assumption at the time (now settled by
§0):
the template sentences that appear in training text are Claude outputs and are
covered. It is less clear whether scenes that a Claude-written *program* computes
count as outputs.
**Options:**
(a) ask Anthropic for written authorisation for this use;
(b) the owner (a person) writes or rewrites the sentence templates and question
templates, so the training text is human-authored, and gets advice on whether
program-computed scenes are affected;
(c) have the text templates written by an open-weight model whose licence allows it
([§3.3](#33-open-weight-models));
(d) do not train on any of it.
**Superseded 2026-11-07:** the owner chose (b) (a person writes the sentences; see
[docs/TEMPLATE-SLOTS.md](docs/TEMPLATE-SLOTS.md)), with (c) allowed; (a) is not pursued.

**Q2 (closed 2026-11-07). Which Anthropic terms apply to our account?** Which agreement covers the Claude
sessions used so far: a consumer plan (the Consumer Terms name Claude.ai and Claude
Pro; they do not name Max or Claude Code on the page) or the API under the Commercial
Terms (§D.4 (a): no building a competing product, "including to train competing AI
models or resell the Services except as expressly approved by Anthropic"; (b) no
reverse engineering or duplicating the Services; (c) no support for a third party
doing so)? The Usage Policy applies to both.

**Q3 (closed 2026-11-07). OpenAI terms.** Some work across these projects used an OpenAI model through
Codex. openai.com refused our automated fetches (HTTP
403), so we could not read the current terms. One secondary tracker records a clause
against using output "to develop artificial intelligence models that compete with
OpenAI". Please read the terms in a browser. Until then we exclude all
OpenAI-model-written content.

**Q4. Learner corrections (later).** Collecting corrections from learners involves
privacy law (for example rules on children's data) and consent wording. This needs
owner and legal review before any collection starts.

**Q5. Publishing the dataset.** Publishing a dataset cannot be undone. The owner
approves each public dataset release.

## 3. Sources

| | Source | Status | Notes |
| --- | --- | --- | --- |
| A | Programmatic generation from the engine and its built-in components | **allowed**; prose-free today; sentence templates only from a person (docs/TEMPLATE-SLOTS.md); the current AI-written templates are excluded | §4 |
| B | Human-authored examples (a named person, DCO sign-off) | allowed | the owner or contributors; each file marked human-authored |
| B' | Agent-authored examples and text in the MartyGraphics repo and this repo | **excluded** (owner decision 2026-11-07) | §0 |
| C | Outputs of open-weight models with permissive licences | allowed (Stage 1 approved 2026-11-07); not used yet | §3.3 |
| C' | Outputs of hosted APIs, even where their terms allow training | **excluded** (owner decision 2026-11-07: no AI-company text) | §3.1 |
| D | Learner corrections | later, with consent | Q4 |
| X | Sealed evaluation sets, coordinator scratch, private app content | **never** | |

### 3.1 Hosted AI providers

Pages read on 2026-11-06. Quotes are short extracts; read the full page before relying
on them.

| Provider | Document (date shown) | Clause | Our plain reading |
| --- | --- | --- | --- |
| Anthropic | [Consumer Terms](https://www.anthropic.com/legal/consumer-terms) (effective 2025-10-08), §3 | "You may not access or use, or help another person to access or use, our Services" … "To develop any products or services that compete with our Services, including to develop or train any artificial intelligence or machine learning algorithms or models" | about competing use of the Services; the text does not say "outputs"; whether it covers our model is Q1 |
| Anthropic | [Usage Policy](https://www.anthropic.com/legal/aup) (page shows effective 2026-11-12, six days after we read it; the version in force today was not checked) | "Use outputs to train an AI model (e.g., "model scraping" or "model distillation") without prior authorization from Anthropic" | the clearest clause on outputs: not allowed unless Anthropic authorises it; applies to all Anthropic services once in force |
| Anthropic | [Commercial Terms](https://www.anthropic.com/legal/commercial-terms) (effective 2025-06-17), §D.4 | may not "(a) access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic; (b) reverse engineer or duplicate the Services; or (c) support any third party's attempt at any of the conduct restricted in this sentence" | bars competing models; Anthropic may approve exceptions to (a); the Usage Policy still applies |
| Anthropic | Consumer §4, Commercial §B | Anthropic assigns its rights in Outputs, "if any", to the user | ownership of outputs does not remove the use restrictions |
| OpenAI | [Terms of Use](https://openai.com/policies/terms-of-use/), [Business Terms](https://openai.com/policies/business-terms/) | **UNVERIFIED**: every fetch returned HTTP 403 | Q3 |
| Google | [Gemini API Additional Terms](https://aistudio.google.com/docs/terms) (effective 2026-03-23; the old ai.google.dev URL redirects here) | "You may not use the Services to develop models that compete with the Services"; you are responsible for "the use of that content by anyone you share it with" | bars competing models; we do not use Gemini outputs |
| Mistral | [Commercial Terms](https://legal.mistral.ai/terms/commercial-terms-of-service) (effective 2026-09-25), §3.3, §2.2(e) | §3.3: "Customer may not use image Outputs to develop or train any image generation product that competes with a Mistral AI Product"; §2.2(e): no use of Output to reverse engineer Mistral products; §2.2 (last paragraph): pass equivalent restrictions to end users | we found no clause on training with text outputs; not used today |
| DeepSeek | [Open Platform Terms](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html) (effective 2026-04-29), §4.2 | "Subject to your compliance to applicable law and our Terms", permitted uses include "training other models (such as model distillation)" | explicitly allowed by its terms, but excluded by the owner decision of 2026-11-07 (no AI-company text) |

**Downstream readers.** None of the documents we read claims to bind a person who is
not a party to the agreement. They bind the account holder (Anthropic: "help another
person to access or use"; Google: responsibility for "anyone you share it with";
Mistral: pass restrictions on to end users). Because the owner's own account produced
the agent-written MartyGraphics text, we assumed that publishing it under Apache-2.0
does not free *us* from these terms; the owner's decision (§0) now excludes that text
in any case. A third party's
position may differ; that is not our question to decide.

### 3.2 Built-in components and worked examples

The MartyGraphics component catalog, its definitions and worked examples are
Apache-2.0, but they were written by AI agents, so their text is excluded (§0). The reference generator uses
only component **ids and parameter ranges** (facts about the engine's interface) and
the engine's solved numbers. It does not copy component titles, `about` text or
example steps into training text.

### 3.3 Open-weight models

Outputs of models under Apache-2.0 or MIT (for example Granite 4.2, Qwen3.5, Gemma 4,
SmolLM3, OLMo 3, Ministral 3, Phi-4-mini; see [PLAN.md](PLAN.md) §4) carry no output
restriction in those licences. **Avoid** outputs of Llama 3.2 (a model trained on them
must be named "Llama…" and carries Meta's use policy) and Gemma 3/3n (the Gemma Terms
treat models trained on their outputs as derivatives). Local models were
approved for Stage 1 on 2026-11-07 (§0).

## 4. Pipeline

```
 sources ──► normalise ──► engine check ──► number check ──► dedupe ──► overlap check ──► scans ──► split ──► data card ──► clearance
 (A,B,C)    (question,     (marty-solid     (stated ratios   (sha256 +   (coordinator,    (PII,      (train /   (+ hashes)    (owner)
            scene, steps)   check --strict)  = solved)        params)     blind; total)    Gitleaks)  dev)
```

| Step | What | Rejects go to |
| --- | --- | --- |
| Normalise | one record per example: question, scene text (compact JSON), task kind | — |
| Engine check | `marty-solid check` (`--strict` when available), pinned engine commit and checker SHA-256 | rejects file with the stable reason (repair material) |
| Number check | each stated ratio equals the engine's solved ratio within 1e-9 | `generator.ratioMismatch` (a generator bug: fix the template) |
| Dedupe | exact: SHA-256 of the scene; near: same component and parameter bucket | dropped |
| Overlap check | blind procedure below (count only) | a non-zero count discards the whole version |
| Scans | personal-data patterns; Gitleaks on the dataset files | dropped, and the source investigated |
| Split | train / development by seed, plus one held-out parameter range and one held-out component in development | — |
| Data card | [template](docs/templates/DATA-CARD.md), every file hashed | — |
| Clearance | owner sets `clearance` to `cleared` for a dataset version | — |

**Blind overlap check.** Any per-item answer, and any filtered file that comes back,
would show which items are in the sealed sets: our generator is deterministic, so we
could always rebuild the file we sent and compare. So the coordinator never returns
items, only a count:

1. **Fixed before the check.** A version is the full intended training set, made from
   seeds and sources recorded in a commit before its first check. We commit its
   SHA-256 before we send it.
2. **Not adaptive.** No version is built from an earlier count. A retry changes the
   seeds of the whole version; it never adds, removes or repeats chosen items.
3. We give the coordinator the version (at least 1,000 distinct items). The
   coordinator counts **distinct** items that overlap a sealed set under a match rule it
   names (for example exact text, or a near-duplicate threshold) and answers with that
   one number.
4. If the number is 0, we may use that version. If it is above 0, we discard the whole
   version and make a new one with new seeds for the whole version (rule 2), with the
   same source list. We never drop or add a source after a count. If all 3 checks
   (rule 5) return above 0, we stop and report to the owner and the coordinator.
5. **At most 3 checks per sealed-set version**, over all releases.

With these rules each answer is a count over a set fixed in advance, so it gives an
overlap rate and cannot be used to test chosen items. A count still carries a little
information (at most about 14 bits per check for 20,000 items, about 43 bits per
sealed-set version); the coordinator may refuse a check that breaks a rule.

Our programmatic examples are generated from parameters and templates, not from
natural questions, so we expect the count to be 0; a non-zero count is itself a
finding to report to the owner and the coordinator.

### 4.1 Task kinds

| Kind | Input | Target | Source today |
| --- | --- | --- | --- |
| `author.solid` | learner question | scene with teaching steps | reference generator (4 components) |
| `repair.solid` | question, refused scene, engine reason | v0.1: the full corrected scene; v0.2: a patch that the engine accepts | today: [mutation repairs](pipeline/README.md#repair-examples-generate_repairspy) (10 mutations of accepted scenes; target = the original); next: rule-based fixers on the generator's rejects (for example `component.check.spacing` → choose a planet count that divides 2 × (sun + planet)); every target re-checked by the engine |
| `refuse.scope` | out-of-scope question | a short "not supported" answer that names what is missing | next: human-written templates ([docs/TEMPLATE-SLOTS.md](docs/TEMPLATE-SLOTS.md), §0) |
| `compose.solid` | question needing 2+ components | scene with `set`, `parent`, compound trains | later |

Target first mixture for v0.1 (to tune on development data): about 70% author, 20%
repair, 10% refusal; about 10,000 to 20,000 examples in total. In v0.1 a repair target
is the full corrected scene. Repair by patch and compose examples come in v0.2, when the
engine CLI can check a patch (requested from the coordinator), as in
[PLAN.md](PLAN.md) §9.

### 4.2 Reference generator

[`pipeline/generate_components.py`](pipeline/generate_components.py) (see
[pipeline/README.md](pipeline/README.md)) implements the A → engine check
→ number check path for `author.solid` today, with tests. It calls no AI model.

## 5. Provenance schema

Every record carries `provenance`:

| Field | Meaning |
| --- | --- |
| `source` | for example `programmatic.components`, `human.<handle>`, `open-weight.<model>` |
| `authorKind` | `program`, `person`, `open-weight-model` or `learner-correction` |
| `licence` | licence of the example (Apache-2.0 unless stated) |
| `clearance` | `pending-owner`, `cleared` (set only by the owner, per dataset version) or `excluded` (contains AI-company text; never training data) |
| `templateAuthor` | who wrote the sentence templates (for example `ai-agent:claude-opus-5-5` or `human.<handle>`); AI-written templates make an example `excluded` (§0) |
| `clearanceReason` | why an example is `excluded`, for example `ai-written-text` |
| `component`, `with` | component id and parameter values (programmatic) |
| `generator` | name, version, seed, script SHA-256, git commit and a dirty flag (programmatic) |
| `model` | open-weight model id, revision hash, licence URL, sampling settings (open-weight only) |
| `engine` | MartyGraphics commit and checker SHA-256 |
| `created` | date (YYYY-MM-DD) |
| `sceneSha256` | SHA-256 of the scene bytes |
| `consent` | consent record id (learner corrections only; never the person's identity) |

## 6. Learner corrections (later)

Only with opt-in consent recorded per learner (a parent or guardian for under-18s).
We keep the question, the scene and the correction, not names, accounts or free text
about the person. A learner can ask for removal; removal applies to the next dataset
version, and the data card says which released models used the removed items. Waits
on Q4.
