-------------------------- MODULE SkillLifecycle --------------------------
EXTENDS Naturals, FiniteSets
CONSTANT Mode
Releases == {"baseline", "candidate"}
None == "none"
VARIABLES prepared, intact, capsules, active, activeKind, ledger, ledgerKind,
          history, phase, pending, pendingKind, confirmed, rollback,
          protectedEligible, reportedEligible, grant, grantValid, usedGrants,
          trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
          lastIntact, lastVerified, lastAuthorized, recovered, rolledBack
vars == <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind,
          history, phase, pending, pendingKind, confirmed, rollback,
          protectedEligible, reportedEligible, grant, grantValid, usedGrants,
          trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
          lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
Init == /\ prepared = {} /\ intact = Releases /\ capsules = {}
        /\ active = None /\ activeKind = "manual" /\ ledger = None /\ ledgerKind = "manual"
        /\ history = {} /\ phase = "idle" /\ pending = None /\ pendingKind = "manual"
        /\ confirmed = FALSE /\ rollback = FALSE /\ protectedEligible = FALSE
        /\ reportedEligible = FALSE /\ grant = None /\ grantValid = FALSE /\ usedGrants = {}
        /\ trialPassed = FALSE /\ report = "none"
        /\ lastConfirmed = TRUE /\ lastPrepared = TRUE /\ lastRollback = TRUE
        /\ lastIntact = TRUE /\ lastVerified = FALSE /\ lastAuthorized = FALSE
        /\ recovered = FALSE /\ rolledBack = FALSE
Prepare(r) == /\ phase = "idle" /\ r \notin prepared /\ prepared' = prepared \cup {r}
              /\ UNCHANGED <<intact, capsules, active, activeKind, ledger, ledgerKind, history,
                phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
                grant, grantValid, usedGrants, trialPassed, report, lastConfirmed, lastPrepared,
                lastRollback, lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
DevelopmentReport == /\ phase = "idle" /\ report = "none" /\ report' = "blocked"
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, grantValid, usedGrants, trialPassed, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
OfflineEligibility == /\ ~reportedEligible /\ reportedEligible' = TRUE
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible,
        grant, grantValid, usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
ReceiveProtectedEvaluation == /\ ~protectedEligible /\ protectedEligible' = TRUE
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, reportedEligible,
        grant, grantValid, usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
ReceiveGrant(kind) == /\ protectedEligible
    /\ ((kind = "trial" /\ grant = None) \/ (kind = "promote" /\ grant = "trial" /\ trialPassed))
    /\ grant' = kind /\ grantValid' = TRUE
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
ExpireGrant == /\ grantValid /\ grantValid' = FALSE
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
Authorization(kind) == /\ protectedEligible /\ grantValid
    /\ IF kind = "trial" THEN grant = "trial" /\ active = "baseline"
       ELSE grant = "promote" /\ active = "candidate" /\ activeKind = "trial" /\ trialPassed
Begin(r,c,rb,kind) == /\ phase = "idle" /\ active = ledger
    /\ r \in prepared /\ r \in intact
    /\ (c \/ Mode = "skip_confirmation")
    /\ (~rb \/ r \in history \/ Mode = "skip_rollback_history")
    /\ (kind = "manual" \/ (r = "candidate" /\ ~rb /\ Authorization(kind)
          /\ (IF kind = "trial" THEN "trial" ELSE "promote") \notin usedGrants))
    /\ phase' = "validated" /\ pending' = r /\ pendingKind' = kind
    /\ confirmed' = c /\ rollback' = rb
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        protectedEligible, reportedEligible, grant, grantValid, usedGrants, trialPassed, report,
        lastConfirmed, lastPrepared, lastRollback, lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
BuildSealedCopy == /\ phase = "validated" /\ capsules' = capsules \cup {pending} /\ phase' = "staged"
    /\ UNCHANGED <<prepared, intact, active, activeKind, ledger, ledgerKind, history, pending,
        pendingKind, confirmed, rollback, protectedEligible, reportedEligible, grant, grantValid,
        usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback, lastIntact,
        lastVerified, lastAuthorized, recovered, rolledBack>>
