# Memory baseline validation — 2026-11-07

Status: implemented locally; live comparison awaits additional model-attempt authorization. No model attempts were made for this experiment.

## Implemented and checked

The [baseline](../evaluation/MEMORY_BASELINE.md) uses scoped SQLite metadata and structured values, private Markdown notes, a generated bounded index, explicit corrections, expiry filtering and all-revision forgetting within the current store. It does not change installed skills or enable background retrieval.

**65 automated tests passed**, including the existing controller/lifecycle suite. The package checker passed. Memory checks cover restart persistence, correction identity, exclusion of superseded values, timezone-aware expiry, inference exclusion, project/flavour/owner mismatch, note and structured storage, all-revision deletion, index overflow rollback, context overflow, tamper detection, orphan recovery, credential refusal and the public CLI's create/retrieve/forget flow. Frozen benchmark inputs are scope checked; modifying their file during an attempt invalidates the result.

The six-scenario scripted comparison completed all **12 fixture attempts**:

| Scenario | No-memory result | Scoped-memory result |
|---|---|---|
| Delayed recall | Appropriate abstention | Correct narrative preference retrieved after reopening |
| Correction | Appropriate abstention | Correct revised value; predecessor absent |
| Stale memory | Appropriate abstention | Expired record absent; appropriate abstention |
| Deletion | Appropriate abstention | Deleted record absent; appropriate abstention |
| Cross-project access | Appropriate abstention | Other project denied through scoped API; sentinel absent |
| Task quality | Appropriate abstention | Remembered UTC offset applied correctly |

All fixture responses matched the answer or abstention appropriate for their available context. Target-answer utility was 0.5 without memory and 1.0 with memory, as deliberately constructed by the control tasks. The report's `improvement_observed` label describes the fixture measurements; it is **not evidence that Daphnie improved**. The same package snapshot was used in both arms. Protected acceptance and verified release remain blocked.

Retained control record: plan `394ad07dccce4a2fa3075641aac48576`, report `b0ae46cd69714012877183e2b938477a`, memory-input digest `b10e5da63eb730bf3c4f8159b2bfb262c54c4bfa74c900153da46cb1ce87d195`. Private inputs, attempts and HTML history remain outside the repository.

## Scope of evidence

These tests establish specific storage, retrieval and comparison mechanics. They do not validate a model's autonomous index maintenance, agent-operated file/SQL navigation, subjective task quality, long-term usefulness, poisoning resistance or host-enforced access isolation. Six public development cases are insufficient for a general effectiveness claim.

Forgetting covers the current memory store only. Earlier frozen benchmark inputs, exported reports, backups and model sessions remain outside its erasure boundary. Do not capture real memory stores in the immutable change ledger.

The proposed live test requires twelve new attempts using the configured model. Earlier live allowances from the controller and lifecycle work are already used; no further allowance is assumed. No publication, active library update or production-memory migration is part of this validation.
