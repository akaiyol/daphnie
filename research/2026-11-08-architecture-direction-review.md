# ADR: Standalone Daphnie with a durable runtime and evidence-based learning

**Status:** Proposed. Standalone direction selected by the owner; this review does not approve a replacement release policy or deploy services.
**Date:** 2026-11-08
**Decider:** Owner, informed by this review and a measured pilot.

## Context

The intended product is a personal agent that works across apps and projects, retains a consistent identity, uses several working modes, and improves its procedures without repeated supervision. The owner permits releases within a policy approved once and permits learning to use existing task budgets only.

The current package contains useful instruction routing, scoped memory mechanics, snapshot/history storage, development comparisons, signed release gates, trial rollback and an automatic phase-selection command. It does not contain the standalone runtime that starts and supervises tasks, obtains acceptance judgments, calls an authorization service, observes trial outcomes and reliably invokes the update pipeline.

The central gap is integration and demonstrated task benefit. The current architecture has more evidence about release mechanics than about useful learning. This review challenges both owner decisions and implementation choices made while fulfilling them.

## Verified observations

- `advance_update` takes an already assembled signed bundle. It selects a permitted transition but does not create the candidate, execute acceptance or obtain signatures. Its decision records explicitly report zero model attempts and no background task.
- Installed skill links still resolve to the editable canonical checkout. They have not migrated to the controller's managed `current` release selection. A successful controller promotion therefore does not by itself establish what an ordinary skill invocation loads.
- No production host-policy file is present. The installed instruction package does not supply a protected acceptance runner, authorization issuer or trial observer.
- The recorded eight-attempt live pilot had baseline and candidate quality of 1.0 in every flavour. With one task family per flavour, it was inconclusive. The design scorer verified structure, not rendered artistic quality. See [live validation](2026-11-05-lifecycle-validation.md).
- The subsequent 90-test suite and bounded lifecycle model validate mechanics under their stated assumptions, not useful autonomous learning. See [task-driven changes](2026-11-08-task-driven-updates.md).

These observations support an architectural change in sequencing; they do not establish that the existing controls or instruction files are inherently ineffective.

## Decisions to keep or revise

| Earlier choice | Assessment | Proposed revision |
|---|---|---|
| Stable identity and owner-controlled permissions | Keep | Protect them from routine learning, while retaining explicit owner revision and version history. |
| Four flavours | Keep as working profiles | Separate identity, role, project data and access authority. A role switch is not an access-control boundary. |
| Each flavour owns skills | Keep ownership; relax duplication | Permit approved shared procedural dependencies with pinned versions and destination testing. Private project memory remains scoped. |
| Autonomous self-updates | Keep, with outcome accountability | Optimize task success and reduced correction recurrence. Making more changes is not a success metric. |
| Approval once within a policy | Keep | Make the runtime enforce scope, resource limits and exceptions. Do not substitute repeated permission prompts for missing integration. |
| Existing task budgets only | Keep as a real constraint | Account for building, reviewing and trying updates before launching work. Defer learning when it would jeopardize task completion. This is not an allowance for unlimited idle-time work. |
| Every learned update uses one quality-gain gate | Revise | Use change-specific evidence profiles, frozen before evaluation. A reproducible repair, an efficiency improvement and a behavioral strategy have different benefit claims. |
| A universal 0.05 gain and fixed observation/duration minimums | Recalibrate | Current numbers are proposals, not measured reliability guarantees. Choose meaningful effects, task coverage and trial duration using pilot variance and risk. |
| Separate signed services before any verified learning | Simplify deployment, preserve independence | Start with one trusted runtime and a protected evaluator/activation boundary. Use signed records when evidence crosses a trust boundary; separate network services are not inherently required for local decisions. |
| Immutable snapshots, atomic selection, audit and rollback | Keep | Make this the actual installation path and record the version loaded in each task. |
| Text files direct the agent | Keep for instructions | Use executable tools for budgets, access control, deadlines, activation and observation. Measure whether the instruction was actually used and helped. |