RecordIntent == /\ phase = "staged" /\ phase' = "intent"
    /\ usedGrants' = (IF pendingKind = "manual" THEN usedGrants
                     ELSE usedGrants \cup {IF pendingKind = "trial" THEN "trial" ELSE "promote"})
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, grantValid, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
PublishPointer == /\ phase = "intent" /\ (pendingKind = "manual" \/ Authorization(pendingKind))
    /\ active' = pending /\ activeKind' = pendingKind /\ phase' = "published"
    /\ lastConfirmed' = confirmed /\ lastPrepared' = (pending \in prepared)
    /\ lastRollback' = (~rollback \/ pending \in history)
    /\ lastIntact' = (pending \in capsules)
    /\ lastVerified' = (pendingKind = "verified" \/ Mode = "mark_verified")
    /\ lastAuthorized' = (pendingKind = "verified" /\ Authorization(pendingKind))
    /\ rolledBack' = (rolledBack \/ (rollback /\ active # None /\ active # pending))
    /\ trialPassed' = (IF pendingKind = "trial" THEN FALSE ELSE trialPassed)
    /\ UNCHANGED <<prepared, intact, capsules, ledger, ledgerKind, history, pending, pendingKind,
        confirmed, rollback, protectedEligible, reportedEligible, grant, grantValid, usedGrants,
        report, recovered>>
FinishHistory == /\ phase \in {"idle", "published"} /\ active # None
    /\ ledger' = active /\ ledgerKind' = activeKind /\ history' = history \cup {active} /\ phase' = "idle"
    /\ recovered' = (recovered \/ (ledger # active))
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, pending, pendingKind, confirmed,
        rollback, protectedEligible, reportedEligible, grant, grantValid, usedGrants, trialPassed,
        report, lastConfirmed, lastPrepared, lastRollback, lastIntact, lastVerified, lastAuthorized, rolledBack>>
ObserveSuccessfulTrial == /\ phase = "idle" /\ active = ledger /\ activeKind = "trial" /\ ~trialPassed
    /\ trialPassed' = TRUE
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, grantValid, usedGrants, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
CrashOrAbort == /\ phase \in {"validated", "staged", "intent", "published"} /\ phase' = "idle"
    /\ UNCHANGED <<prepared, intact, capsules, active, activeKind, ledger, ledgerKind, history,
        pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, grantValid, usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
ChangePrepared(r) == /\ r \in prepared /\ r \in intact /\ intact' = intact \ {r}
    /\ UNCHANGED <<prepared, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, grantValid, usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
RestorePrepared(r) == /\ r \in prepared /\ r \notin intact /\ intact' = intact \cup {r}
    /\ UNCHANGED <<prepared, capsules, active, activeKind, ledger, ledgerKind, history,
        phase, pending, pendingKind, confirmed, rollback, protectedEligible, reportedEligible,
        grant, grantValid, usedGrants, trialPassed, report, lastConfirmed, lastPrepared, lastRollback,
        lastIntact, lastVerified, lastAuthorized, recovered, rolledBack>>
Next == (\E r \in Releases: Prepare(r) \/ ChangePrepared(r) \/ RestorePrepared(r))
    \/ (\E r \in Releases, c \in BOOLEAN, rb \in BOOLEAN, kind \in {"manual", "trial", "verified"}: Begin(r,c,rb,kind))
    \/ (\E kind \in {"trial", "promote"}: ReceiveGrant(kind))
    \/ DevelopmentReport \/ OfflineEligibility \/ ReceiveProtectedEvaluation \/ ExpireGrant
    \/ BuildSealedCopy \/ RecordIntent \/ PublishPointer \/ FinishHistory \/ ObserveSuccessfulTrial \/ CrashOrAbort
Spec == Init /\ [][Next]_vars
TypeOK == /\ prepared \subseteq Releases /\ intact \subseteq Releases /\ capsules \subseteq Releases
          /\ active \in Releases \cup {None} /\ ledger \in Releases \cup {None}
          /\ history \subseteq Releases /\ phase \in {"idle", "validated", "staged", "intent", "published"}
NoUnconfirmedAdoption == lastConfirmed
PreparedBeforeAdoption == lastPrepared
RollbackPreviouslyActive == lastRollback
NeverMislabelVerified == (~lastVerified \/ lastAuthorized)
DevelopmentCannotApprove == report \in {"none", "blocked"}
IntactAtCommit == lastIntact
NoManualAdoptionReachable == active = None
NoRollbackReachable == ~rolledBack
NoRecoveryReachable == ~recovered
NoVerifiedReleaseReachable == ~lastVerified
=============================================================================
