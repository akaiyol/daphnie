# Local controller operations

Status: functional, manually operated development controller. Python 3.9+ and SQLite support local operations; signed release verification additionally requires OpenSSL with Ed25519 support. Live attempts additionally require an installed, signed-in Codex CLI available as `codex` on PATH. No dependency, scheduler or model is installed automatically.

## What happens when you call Daphnie

Invoking a Daphnie skill loads its instructions in the current chat. It does not start this controller. The controller records only explicitly registered and scanned roots, submitted observations and attempts it launches. It cannot consolidate unseen chats or prove that an unmanaged session used a particular skill.

Each observation belongs to a root, flavour, project and topic. Consolidation groups matching evidence into proposed bundles. It does not infer a verified lesson or change an active procedure. A separate candidate workspace lets an operator make and review the proposed edit while retaining the baseline.

## Data and commands

Keep state in a dedicated private directory outside the public checkout and all registered roots. Use synthetic development fixtures only for model runs. State contains evidence, output artifacts and local paths; do not commit or publicly export it. Filename exclusions, conservative output minimization and obvious credential rejection are safeguards, not comprehensive secret detection. Backups need the same privacy controls. No deletion/retention engine is implemented yet.

All commands below run from the package checkout. Uppercase values stand for operator-selected paths or complete IDs returned by preceding commands. Use `--help` on any command for arguments. The controller exclusively locks operator commands, commits events transactionally and checks content hashes. It detects accidental corruption; it is not tamper-proof against the same operating-system account.

```sh
python3 scripts/daphnie.py --state PRIVATE_STATE init
python3 scripts/daphnie.py --state PRIVATE_STATE register source CHECKOUT --flavour shared --project daphnie
python3 scripts/daphnie.py --state PRIVATE_STATE scan source --reason 'Initial baseline'
```

Register narrow roots. Package roots require `CORE.md`. Private note roots use `--kind memory` and an exact flavour/project. Registration grants capture permission for that root; `.git`, dependency caches, designated private directories and credential filenames are excluded and listed in the snapshot. Changes discovered at a later scan have unknown authorship unless explicitly supplied. There is no continuous file watcher.

```sh
python3 scripts/daphnie.py --state PRIVATE_STATE observe source --flavour assistant --project daphnie --topic recovery --text-file PRIVATE_NOTE
python3 scripts/daphnie.py --state PRIVATE_STATE consolidate source --flavour assistant --project daphnie
python3 scripts/daphnie.py --state PRIVATE_STATE candidate BASELINE_ID --workspace NEW_CANDIDATE_DIRECTORY --flavour assistant --reason-file PRIVATE_REASON --bundle BUNDLE_ID
python3 scripts/daphnie.py --state PRIVATE_STATE scan CANDIDATE_ROOT --reason 'Reviewed candidate edit'
```

The candidate command returns its registered root ID. Edit only the intended procedure in that workspace, review the diff and scan it to obtain `CANDIDATE_ID`. The selected flavour is metadata and prompt routing, not enforced filesystem authority: review must still ensure the edit stays within its approved scope. Shared/core changes require owner review and broader evidence.

## Run a comparison

Freeze exact baseline/candidate snapshots, suite, model, reasoning effort, CLI version, scorer, budget and thresholds before execution. The public starter suite has only one synthetic family per flavour. It checks basic artifacts, not realistic competence or personality. Expand independent families and calibrate scoring before interpreting an apparent gain.

```sh
python3 scripts/daphnie.py --state PRIVATE_STATE plan --baseline BASELINE_ID --candidate CANDIDATE_ID --suite benchmarks/development/core.json --adapter codex --model CONFIGURED_MODEL --effort CONFIGURED_EFFORT --max-attempts 8 --timeout 120
python3 scripts/daphnie.py --state PRIVATE_STATE run PLAN_ID
python3 scripts/daphnie.py --state PRIVATE_STATE compare PLAN_ID
python3 scripts/daphnie.py --state PRIVATE_STATE history --html PRIVATE_REPORT.html
```

Eight attempts cover the four starter tasks, each run once on baseline and candidate. A `--task` filter can narrow a smoke test with a correspondingly explicit budget. Repeats do not increase the independent family count. Plans run once and automatically record their comparison; `compare` reads that existing report or creates one for a partial run. Comparisons cannot be overwritten. Timeouts, process errors and interrupted attempts remain in history. There is no automatic retry or replay of external actions. The trusted `command` adapter is for controller fixtures, not evidence of agent improvement.

