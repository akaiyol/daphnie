# One-time approval for scoped skill releases

Status: implemented controller gates; production automatic releases are disabled. The owner selected approval once within a policy. This document defines the proposed scope; it does not install a reviewer, signing service, background task or host isolation.

## Proposed owner policy

- Allow separately evaluated changes within one named flavour’s `libraries/<flavour>/` only. Require library and changed procedure version increases; preserve existing skill IDs.
- Exclude core values, mode contracts, permissions, entrypoints, controller code, evaluator rules and acceptance data. These require owner review outside routine learning.
- Freeze acceptance criteria before the experiment. Proposed starting thresholds: at least three independent target and three regression families; mean improvement at least 0.05 on the declared 0–1 rubric; regression at most 0.02; family cost ratio at most 1.2. These are pilot settings, not research-established universal values.
- Require protected acceptance, actual skill-use evidence and all mandatory protocol checks to pass. Unknown evidence blocks release. The independent reviewer must calibrate its rubric and retain private artifacts.
- Require a monitored trial before verified promotion. Proposed pilot minimum: ten observed tasks across at least 24 hours, with no critical violations, all mandatory checks passing and rollback exercised. The current record checks total observations and elapsed time; task coverage must be verified by the trusted observer.
- Restrict grants to one exact baseline, candidate, evaluation and phase. Grants expire after at most ten minutes and are consumed once. Evidence expires within seven days and the proposed owner policy expires after 30 days for review.
- Let the trusted authorization service issue grants automatically within this policy. A separate signing identity approves grants; the learner cannot sign its own evaluation, trial or authorization.
- On an explicit signed trial failure, restore only the original baseline without another owner prompt. Unknown checks block promotion; no timeout daemon is installed. The trusted host must deliver observations and call rollback. Expired policy or unavailable observers require operator intervention.

These proposed thresholds must be approved and calibrated against representative tasks before production activation. Approving this policy does not prove that a candidate improves Daphnie.

## Resources approved by the owner

Use existing task budgets only. Automatic phase selection is available through `advance-update`; Daphnie owns preparing candidates and requesting reviews under [the task-driven workflow](../SELF_UPDATE.md). No separate ongoing spending or background allowance is granted. A missing grant within an approved policy is obtained from the trusted service rather than requested as another owner approval.

## Trust setup required

The CLI reads one fixed owner-managed file: `~/.config/daphnie/release-policy.json`. It must be an owner-owned regular read-only file, with no symlink. It contains public keys, role assignments, scope, expiry and frozen thresholds. Private signing keys and protected acceptance datasets never belong in the public repository or learner context.

A trusted host must protect the policy, controller deployment/state, signed evidence and private keys from the learner’s write and execution capabilities. File permission bits under the same unrestricted account do not establish that separation. Do not configure same-account learner-generated keys and call this independent evaluation. Arbitrary Python access to internal APIs also bypasses an in-process trust boundary.

The trusted integration must implement acceptance execution and artifact checking, grant issuance, trial observation and failure delivery. It may run as part of the host’s task-completion workflow or a separately authorized service. This repository does not install either. A Daphnie skill invocation alone does not start them or capture other chats.

## Review and operations

`release-status` explains whether the host policy exists and reports the selected version and verification label. `release-preview --bundle PRIVATE_BUNDLE` validates the entire trial or promotion bundle without selecting a release or consuming its grant; it may finish pending history recovery. `start-trial`, `promote-release` and `stop-trial` execute the corresponding signed transition. All use the existing `--state PRIVATE_STATE` option.

For a trial or promotion, both snapshots must already be captured and prepared. The private bundle carries signed evaluation and authorization; promotion also carries signed trial observations. The controller rechecks evidence immediately before publication. A fresh generation is built from snapshot blobs; mutable prepared-cache contents are never selected directly.

After atomic pointer publication, a history failure is reported as applied with pending recovery. `recover` finishes history; it does not rerun external tasks. Before publication, failure preserves the previous selection. A consumed but unpublished grant requires a new grant from the trusted service, within the already approved policy.

Existing installed skills still point to their current checkout. Switching them to controller-managed releases requires deliberate installer migration; this change does not alter those links. Existing chats are not guaranteed to reload changed skills. There is no background task, automatic Git pull, automatic publication or demonstrated live improvement in this implementation.

## Design basis

[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) informs the separation between transactional history and filesystem publication. [The Update Framework specification](https://theupdateframework.github.io/specification/latest/) informs trusted roles, hash-bound targets, expiry and signed authorization; this is not a TUF implementation. [OpenSSL Ed25519 verification](https://docs.openssl.org/3.6/man1/openssl-pkeyutl/) supplies the signature operation. See the [evaluation protocol](PROTOCOL.md) and [research credits](../README.md#credits-and-design-influences) for behavioral evaluation foundations.
