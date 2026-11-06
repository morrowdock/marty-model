# Security policy

This project is at the planning stage. Only the latest `main` branch is considered for
security fixes; there is no security support SLA and no supported release yet.

Report vulnerabilities privately to **admin@morrowdock.app**. Include the affected
commit, the impact and minimal synthetic reproduction steps. Do not post
vulnerabilities, secrets, personal data or private course material in public issues.
Never include credentials in a report. We coordinate disclosure after a fix is
available.

## In scope

* Scripts in this repository (for example, a data generator that runs an engine binary
  on untrusted input).
* Released datasets and model files, when they exist: for example, an example that
  contains personal data, a credential, private content or an evaluation item.
* Model behaviour that bypasses the engine check or hides that a scene was not checked.

## Out of scope

* Bugs in the MartyGraphics engine itself. Report those to
  [MartyGraphics](https://github.com/morrowdock/martygraphics/blob/main/SECURITY.md).
* Factual errors in model output that do not have a security impact. Open an issue.
