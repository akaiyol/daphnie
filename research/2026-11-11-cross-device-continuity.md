# ADR: cross-device project continuity

Status: accepted for this scoped implementation; Windows and live recall validation pending.
Date: 2026-11-11. Decision authority: the owner's request to research and implement alternating Mac/Windows use with shared project memory.

## Context

The public instruction package must remain separate from private project evidence. Alternating use permits a single-writer handoff. Skill installations contain machine-local links; controller roots contain absolute paths. Portable memory must retain provenance without silently turning old context into instructions or permissions.

## Evidence

Sources accessed 2026-11-11:

- [OpenAI: local memories](https://learn.chatgpt.com/docs/customization/memories) describes separate local Codex memory stores, asynchronous generation and generated-state files. It does not establish supported cross-device replication of the full local profile.
- [OpenAI: Windows app](https://learn.chatgpt.com/docs/app/windows) and [WSL](https://learn.chatgpt.com/docs/windows/wsl) document WSL2, Linux-home checkouts, the agent environment setting and separate Windows/WSL Codex homes. Local source imports `fcntl` in the controller and experimental memory store, making WSL2 the compatible current Windows route.
- [OpenAI: skills](https://learn.chatgpt.com/docs/build-skills) documents local discovery and explicit invocation. Installing the same instruction package does not synchronize private context.
- [Git: pull](https://git-scm.com/docs/git-pull) documents fast-forward-only refusal when histories diverge. Normal pushes arbitrate conflicting remote branch advances without overwriting the competing commit.
- [SQLite: backup API](https://www.sqlite.org/backup.html) documents consistent database snapshots. [SQLite corruption guidance](https://www.sqlite.org/howtocorrupt.html) explains why copying live database files and omitting recovery journals can be unsafe.
- [Syncthing: synchronization](https://docs.syncthing.net/users/syncing.html) documents file/block transfer. That is not a transaction spanning a database, notes and controller state. A database transfer requires application-aware snapshots regardless of the file transport.

## Options considered

| Method | Benefits | Costs and limits | Decision |
|---|---|---|---|
| Public package Git + private Markdown Git, explicit handoff | Versioned context, no always-on server, works while the other computer is off, reviewable conflicts | User/agent must save a checkpoint and finish before switching; two repos are not atomic | Selected |
| Continuous file sync of the whole profile | Broad filesystem replication | Includes credentials and host state; generated stores and databases need lifecycle coordination; not established as supported Codex replication | Rejected for this scope |
| A central private memory service | One transactional authority, potential concurrent access | Authentication, hosting, backup and retrieval integration add maintenance; no requirement for concurrent writers | Deferred |
| Remote access to one canonical computer | One filesystem and runtime | Requires that host to remain reachable and awake; does not provide independent local work | Deferred |

## Decision

Use a private project-scoped Markdown repository alongside the public package, with a package revision pin and a persistent device claim. Require clean start states, fast-forward-only transitions and successful normal pushes. Preserve failed local commits for explicit recovery. Verify private GitHub visibility and identical fetch/push origins before uploading memory. Keep local config and links outside synced records.

Connect the private index through the operating contract's existing opt-in configuration. Do not change personality, flavour contracts, release gates or generated Codex memory. Historical project evidence can be copied as reviewed Markdown; complete chat reconstruction and automatic memory-engine migration are outside this implementation. SQLite/controller transfer remains a separately designed extension, not a file-sync side effect.

## Consequences and remaining checks

Shared project continuity is explicit and auditable. Recall still depends on the agent following the existing operating contract and host access permissions. A persistent claim discourages accidental concurrent sessions but is not access control or an authenticated distributed lock. The package and memory commits preserve coherent completed handoffs while failed operations require recovery.

Validate the actual Windows environment, skill discovery and a real save/switch/recall round trip. Before adding structured-memory transfer, define deletion across backups, lock ownership, atomic note/database capture and path remapping. No production improvement, all-chat access or isolation claim follows from synthetic handoff tests.
