-------------------------- MODULE SkillLifecycle --------------------------
EXTENDS Naturals, FiniteSets
CONSTANT Mode
Releases == {"baseline", "candidate"}
NoRelease == "none"
VARIABLES prepared, intact, active, history, pointer, phase, pending,
          confirmed, wasPrepared, rollback, report, reportedEligible,
          lastConfirmed, lastPrepared, lastRollback, lastIntact, lastVerified,
          recovered, rolledBack
vars == <<prepared, intact, active, history, pointer, phase, pending,
          confirmed, wasPrepared, rollback, report, reportedEligible,
          lastConfirmed, lastPrepared, lastRollback, lastIntact, lastVerified,
          recovered, rolledBack>>
Init == /\ prepared = {} /\ intact = Releases
        /\ active = NoRelease /\ history = {} /\ pointer = NoRelease
        /\ phase = "idle" /\ pending = NoRelease
        /\ confirmed = FALSE /\ wasPrepared = FALSE /\ rollback = FALSE
        /\ report = "none" /\ reportedEligible = FALSE
        /\ lastConfirmed = TRUE /\ lastPrepared = TRUE /\ lastRollback = TRUE
        /\ lastIntact = TRUE /\ lastVerified = FALSE
        /\ recovered = FALSE /\ rolledBack = FALSE
Prepare(r) == /\ phase = "idle" /\ r \notin prepared
              /\ prepared' = prepared \cup {r}
              /\ UNCHANGED <<intact, active, history, pointer, phase, pending,
                  confirmed, wasPrepared, rollback, report, reportedEligible,
                  lastConfirmed, lastPrepared, lastRollback, lastIntact,
                  lastVerified, recovered, rolledBack>>
DevelopmentReport == /\ phase = "idle" /\ report = "none" /\ report' = "blocked"
                     /\ UNCHANGED <<prepared, intact, active, history, pointer, phase,
                         pending, confirmed, wasPrepared, rollback, reportedEligible,
                         lastConfirmed, lastPrepared, lastRollback, lastIntact,
                         lastVerified, recovered, rolledBack>>
OfflineEligibility == /\ phase = "idle" /\ ~reportedEligible
                      /\ reportedEligible' = TRUE
                      /\ UNCHANGED <<prepared, intact, active, history, pointer, phase,
                          pending, confirmed, wasPrepared, rollback, report,
                          lastConfirmed, lastPrepared, lastRollback, lastIntact,
                          lastVerified, recovered, rolledBack>>
BeginAdoption(r, consent, isRollback) ==
    /\ phase = "idle" /\ r \in prepared /\ r \in intact
    /\ (consent \/ Mode = "skip_confirmation")
    /\ phase' = "validated" /\ pending' = r /\ confirmed' = consent
    /\ wasPrepared' = (r \in prepared) /\ rollback' = isRollback
    /\ UNCHANGED <<prepared, intact, active, history, pointer, report, reportedEligible,
         lastConfirmed, lastPrepared, lastRollback, lastIntact, lastVerified,
         recovered, rolledBack>>
CommitAdoption ==
    /\ phase = "validated"
    /\ (~rollback \/ pending \in history \/ Mode = "skip_rollback_history")
    /\ active' = pending /\ history' = history \cup {pending} /\ phase' = "committed"
    /\ lastConfirmed' = confirmed /\ lastPrepared' = wasPrepared
    /\ lastRollback' = (~rollback \/ pending \in history)
    /\ lastIntact' = (pending \in intact)
    /\ lastVerified' = (Mode = "mark_verified")
    /\ rolledBack' = (rolledBack \/ (rollback /\ active # NoRelease /\ active # pending))
    /\ UNCHANGED <<prepared, intact, pointer, pending, confirmed, wasPrepared,
         rollback, report, reportedEligible, recovered>>
RejectRollback == /\ phase = "validated" /\ rollback /\ pending \notin history
                  /\ Mode # "skip_rollback_history" /\ phase' = "idle"
                  /\ UNCHANGED <<prepared, intact, active, history, pointer, pending,
                      confirmed, wasPrepared, rollback, report, reportedEligible,
                      lastConfirmed, lastPrepared, lastRollback, lastIntact,
                      lastVerified, recovered, rolledBack>>
Reconcile == /\ phase \in {"idle", "committed"}
             /\ active # NoRelease /\ active \in intact
             /\ pointer' = active /\ phase' = "idle"
             /\ recovered' = (recovered \/ (pointer # active))
             /\ UNCHANGED <<prepared, intact, active, history, pending, confirmed,
                 wasPrepared, rollback, report, reportedEligible, lastConfirmed,
                 lastPrepared, lastRollback, lastIntact, lastVerified, rolledBack>>
Crash == /\ phase \in {"validated", "committed"} /\ phase' = "idle"
         /\ UNCHANGED <<prepared, intact, active, history, pointer, pending, confirmed,
             wasPrepared, rollback, report, reportedEligible, lastConfirmed,
             lastPrepared, lastRollback, lastIntact, lastVerified, recovered, rolledBack>>
ChangePackage(r) == /\ r \in prepared /\ r \in intact /\ intact' = intact \ {r}
                    /\ UNCHANGED <<prepared, active, history, pointer, phase, pending,
                        confirmed, wasPrepared, rollback, report, reportedEligible,
                        lastConfirmed, lastPrepared, lastRollback, lastIntact,
                        lastVerified, recovered, rolledBack>>
RestorePackage(r) == /\ r \in prepared /\ r \notin intact /\ intact' = intact \cup {r}
                     /\ UNCHANGED <<prepared, active, history, pointer, phase, pending,
                         confirmed, wasPrepared, rollback, report, reportedEligible,
                         lastConfirmed, lastPrepared, lastRollback, lastIntact,
                         lastVerified, recovered, rolledBack>>
LosePointer == /\ phase = "idle" /\ pointer # NoRelease /\ pointer' = NoRelease
               /\ UNCHANGED <<prepared, intact, active, history, phase, pending,
                   confirmed, wasPrepared, rollback, report, reportedEligible,
                   lastConfirmed, lastPrepared, lastRollback, lastIntact,
                   lastVerified, recovered, rolledBack>>
Next == (\E r \in Releases: Prepare(r) \/ ChangePackage(r) \/ RestorePackage(r))
        \/ (\E r \in Releases, c \in BOOLEAN, rb \in BOOLEAN: BeginAdoption(r,c,rb))
        \/ CommitAdoption \/ RejectRollback \/ Reconcile \/ Crash
        \/ LosePointer \/ DevelopmentReport \/ OfflineEligibility
Spec == Init /\ [][Next]_vars
TypeOK == /\ prepared \subseteq Releases /\ intact \subseteq Releases
          /\ active \in Releases \cup {NoRelease} /\ history \subseteq Releases
          /\ pointer \in Releases \cup {NoRelease}
          /\ phase \in {"idle", "validated", "committed"}
NoUnconfirmedAdoption == lastConfirmed
PreparedBeforeAdoption == lastPrepared
RollbackPreviouslyActive == lastRollback
NeverMislabelVerified == ~lastVerified
DevelopmentCannotApprove == report \in {"none", "blocked"}
IntactAtCommit == lastIntact
NoManualAdoptionReachable == active = NoRelease
NoRollbackReachable == ~rolledBack
NoRecoveryReachable == ~recovered
NoVerifiedReleaseReachable == ~lastVerified
=============================================================================
