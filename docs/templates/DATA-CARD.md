<!--
Data card template for a Marty training or development dataset. Copy this file next
to the dataset, fill every field, and delete these comments. Write "none" rather than
leaving a field empty. Sealed evaluation sets do NOT get a public data card from this
project: the MartyGraphics coordinator owns and describes them.
-->

# Marty data card: `<dataset name>-<version>`

## Summary

| Field | Value |
| --- | --- |
| Name and version | `<name>-<version>` |
| Date created | `YYYY-MM-DD` |
| Purpose | training / development (never held-out evaluation) |
| Licence | `<for example Apache-2.0>` |
| Terms that flow down to users of this data | `<list or none>` |
| Examples | `<n>` (train `<n>`, development `<n>`) |
| Files and hashes | `<file>`: sha256 `<hash>` |
| Format | JSON Lines, one example per line, schema `<schema id>` |
| Generator | `<script>` at commit `<sha>`, seed `<seed>` |
| Engine | MartyGraphics commit `<sha>`; checker `<binary>` sha256 `<hash>` |
| Contact | admin@morrowdock.app |

## Sources

One row per source. A source that is not on the allowed list in `DATA.md` must not
appear here.

| Source | Kind | Licence / terms (URL, date checked) | Examples | Share |
| --- | --- | --- | --- | --- |
| `<for example programmatic: built-in components>` | program | Apache-2.0 (this repo) | | |
| `<for example hand-written MartyGraphics examples; check each provenance.json>` | person | Apache-2.0 (`<URL>`) | | |
| `<open-weight model name>` | open-weight-model | `<licence URL>` | | |

Author kinds: `program` (rules and templates, no model), `person` (a named human,
DCO sign-off), `open-weight-model` (name, revision, licence), `learner-correction`
(only with recorded consent; see `DATA.md`). Text or scenes written by a hosted AI
model are excluded unless `DATA.md` allows that provider.

Is the dataset licence compatible with every source? `<yes / explain>`

## Per-example provenance

Every example carries these fields (see `DATA.md` for the exact schema):
`id`, `source`, `authorKind`, `licence`, `clearance`, `templateAuthor`, `generator`
(name, version, seed, script sha256, commit, dirty), `engine` (commit, checker sha256),
`check` (command, `ok`, reason, ratios, `engineVerified`, `derived`), `created`, and
`sceneSha256`.

## Checks run

| Check | Result |
| --- | --- |
| Every scene passes `marty-solid check` (and `--strict` when available) | `<n>/<n>` |
| Every stated engine-solved ratio equals the engine's value | `<n>/<n>` |
| Every other stated number is exact arithmetic on the scene (listed per example as `derived`) | `<n>/<n>` |
| Exact and near duplicates removed (method) | `<n removed>` |
| Overlap with sealed evaluation sets checked by the coordinator (method, no access by us) | `<result>` |
| Personal data scan (method) | `<result>` |
| Secret scan (Gitleaks version) | `<result>` |

## Coverage

`<Table of scene kinds, components and parameter ranges covered, with counts.
Name what is NOT covered.>`

## Known issues and biases

`<Plain list. For example: templated language is repetitive; only English; only
mechanical topics.>`

## Consent and personal data

`<"No personal data" or, for learner corrections: how consent was recorded; how
consent was recorded for learners under 18 (a parent or guardian); how data was
de-identified; how a person can ask for removal; and what happens to models already
trained on the data when consent is withdrawn.>`

## Changes from the previous version

`<list or "first version">`