Changing these rules requires a deliberate owner-approved architecture/policy revision. This proposal does not weaken existing signed gates or silently promote candidates.

## Options considered

| Option | Benefit | Cost and limitation | Fit |
|---|---|---|---|
| Continue improving the Codex instruction package | Lowest immediate work; retains existing host tools | Lifecycle invocation and cross-app operation remain host-dependent | Useful client/integration, insufficient as the product's centre |
| One standalone runtime with restricted workers and app adapters | Direct ownership of task lifecycle, budgets, context and learning; reuses existing Python/controller code | Requires real tool mediation, durable state and host capability validation | Recommended first implementation |
| Distributed service platform with independently deployed reviewer, signer and memory services | Supports multiple machines and organizational trust boundaries | More operational burden and failure modes before task benefit is established | Defer until a concrete boundary or scale requires it |

This recommendation is an engineering judgment about the owner's goals, not a research finding that one architecture universally wins. A standalone model connection, its credentials and its usable resource accounting still require verification; an existing task allowance does not itself configure that connection.

## Proposed responsibilities

Use one local-first runtime initially. Avoid splitting deployment units merely because logical responsibilities differ. Preserve a real protected boundary wherever learner code could otherwise alter criteria, private data or activation.

1. **Clients:** accept work and show status. Codex is one client; other apps connect through explicit adapters. Client conversations do not own the canonical task state.
2. **Task supervisor:** creates durable task/project identities, reserves the remaining authorized budget, records checkpoints, detects stalls, and controls resume/cancellation. Tool adapters declare whether cancellation is supported. A timeout is not proof that an external effect was cancelled.
3. **Context and capability assembly:** loads the owner policy, selected mode, authorized project records and relevant versioned procedures. Access is checked before retrieval and before tool execution. Workers cannot bypass the gateway with a broader shell or filesystem capability.
4. **App/tool gateway:** holds credentials outside learner context, enforces per-project read/write/action permissions and records outcome receipts. Retries require operation-specific deduplication or reconciliation. Uncertain external effects are not automatically replayed.
5. **Memory and procedure stores:** separate contextual facts/preferences from reusable execution guidance. Preserve provenance, correction/expiry semantics and supporting evidence. Share sanitized procedures through explicit dependencies; do not turn mode labels into privacy enforcement.
6. **Task evaluation:** evaluates the actual artifact or resulting app state with appropriate code checks, calibrated judgment and selective human review. Store expected and observed skill versions, environment/configuration and outcome evidence.
7. **Learning pipeline:** creates focused candidates from supported failures, runs development checks, obtains protected acceptance, applies the approved evidence profile, starts bounded trials, monitors outcomes and restores prior compatible state on failure.
8. **Release registry:** selects the package actually loaded by new tasks. Record a complete immutable package snapshot while changing only the authorized procedure scope. Existing task contexts remain tied to their starting version unless explicitly restarted.

Every trial needs an enforced stopping condition for failure, missing observations, observer unavailability and budget exhaustion. Recovery authority should be narrowly sufficient to restore the recorded baseline even when ordinary promotion authorization has expired; the current code does not implement that autonomous watchdog. A rollback of skill files cannot undo external app effects or erase already exposed context. Trial memory writes need attributable versions and a defined reconciliation policy.

A trusted runtime process does not automatically enforce worker isolation. The implementation must restrict worker file/tool access and prevent direct policy/state/key modification. App interfaces that cannot provide the required separation need narrower allowed actions or explicit limitations.

## Evaluation changes

Use evidence proportionate to the claim while retaining critical permission/privacy checks:

- **Repairs:** establish the intended behavior with a failing-then-passing regression and unchanged required behavior. This supports a scoped repair claim, not general agent competence.
- **Efficiency changes:** demonstrate resource improvement with quality remaining within a predeclared noninferiority margin. A quality-only gain gate cannot establish this kind of benefit.
- **Behavioral procedures:** use paired baseline/candidate tasks, held-out families, calibrated rubrics, adverse cases and a monitored trial. Do not repeatedly tune to protected outcomes.
- **Governance, permissions and acceptance changes:** remain owner-controlled and outside routine learner promotion.

