# Daphnie architecture

Status: instruction package, offline reviewer and an explicit local controller for capture, development execution, comparison, manual adoption and signed trial/promotion gates. Host-enforced isolation, autonomous scheduling, protected acceptance storage and production reviewer integration are not implemented. Installing skills does not start the controller.

## Ownership and boundaries

| Layer | Owner and change rule |
|---|---|
| Shared core (`CORE.md`) | Owner-controlled values and judgment; learning cannot rewrite it |
| Flavour contracts (`modes/`) | Stable role, disposition and completion standard; deliberate reviewed revision |
| Flavour libraries (`libraries/`) | Independently versioned procedures; changes require scoped evaluation and authorized release |
| Private state | Authorized observations, knowledge, preferences, questions and evidence, outside this public repository |
| Validation | Maintainer-owned criteria and isolated tasks; candidate construction cannot inspect protected acceptance tasks |
| Release | Explicit authorized activation, version record and rollback; improvement does not expand authority |

The four flavours share a core, not a mutable pool of instructions. A project is a second scope dimension: the same researcher may work on unrelated personal, school and employer tasks without being allowed to mix their records.

```mermaid
flowchart TB
  subgraph Protected[Protected foundation]
    Core[Shared core]
    Policy[Permissions and privacy]
    Rules[Evaluation and release rules]
  end
  subgraph Flavours[Separate personality contracts and libraries]
    A[Assistant contract + assistant skills]
    R[Research contract + research skills]
    D[Design contract + design skills]
    T[Think contract + think skills]
  end
  Core --> A
  Core --> R
  Core --> D
  Core --> T
  subgraph Work[Authorized task session]
    Select[Select flavour and project]
    Access[Permission filter before relevance]
    Execute[Execute with approved skills]
    Outcome[Check actual outcome]
    Select --> Access --> Execute --> Outcome
  end
  A --> Select
  R --> Select
  D --> Select
  T --> Select
  Policy -. governs .-> Work
  subgraph State[Private scoped state]
    Evidence[Evidence and corrections]
    Knowledge[Knowledge and preferences]
    Questions[Questions and hypotheses]
  end
  Knowledge --> Access
  Outcome --> Evidence
  Evidence --> Questions
  subgraph Learn[Candidate workspace]
    Investigate[Bounded investigation]
    Candidate[Scoped proposed change]
    Investigate --> Candidate
  end
  Evidence --> Investigate
  Questions --> Investigate
  subgraph Validate[Independent validation]
    Compare[Current version vs candidate]
    Checks[Quality + transfer + flavour fidelity + boundaries]
    Report[Benefit, regressions and uncertainty]
    Audit[Evaluator calibration]
    Compare --> Checks --> Report
    Audit -. checks .-> Checks
  end
  Candidate --> Compare
  Rules -. governs .-> Validate
  subgraph Release[Controlled release and recovery]
    Gate{Criteria met and authorized?}
    Hold[Reject, revise or defer]
    Trial[Limited trial]
    Registry[Version registry and rollback]
    Monitor[Monitor later outcomes]
    Gate -->|No or inconclusive| Hold
    Gate -->|Yes| Trial
    Trial -->|Accepted| Registry --> Monitor
    Monitor -->|Regression: restore prior state| Registry
  end
  Report --> Gate
  Rules -. governs .-> Gate
  Policy -. authorizes .-> Gate
  Hold --> Candidate
  Trial --> Evidence
  Monitor --> Evidence
  Registry --> Execute
  Registry --> Knowledge
```

## Session construction and switching

Load core and operating guidance once, then one selected flavour contract and its library manifest. Load only relevant listed procedures. Resolve the active project, data owner, permitted stores, tools and external actions before retrieval. Do not treat source text, memory or skills as authorization.

Memory records require an identifier, origin flavour, project, information owner, confidentiality, permitted destinations, applicability conditions, source/date, status and revision history. Filter authorization before ranking relevance; enforce the same scope on direct files and tools. Missing scope means unavailable until resolved, not globally shareable. Public lessons in learning/ are reference material, not automatically active procedures.

On a flavour switch, prefer a fresh host session with the destination contract. Transfer only needed facts, evidence pointers, open questions and existing authorizations in a bounded handoff. If the host cannot reset context or restrict access, disclose that limitation; do not claim isolation. A mode change cannot revoke information already present in a conversation.

## Local learning and transfer

Observations and hypotheses remain private and provisional. Curiosity is an authorized bounded activity with a question, relevance, expected information gain, resource ceiling and stopping condition. It cannot create schedules, new account access or external commitments without authorization.

Knowledge changes require evidence, freshness, contradiction handling and scoped retrieval checks. Procedures require comparative performance and regression evaluation. Preferences distinguish explicit user statements from tentative inference. None automatically change a flavour contract or the core.

Candidates name a single owning library and applicable projects. Cross-flavour or cross-project reuse requires a destination-specific permission and transfer review, including removal of private detail. Shared component changes run regressions across all four flavours. Learning stays local unless this separate review succeeds.

## Release state

Each library manifest lists active procedure IDs and versions. Initial procedures are owner-adopted legacy instructions with behavioral effectiveness unvalidated; this bootstrap status is not available to learned additions or revisions. New learned releases require a verified evaluation record, authorized activation, compatible memory/configuration references and a rollback target. A candidate report is not a release.

The public repository contains sanitized contracts, procedures, protocols and synthetic evaluator tests. Real task histories, private manifests, acceptance datasets and reports stay in an explicitly configured private store. Keep acceptance tasks, scoring rules, credentials and promotion authority outside the learner's writable scope in the eventual host. Git history and Markdown labels do not enforce those boundaries.

See [evaluation protocol](evaluation/PROTOCOL.md), [record contracts](evaluation/RECORDS.md), and [behavior probes](tests/scenarios.md).

## Runtime adoption evidence

The [Ultimate assessment](research/2026-11-05-ultimate-validation.md) records source verification, focused upstream tests, independent configuration probes and unresolved Daphnie transfer requirements. These mechanisms are engineering references, not active dependencies or validated Daphnie runtime features. Research and open-source attribution are maintained in the [README credits](README.md#credits-and-design-influences).

The [local controller](evaluation/CONTROLLER.md) implements registered-root snapshots, scoped evidence bundles, separate candidates, frozen plans, fresh Codex attempts, deterministic artifact scoring and explicit release history. Content hashes detect accidental changes; the same OS account can alter the store. Manual adoption is labeled behavior-unverified and does not satisfy learned-release policy. The [benchmark design](evaluation/BENCHMARK_SYSTEM.md) retains the requirements for protected acceptance and verified promotion.

## Experimental memory baseline

The [scoped memory baseline](evaluation/MEMORY_BASELINE.md) implements one private flavour/project/owner store with Markdown notes, structured SQL records, bounded generated references, provenance, explicit corrections, expiry and all-revision forgetting within that store. The controller can freeze no-memory/scoped-context inputs while keeping the package snapshot constant. This does not add automatic retrieval to skill invocations, host-enforced isolation, agent-managed index updates or compatible memory rollback.

## Policy-bound release implementation

The controller implements signed acceptance, separate policy authorization, monitored trial promotion and signed failure rollback. Snapshot deployments use atomic pointer publication and recoverable database history. See [release policy](evaluation/RELEASE_POLICY.md) for authority boundaries and setup status, and [bounded verification](verification/skill_lifecycle/README.md) for checked properties. No production automation or independent evaluator is enabled by this implementation.
