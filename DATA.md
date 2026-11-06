# Marty model data

Status: design, 2026-11-06. No training dataset exists yet. Nothing here is cleared
for training until the owner decides the questions in
[§2 Questions for the owner](#2-questions-for-the-owner).

This is not legal advice. Where a question is legal, it is written down for the owner
instead of being decided here.

## 1. Rules

1. **Rights first.** We use a source only when we have a clear right to train on it
   and to publish the result under Apache-2.0.
2. **Engine check.** Every example passes `marty-solid check` (and `--strict` when the
   engine has it). An example that the engine refuses is never a training target. It
   can be the *input* of a repair example.
3. **Numbers from the engine.** Every number that example text states is either a
   value in the scene or follows from it by exact arithmetic, and every stated ratio
   equals the ratio the engine solved.
4. **Provenance on every example** ([§5](#5-provenance-schema)).
5. **No personal data, no private course content, no credentials.**
6. **No evaluation leakage.** We never read the sealed evaluation sets. Before a
   dataset is used, the MartyGraphics coordinator checks it for overlap with them,
   removes overlapping items on its side and tells us only the total removed.

## 2. Questions for the owner

These need a decision from the owner, perhaps with a lawyer. Until they are decided,
generated data carries `"clearance": "pending-owner"` and is not used for training.

**Q1. Text and code written by Claude in this project and in MartyGraphics.**
Most MartyGraphics commits carry `Co-Authored-By: Claude Opus 5.5` (16 of the 23
commits on main at 76104dea), and this repository, including the generator and its
sentence templates, is written by a Claude agent. Anthropic's terms
([§3.1](#31-hosted-ai-providers)) prohibit using Claude outputs to develop or train AI
models (the Usage Policy adds "without prior authorization from Anthropic"). Our
reading: the template sentences that appear in training text are Claude outputs. It is
less clear whether scenes that a Claude-written *program* computes count as outputs.
**Options:**
(a) ask Anthropic for written authorisation for this use;
(b) the owner (a person) writes or rewrites the sentence templates and question
templates, so the training text is human-authored, and gets advice on whether
program-computed scenes are affected;
(c) have the text templates written by an open-weight model whose licence allows it
([§3.3](#33-open-weight-models));
(d) do not train on any of it.
**Recommended:** (a) and (b) together. The templates are small (about 40 sentences),
so (b) costs the owner about an hour.

**Q2. Which Anthropic terms apply to our account?** Which agreement covers the Claude
sessions used so far: a consumer plan (the Consumer Terms name Claude.ai and Claude
Pro; they do not name Max or Claude Code on the page) or the API under the Commercial
Terms (which bar only *competing* models)? The Usage Policy applies to both.

**Q3. OpenAI terms.** Some work across these projects used an OpenAI model through
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
| A | Programmatic generation from the engine and its built-in components | **preferred**; reference generator exists; text templates wait on Q1 | §4 |
| B | Human-authored examples (a named person, DCO sign-off) | allowed | the owner or contributors; each file marked human-authored |
| B' | Agent-authored examples in the MartyGraphics repo | **excluded** until Q1 (Claude) and Q3 (OpenAI) are decided | Apache-2.0 on the repo does not remove the account holder's obligations to the provider; see §3.1 |
| C | Outputs of open-weight models with permissive licences | allowed after Stage 1 approval (needs a local model download) | §3.3 |
| C' | Outputs of hosted APIs whose terms allow training | possible, needs owner approval (paid API, credentials, data leaves the machine) | DeepSeek explicitly allows it; §3.1 |
| D | Learner corrections | later, with consent | Q4 |
| X | Sealed evaluation sets, coordinator scratch, private app content | **never** | |

### 3.1 Hosted AI providers

Pages read on 2026-11-06. Quotes are short extracts; read the full page before relying
on them.

| Provider | Document (date shown) | Clause | Our plain reading |
| --- | --- | --- | --- |
| Anthropic | [Consumer Terms](https://www.anthropic.com/legal/consumer-terms) (effective 2025-10-08), §3 | may not use the Services "to develop any products or services that compete with our Services, including to develop or train any artificial intelligence or machine learning algorithms or models" | training any AI model on outputs is prohibited under the consumer agreement |
| Anthropic | [Usage Policy](https://www.anthropic.com/legal/aup) (page shows effective 2026-11-12, six days after we read it; the version in force today was not checked) | "Use outputs to train an AI model (e.g., "model scraping" or "model distillation") without prior authorization from Anthropic" | prohibited unless Anthropic authorises it; applies to all Anthropic services |
| Anthropic | [Commercial Terms](https://www.anthropic.com/legal/commercial-terms) (effective 2025-06-17), §D.4 | may not "build a competing product or service, including to train competing AI models" | bars competing models; the Usage Policy still applies |
| Anthropic | Consumer §4, Commercial §B | Anthropic assigns its rights in Outputs, "if any", to the user | ownership of outputs does not remove the use restrictions |
| OpenAI | [Terms of Use](https://openai.com/policies/terms-of-use/), [Business Terms](https://openai.com/policies/business-terms/) | **UNVERIFIED**: every fetch returned HTTP 403 | Q3 |
| Google | [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms) (effective 2026-03-23) | "You may not use the Services to develop models that compete with the Services"; you are responsible for "the use of that content by anyone you share it with" | bars competing models; we do not use Gemini outputs |
| Mistral | [Commercial Terms](https://legal.mistral.ai/terms/commercial-terms-of-service) (effective 2026-09-25) | the training restriction covers image outputs; no reverse engineering of Mistral products from Output | text outputs not restricted for training; not used today |
| DeepSeek | [Open Platform Terms](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html) (effective 2026-04-29), §4.2 | permitted uses include "training other models (such as model distillation)" | explicitly allowed; needs owner approval as a paid API |

**Downstream readers.** None of these documents claims to bind a person who is not a
party to the agreement. They bind the account holder (Anthropic: "help another person
to access or use"; Google: responsibility for "anyone you share it with"; Mistral:
pass restrictions on to end users). Because the owner's own account produced the
agent-written MartyGraphics text, publishing it under Apache-2.0 does not free *us*
from these terms. A third party's position may differ; that is not our question to
decide.

### 3.2 Built-in components and worked examples

The MartyGraphics component catalog, its definitions and worked examples are
Apache-2.0, but they were written by AI agents (see Q1). The reference generator uses
only component **ids and parameter ranges** (facts about the engine's interface) and
the engine's solved numbers. It does not copy component titles, `about` text or
example steps into training text.

### 3.3 Open-weight models

Outputs of models under Apache-2.0 or MIT (for example Granite 4.2, Qwen3.5, Gemma 4,
SmolLM3, OLMo 3, Ministral 3, Phi-4-mini; see [PLAN.md](PLAN.md) §4) carry no output
restriction in those licences. **Avoid** outputs of Llama 3.2 (a model trained on them
must be named "Llama…" and carries Meta's use policy) and Gemma 3/3n (the Gemma Terms
treat models trained on their outputs as derivatives). Using any local model needs
the Stage 1 approval in PLAN.md (download and install).

## 4. Pipeline

```
 sources ──► normalise ──► engine check ──► number check ──► dedupe ──► overlap check ──► scans ──► split ──► data card ──► clearance
 (A,B,C)    (question,     (marty-solid     (stated ratios   (sha256 +   (coordinator     (PII,      (train /   (+ hashes)    (owner)
            scene, steps)   check --strict)  = solved)        params)     removes; total)  Gitleaks)  dev)
```

| Step | What | Rejects go to |
| --- | --- | --- |
| Normalise | one record per example: question, scene text (compact JSON), task kind | — |
| Engine check | `marty-solid check` (`--strict` when available), pinned engine commit and checker SHA-256 | rejects file with the stable reason (repair material) |
| Number check | each stated ratio equals the engine's solved ratio within 1e-9 | `generator.ratioMismatch` (a generator bug: fix the template) |
| Dedupe | exact: SHA-256 of the scene; near: same component and parameter bucket | dropped |
| Overlap check | we give the coordinator the dataset version; it removes items that overlap the sealed sets on its side and reports only the total removed, once per version (a per-item answer would leak the sealed sets) | removed by the coordinator |
| Scans | personal-data patterns; Gitleaks on the dataset files | dropped, and the source investigated |
| Split | train / development by seed, plus one held-out parameter range and one held-out component in development | — |
| Data card | [template](docs/templates/DATA-CARD.md), every file hashed | — |
| Clearance | owner sets `clearance` to `cleared` for a dataset version | — |

### 4.1 Task kinds

| Kind | Input | Target | Source today |
| --- | --- | --- | --- |
| `author.solid` | learner question | scene with teaching steps | reference generator (4 components) |
| `repair.solid` | question, refused scene, engine reason | a patch that the engine accepts | next: rule-based fixers on the generator's rejects (for example `component.check.spacing` → choose a planet count that divides 2 × (sun + planet)), plus deliberate mutations of valid scenes (drop a required key, unknown key, bad reference) with the inverse patch; every patch re-checked by the engine |
| `refuse.scope` | out-of-scope question | a short "not supported" answer that names what is missing | next: human-written templates (Q1) |
| `compose.solid` | question needing 2+ components | scene with `set`, `parent`, compound trains | later |

Target first mixture (to tune on development data): about 60% author, 25% repair,
10% refusal, 5% compose, about 10,000 to 20,000 examples in total.

### 4.2 Reference generator

[`pipeline/generate_components.py`](pipeline/README.md) implements the A → engine check
→ number check path for `author.solid` today, with tests. It calls no AI model.

## 5. Provenance schema

Every record carries `provenance`:

| Field | Meaning |
| --- | --- |
| `source` | for example `programmatic.components`, `human.<handle>`, `open-weight.<model>` |
| `authorKind` | `program`, `person`, `open-weight-model` or `learner-correction` |
| `licence` | licence of the example (Apache-2.0 unless stated) |
| `clearance` | `pending-owner` or `cleared` (set only by the owner, per dataset version) |
| `generator` | name, version, seed, commit (programmatic) |
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