Each Codex attempt starts a fresh ephemeral session in a fresh directory with synthetic files and the frozen package. The prompt names the selected skill. Supported settings disable user configuration, automatic memories and bundled skills; the plan records model and CLI configuration. Reasoning and raw command output are not retained. Final artifacts, minimized event metadata, available token counts and elapsed time are recorded. Monetary cost is unknown without an explicit pricing model. Intended skill hashes and post-run package integrity are checked; actual skill loading remains unverified. These measures do not establish process, network, flavour or private-memory isolation.

Reports summarize paired changes separately by flavour and bootstrap task families. Failures remain visible. Mandatory unknown checks always block verified release: protected acceptance isolation, flavour fidelity, evaluator calibration, general privacy and actual skill loading. A positive development result cannot automatically activate anything. The older `scripts/evaluate.py` separately reviews supplied acceptance records under the [protocol](PROTOCOL.md); it does not convert these development results into verified evidence.

## Fetch and adopt updates

```sh
python3 scripts/daphnie.py --state PRIVATE_STATE fetch source --branch main
python3 scripts/daphnie.py --state PRIVATE_STATE import-revision source EXACT_40_CHARACTER_COMMIT
```

Fetching updates Git objects only. Importing snapshots the exact commit without changing the working checkout, installed skills or active release. Review and compare that snapshot before deciding whether to adopt it. No automatic pull, merge, self-edit or publication occurs.

Manual adoption is deliberately separate from verified learning:

```sh
python3 scripts/daphnie.py --state PRIVATE_STATE prepare-release SNAPSHOT_ID
python3 scripts/daphnie.py --state PRIVATE_STATE activate RELEASE_ID --confirm-release RELEASE_ID --reason 'Explicit owner adoption' --owner-adopt-unverified
python3 scripts/install.py --release-state PRIVATE_STATE --destination SKILLS_DIRECTORY
```

Prepared packages are content-addressed and checked against their snapshots and required package layout. Activation copies verified snapshot blobs to a fresh read-only deployment. Atomic replacement of the stable `current` pointer commits the selection; SQLite history is a recoverable projection. The installer refuses unknown existing entries, including links to the editable checkout. Inspect and deliberately migrate those links if opting in; this implementation does not replace them. Existing installations remain attached to their checkout until migrated. Active package files must be treated as read-only; hash checks detect mutation but the same account can still edit them. Skills in an already-running chat are not guaranteed to reload; use a fresh chat after changing the active release.

```sh
python3 scripts/daphnie.py --state PRIVATE_STATE rollback PREVIOUS_RELEASE_ID --confirm-release PREVIOUS_RELEASE_ID --reason 'Owner rollback' --owner-adopt-unverified
python3 scripts/daphnie.py --state PRIVATE_STATE recover
python3 scripts/daphnie.py --state PRIVATE_STATE verify
python3 scripts/daphnie.py --state PRIVATE_STATE status
```

Rollback accepts a previously active package and preserves newer observations. Compatible private-memory rollback is not implemented. Recovery marks unfinished attempts interrupted and repairs history from the published selection and restores a missing pointer from the last applied deployment; it does not repeat actions. Manual adoption records `behavior_verified: false`, requires explicit full-ID confirmation and reason, and never claims compliance with the verified-release protocol. The CLI is not an independently authenticated approval service.

## Validation and remaining work

See the [initial validation record](../research/2026-11-05-controller-validation.md) and [whole-lifecycle validation](../research/2026-11-05-lifecycle-validation.md). The repeatable `tests/test_lifecycle.py` drives capture through rollback and recovery without model calls. Signed evidence, preauthorized grants, monitored-trial gates and signed failure rollback are implemented; see [release policy and setup](RELEASE_POLICY.md). Protected production acceptance and authority separation, calibrated flavour/privacy/poisoning checks, actual skill-use evidence and realistic multi-family tasks remain deployment requirements. Background operation should be added only after those boundaries and an explicit operating schedule are defined.

## Advance an update without choosing the phase

`advance-update --bundle PRIVATE_SIGNED_BUNDLE` determines the next transition from the active snapshot and trusted evidence. It prepares the exact snapshots and starts an eligible trial, promotes a completed passing trial, restores the original baseline after signed failure, recognizes an already verified candidate, or records a deferral when evidence is incomplete. Missing authorization is a request to the configured host service, not a new per-release owner approval. Invalid signatures and identity mismatches remain errors. Evidence blobs and `update_decision` events are private and retained for resumption.

The command launches no model attempts. Daphnie obtains review artifacts using only the active task’s remaining allowance under the [self-update workflow](../SELF_UPDATE.md). No scheduler or independent reviewer is installed.
