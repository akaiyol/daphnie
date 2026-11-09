# Delegation, ownership and evaluation: source review

Date: 2026-11-08. Owner direction: permit automatic delegation within an approved policy, use existing task budgets, and make Daphnie accountable for all work including workers. This extends the [minimal-change adoption](../learning/journal/2026-11-08-minimal-effective-changes.md); it does not approve new spending, app access or unattended execution.

## Linked posts and independent checks

Both direct X pages returned access errors. Their public text was retrieved through the FxTwitter text API. The returned author handles, post IDs and attached article IDs were checked; raw responses remain outside the public repository. No media was downloaded and no article-specific product commands were installed.

### Addy Osmani: management and verification

[Your coding agents made you a manager](https://x.com/addyosmani/status/2119332146485891501), attached article `2118901185377964033`, published 2026-11-08. Practical advice emphasizes clear outcomes, executable checks, bounded assignments, early correction, retained judgment and limiting simultaneous work. The adoption is Daphnie's responsibility for coordination and verified delivery, with owner-controlled governance. This is practitioner guidance, not measured proof that delegating improves Daphnie. Agent counts and cheap-rework claims are not adopted as guarantees.

The author's [January 8 predecessor](https://addyosmani.com/blog/coding-agents-manager/) was checked separately; it is not substituted for the linked November article.

### Sergii Makarevych: evaluate the system and the grader

[Evals: how to know whether an AI system actually works](https://x.com/sermakarevich/status/2106453816757354947), attached article `2106452411397165056`. Its useful distinction is between product outcomes, grader validity, trial consistency and monitoring. Its running tutorial is illustrative and was not reproduced here. No tutorial performance number or universal agreement threshold is adopted. Task-specific calibration remains necessary, and deterministic checks can establish meaningful outcomes when an appropriate ground truth exists.

One cited paper, [Reliability without Validity, arXiv:2606.19544](https://arxiv.org/abs/2606.19544), was withdrawn by arXiv administrators on 2026-11-03. The current record says it did not meet research-content quality standards. Its reported numerical results are excluded from this design's evidence. This does not by itself invalidate the article's other sources or general calibration advice.

### Research checked beyond the posts

| Primary source and method | Supported implication and limit |
|---|---|
| [Kim et al., Towards a Science of Scaling Agent Systems, v3](https://arxiv.org/html/2512.08296v3): 260 configurations, six benchmarks and matched reasoning budgets. | Coordination benefits depend on decomposability; sequential and tool-heavy tasks can lose capacity to overhead. Some coding evaluations use small subsets. The older 180-configuration blog summary is not the current paper's experimental count. This is no universal agent-count rule. |
| [Cemri et al., Why Do Multi-Agent LLM Systems Fail?, v3](https://arxiv.org/html/2503.13657v3): MAST taxonomy built from annotated traces, expanded to 1,600+ traces across seven frameworks. | Diagnose specification, coordination and verification failures separately. Role labels and clearer prompts alone do not establish reliable orchestration; the taxonomy is not exhaustive and does not prove a particular runtime correct. |
| [Anthropic, multi-agent research system](https://www.anthropic.com/research/multi-agent-research-system): engineering account and internal research evaluations. | Focused assignments, bounded effort and evidence-rich returns are useful design inputs. Its reported gains involve greater resource use; they do not establish superiority within Daphnie's fixed task allowance. |
| [Bodhwani, Tran and Wei, GAUGE](https://arxiv.org/html/2609.12191v1): compares judge rankings with verifiable reward across 25 agents and two simulated-task benchmarks. | Satisfaction and judge agreement can diverge from task completion, especially for close alternatives. Ground decisions in artifacts/tool state and calibrate on relevant outcomes. Simulated domains and a limited human panel constrain generalization to Daphnie's projects. |
| [Anthropic, Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents): agent-evaluation engineering guidance. | Use suitable code, model and human judgments, with actual outcome evidence and calibration. This supports the method, not fixed release cutoffs or proof that the current judge is adequate. |

These studies support selective, measured delegation. They do not establish that multiple agents, different model families or majority voting inherently improve correctness.

## Daphnie policy adopted

[Delegation contract](../DELEGATION.md) is the single detailed source; [OPERATING.md](../OPERATING.md) routes to it only before dispatch. Daphnie may choose useful bounded assignments automatically under the owner's standing direction. She owns every contribution from selection and context through resource use, monitoring, verification, integration, recovery and final reporting. The owner remains responsible for authorizing protected policy changes and external actions outside existing scope; workers do not gain that authority.

The initial operating limit is two direct workers concurrently, or a lower host limit, with no recursive spawning. This is a conservative implementation choice, not a measured optimum. All parent/worker work uses the same existing allowance. Workers have distinct output ownership; Daphnie integrates and performs final external mutations under the task's permissions. Their completion reports are submissions for verification, never automatic acceptance.

The [evaluation protocol](../evaluation/PROTOCOL.md) now clarifies worker versus task outcomes, grader false approvals/rejections, repeat consistency and calibration. It does not change the executable reviewer thresholds or let a learner's worker approve its own release.

## What is implemented and what needs a runtime

Implemented here: owner-directed shared guidance, delegation decision/ownership contract, source attribution, and the two regression-tested controller repairs described in the adoption record. Available host tools can be used under their actual controls. No new provider, model call allowance, scheduler or worker daemon is installed.

Still required for standalone execution: an authoritative task/worker ledger, durable budget reservations, enforced capability boundaries, supervised dispatch, cancellation/restart recovery, and independently configured release evaluation/authorization. Instructions do not supply those mechanisms. The earlier 93 tests and bounded release-model checks do not validate these missing worker controls.

A delegation pilot must compare direct and delegated execution under the same total allowance and task conditions. Measure verified completion, correctness, rework, resource use, latency, owner interventions and permission failures. Count the parent's briefing, review and integration overhead. Accept a worker's result only after inspecting its actual artifact/state. No such live pilot was run in this update.