Keep evaluation profiles outside candidate control. Record coverage, evaluator/configuration version, trial state and limitations alongside any verification label. A global `behavior_verified` boolean should not be interpreted as validity for arbitrary projects, models or tools.

For procedure diagnosis, distinguish availability, loading, use and benefit. Compare the baseline against the candidate and, where informative, the supporting source evidence and irrelevant/incorrect context. Do not assume the candidate wins because the text was shorter or more explicit.

## Implementation order and acceptance

1. Connect one durable task path to one authorized app/project scope. Establish start, checkpoints, observed completion, bounded tool waiting and restart recovery before expanding app coverage.
2. Unify installation and task identity: one canonical source repository, immutable deployed releases, one active selection and a recorded loaded version per new task. Development edits cannot silently become production procedures.
3. Build a representative evaluation set from actual failures. Separate deterministic artifact failures from subjective quality; calibrate the latter against owner judgments before automatic decisions depend on it.
4. Demonstrate one complete learning cycle: observed failure, scoped candidate, protected comparison, permitted activation, actual loading on a new task, later outcome and rollback drill. Keep baseline conditions and budgets comparable.
5. Expand app adapters and approved shared procedures only after this path works. Add independent deployments or remote signatures when concrete trust boundaries require them.

For a fixed pilot window, report by task family/mode/project: verified task completions divided by attempted tasks; tasks requiring unplanned owner rescue divided by attempted tasks; repeated known failures divided by relevant recurrence opportunities; resource use and time to verified completion. Keep failures and timeouts visible in the denominator. Compare matched baseline/candidate outcomes before attributing improvement to a skill change. Record boundary violations separately, with critical violations blocking release regardless of average performance.

Track learning overhead against the same authorized task allowance, including failed reviews and retries. A rejected candidate can be a correct decision; a high promotion rate is not a target. A passive runtime may exist without a separate model budget, but new model work still requires remaining authorized allowance. No new schedule, spending or app access is approved here.

## Research basis and limits

- [Anthropic, Building effective agents](https://www.anthropic.com/research/building-effective-agents): engineering experience favors starting with simple composable patterns and justifying complexity. This is practice guidance, not a controlled comparison proving this proposed runtime.
- [Anthropic, Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents): distinguish transcripts from actual outcomes; combine deterministic, model and human grading appropriately and calibrate judges. This supports the measurement direction, not any particular Daphnie threshold.
- [Li et al., SkillsBench, v4](https://arxiv.org/html/2602.12670v4): evaluates 87 terminal/container tasks. Curated skills help on average; the diagnostic self-generated condition underperforms no-skills in three configurations. The authors identify discovery, authoring/solving interference and content errors, with configuration and coverage caveats. This does not establish that evaluated longitudinal self-improvement is impossible, or that terminal results transfer directly to cross-app GUI work.
- [Zhao et al., Large Language Model Agents Are Not Always Faithful Self-Evolvers](https://proceedings.mlr.press/v306/zhao26aw.html): controlled interventions across four frameworks, 13 backbones and nine environments reveal problems using condensed experience. This motivates retaining evidence and testing causal use; it does not require loading entire histories or establish the best storage architecture.

## Consequences

The standalone runtime becomes the main product; instruction files and Codex integration remain reusable assets. Current snapshot, recovery and comparison code can be retained. Some signing/deployment complexity is deferred rather than expanded. Task supervision, protected evaluation and reliable version loading become near-term priorities.

Broader autonomy becomes a capability delivered and measured by the host. It cannot be established by adding another operating instruction. Useful learning remains unproven until the proposed end-to-end task experiment supplies evidence.

## Subsequent pstack review

The [pstack decision review](2026-11-08-pstack-decision-review.md) reproduced a procedure identity/version gap and a malformed-input error-boundary gap in the retained implementation. It also confirmed the quality-only evaluation constraint and the need for final authorization freshness checks. These findings refine the acceptance conditions above; they do not validate the unbuilt standalone runtime. No production code or policy was changed by that review.
