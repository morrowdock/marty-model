# Contributing

Small, focused pull requests are welcome. This project is at the planning stage.

## Sign-off (DCO)

Every commit must include a DCO sign-off. By signing, you certify the
[Developer Certificate of Origin 1.1](https://developercertificate.org/) for that
commit. Use `git commit -s` and an email you are comfortable publishing; a GitHub
noreply address is recommended. A sign-off is a certification, not a cryptographic
signature.

## Data and examples

Training data is the most sensitive part of this project. Before you submit an example,
a generator or a dataset:

1. **Rights.** You must have the right to publish it under Apache-2.0. Do not submit
   text or scenes written by a hosted AI model unless the data rules (`DATA.md`, in
   review) say that source is allowed. Until they land, do not submit such data. If you are not sure, say so in the pull request and do not
   include the data.
2. **Engine check.** Every scene must pass the MartyGraphics engine (`marty-solid
   check`, and `--strict` when it is available). Record the engine commit and the
   checker binary hash.
3. **Provenance.** Every example carries the provenance fields that `DATA.md` lists: source,
   licence, author kind (program, person, open-weight model), generator version, engine
   commit, checker hash, and date.
4. **No personal or private content.** No personal data, no learner data without
   recorded consent, no private course material, no credentials, no proprietary
   templates.
5. **No evaluation leakage.** Do not submit questions, scenes or text taken from any
   MartyGraphics evaluation set. Evaluation sets are sealed and are run by the
   MartyGraphics coordinator only.

## Code

* Python scripts use only the standard library unless a pull request explains why.
* Add a test for each behaviour you change. Run `python3 -m unittest discover -s tests`.
* Keep scripts deterministic: the same seed gives the same bytes.

## Conduct and security

Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Report vulnerabilities as
[SECURITY.md](SECURITY.md) describes, not in public issues.
