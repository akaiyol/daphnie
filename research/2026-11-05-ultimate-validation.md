# Ultimate: mechanism verification and adoption assessment

Review date: 2026-11-05. Upstream: [Ultimate](https://github.com/HazAT/ultimate), Daniel Griesser (HazAT) and contributors. Inspected revision: [`29f3db4e76d888d305ab8ce33fd7f1db793c9d1a`](https://github.com/HazAT/ultimate/tree/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a).

## Decision and scope

The tested runtime mechanisms are credible implementation references. They are not validated Daphnie features. Adopt the patterns conditionally: explicit capability profiles, visible context provenance, replay-aware durable state, and a deterministic checked release queue. Preserve Daphnie's independent behavioral evaluation, flavour contracts, data permissions and owner-controlled governance. Do not import Ultimate's unrestricted customization, automatic lesson promotion, or global/project override precedence as Daphnie policy.

This review inspected source and ran focused scripted-model tests in a temporary checkout. It made no requests to a paid model, installed no running Ultimate service, used no personal conversation data, and imported no Ultimate runtime code into Daphnie. The independent probes committed alongside this report are original review tests, designed to run inside the upstream checkout.

## Reproduction environment

- Node v26.13.0 and pnpm 11.8.0, installed only in a temporary tools directory.
- macOS arm64; Apple Git 2.50.1. Ultimate's README requests Git 2.54 or later, so this is not its fully supported environment.
- Dependencies installed from the pinned lockfile with `pnpm install --frozen-lockfile --ignore-scripts`; dependency install scripts stayed disabled. No dependency or runtime source patches beyond the repository's existing lockfile patches were introduced.
- Test scratch storage was redirected to a dedicated temporary directory. Upstream setup disables real provider credentials and the real Claude/Tailscale commands; tests use faux/scripted responses.
- No full-suite, external-service, long-running personal-agent, model-quality, or OS-level isolation certification is claimed.

From a disposable checkout at the revision above, run:

```sh
pnpm exec vitest run test/agents-deny-tools.test.ts test/skills.test.ts test/lineage-memory.test.ts test/lander-watchdog.test.ts --maxWorkers=2
pnpm exec vitest run --config test/e2e/vitest.config.ts test/e2e/supervisor.test.ts test/e2e/workspaces-integration.test.ts --maxWorkers=1
```

Copy [ultimate-probes.test.ts](ultimate-probes.test.ts) into that checkout as `test/daphnie-audit.test.ts`, then run `pnpm exec vitest run test/daphnie-audit.test.ts --maxWorkers=1`. These probes inspect actual configuration assembly; they do not ask a language model to obey the resulting instructions.

## Observed results

| Test file | Unmodified upstream result | What it supports |
|---|---|---|
| `test/agents-deny-tools.test.ts` | 3 passed | Explicit/inherited tool filtering, additive denials, preservation of parent tools |
| `test/skills.test.ts` | 2 passed | Skill origins/overrides, gated project skill locations, command expansion |
| `test/lineage-memory.test.ts` | 12 passed | Atomic memory operations, limits, source-linked briefs, restricted `remember` writer and deduplicated distillation |
| `test/lander-watchdog.test.ts` | 10 passed | Check deadlines, output/error retention, process-group handling |
| `test/e2e/supervisor.test.ts` | 6 passed | Restart replay, failed preparation, failed activation rollback, storage ownership, SIGKILL recovery |
| `test/e2e/workspaces-integration.test.ts` | 68 passed; 6 failed | Broad workspace/release integration, with six failure-injection cases initially unresolved |
| Independent `test/daphnie-audit.test.ts` | 4 passed | Capability subset, deferred denial, broad default inheritance and limits of read-only prose |

### Six integration failures and the diagnostic rerun

Five cases timed out and one failed an expected-result assertion. All six depend on `reference-transaction` hooks identifying a parent process with a command line starting `git <command>`. An independent temporary Git-hook diagnostic showed Apple Git reporting its absolute executable path instead. Therefore those hooks never activated their intended hold/failure condition in this environment.

In the disposable checkout only, the two hook templates in `test/e2e/workspaces-integration.test.ts` were adjusted to normalize the initial executable path before matching. Specifically, `ps -ww -p "$PPID" -o args=` was piped through `sed 's|^[^ ]*/git |git |'`. No production code, assertion, deadline, expected result or runtime policy changed.

Reran only the six failed cases:

```sh
pnpm exec vitest run --config test/e2e/vitest.config.ts test/e2e/workspaces-integration.test.ts --maxWorkers=1 -t 'renders workspace preparation|queued landing reads|aborting release|resuming a child after its removal|branch deletion failure|persistent branch deletion'
```

Result: 6 passed, 68 skipped. The passing rerun supports the process-name mismatch diagnosis. It is a result with an adapted test fixture, not an unmodified full-suite pass or a claim that every Git version is supported. The unaffected 68 cases were not rerun. Preserve this distinction when reporting the results.

## Mechanism-level findings and Daphnie conditions

| Candidate mechanism | Source evidence and judgment | Condition before adoption in Daphnie |
|---|---|---|
| Executable flavour configuration | [`definitionAgent`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/lib/agents.ts#L146) filters tool exposure; focused tests and independent probes pass. A definition without `tools` inherits broad capabilities. | Require explicit allowlists per flavour, validated tool names, externally protected permissions, and tests for equivalent actions through other tools. |
| Context/skill provenance | [`server/skills.ts`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/server/skills.ts) records scopes and overridden paths; skill tests pass. Its `.pi/skills` layer is loaded before the trust-gated `.agents/skills` and `.ultimate/skills` layers. | Inventory every load path. Reject unauthorized sources before loading; do not assume all project skill locations share the same trust gate. Record actual loaded versions and retrieved records per session. |
| Durable actions and recovery | [`docs/durability.md`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/docs/durability.md) separates safe replay from interrupted effects; supervisor tests demonstrate bounded recovery behavior. | Add idempotency keys, reconciliation and crash-point tests for Daphnie's actual connectors. Never infer exactly-once external delivery from SQLite transactions. |
| Deterministic release queue | [`lander.ts`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/extensions/workspaces/lander.ts), workspace tests and supervisor tests support checked integration and activation recovery. Passing checks can include a failure followed by a passing rerun, labeled flaky. | Require Daphnie's protected behavioral report, owner authorization and compatible-state rollback. Treat flaky boundary/behavioral checks as unresolved, not automatic promotion eligibility. Do not let candidates rewrite the gate. |
| Evidence-linked reflection | [`DREAM.md`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/extensions/dream/DREAM.md) distinguishes code, checks, instructions, skills and contextual memory. The [`dream-pass`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/agents/dream-pass.md) is instructed to read only but includes `bash` and `codemode`. Independent assembly probes confirm read-only prose does not remove shell access. | Use inspection-only APIs or an enforced read-only execution environment. Treat reflection output as candidates; assess benefit and cost before adopting a recurring reflection process. |
| Structured memory writes | [`memory.ts`](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/extensions/lineage/memory.ts) validates batches and source links, and tests cover a restricted writer and deduplication. A summary model can still distill landed work automatically. | Preserve provenance and atomicity, but add owner/project/flavour permissions, evidence review, contrary evidence and applicable update tests. A successful merge or well-formed memory is not proof of a correct transferable lesson. |

Ultimate's [security policy](https://github.com/HazAT/ultimate/blob/29f3db4e76d888d305ab8ce33fd7f1db793c9d1a/SECURITY.md) explicitly distinguishes code-enforced boundaries from ordinary content steering. Its cross-project reading/messaging is an intentional feature, not evidence of Daphnie-style confidentiality isolation. Git worktrees isolate edits, not general filesystem, network or credential access.

## Daphnie transfer validation still required

Before any mechanism is called validated for Daphnie:

1. Build one minimal host adapter with explicit flavour/tool/data permissions and a session manifest. Test both retrieval and direct tool access with synthetic cross-project sentinels, alternative tool routes and flavour switches.
2. Compare the current instruction-only package against the adapter on matched task families, including adverse memory, costs, flavour fidelity and shared-core regressions. Freeze the candidate and protect acceptance tasks before evaluation.
3. Exercise crash recovery around each actual external side effect, including an uncertain response after the external action completed. Verify that recovery reconciles rather than duplicates the effect.
4. Submit known-bad skills and changed gate configurations. Confirm that failed, unknown, stale, flaky or unauthorized evidence cannot activate a release. Restore prior skills, retrieval configuration and compatible memory, then verify resulting behavior.
5. Run an authorized limited trial and inspect later outcomes before broadening scope. A passing upstream infrastructure test cannot substitute for these steps.

No Daphnie runtime mechanism was activated by this review. The result is a bounded verification record, original review probes and explicit adoption requirements.

## Attribution

Ultimate: MIT License, copyright 2026 Daniel Griesser. Pi / Pi Durable and the Earendil Works contributors deserve upstream credit for the durable framework used by Ultimate. The observed behavior belongs to that combined dependency stack; this review does not attribute every component to Ultimate or independently certify Pi Durable. Source reuse would require retaining applicable notices; this assessment and its original probes do not copy the upstream runtime.
