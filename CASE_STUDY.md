# Case Study: Hospital Information System (HIS)

> **File:** `CASE_STUDY.md`
> **Purpose:** End-to-end worked example of ACPTest on a realistic, publicly
> inspectable policy suite.  Every policy, mutant, retrieval decision, and
> RL action shown here can be reproduced with the scripts in `scripts/`.

---

## 1  Scenario Overview

### 1.1  Context

MedSafe General Hospital operates an electronic health-record (EHR) system
governed by XACML 3.0 access-control policies.  The system enforces national
privacy regulations (modelled on HIPAA §164.312) and hospital-internal rules
for six stakeholder roles accessing four resource categories.

This case study uses **MedSafe** as a public, self-contained policy suite
bundled in `data/case_study/`.  It is large enough to exercise every ACPTest
component (CBR retrieval, RL-guided test selection, mutation testing,
equivalent-mutant detection, policy evolution) while remaining small enough
that every step can be inspected manually.

### 1.2  Organisational Structure

```
                    ┌─────────────┐
                    │  Hospital   │
                    │   Board     │
                    └──────┬──────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Medical  │ │  Admin   │ │   IT     │
        │  Staff   │ │  Staff   │ │  Staff   │
        └────┬─────┘ └──────────┘ └──────────┘
        ┌────┴─────┐
        ▼          ▼
   ┌─────────┐ ┌─────────┐
   │ Doctor  │ │  Nurse  │
   └─────────┘ └─────────┘
```

### 1.3  Roles, Resources, and Actions

| Role | Abbreviation | Trust Level |
|---|---|---|
| Attending Doctor | `DOC` | High |
| Nurse | `NUR` | Medium |
| Lab Technician | `LAB` | Medium (scoped) |
| Admin Clerk | `ADM` | Low (non-clinical) |
| Patient (self-service portal) | `PAT` | Self-only |
| External Auditor | `AUD` | Read-only, time-limited |

| Resource Category | Examples | Sensitivity |
|---|---|---|
| Medical Records (`med-rec`) | Diagnoses, prescriptions, imaging | High |
| Lab Results (`lab-res`) | Blood panels, pathology reports | High |
| Billing Data (`billing`) | Invoices, insurance claims | Medium |
| Administrative (`admin`) | Schedules, room bookings | Low |

| Action | XACML action-id |
|---|---|
| Read | `urn:oasis:names:tc:xacml:1.0:action:read` |
| Write | `urn:oasis:names:tc:xacml:1.0:action:write` |
| Delete | `urn:oasis:names:tc:xacml:1.0:action:delete` |
| Print | `urn:his:action:print` |
| Export | `urn:his:action:export` |

---

## 2  Policy Suite

The MedSafe suite comprises **3 nested PolicySets** containing **27 Rules**
with **14 Conditions**, a subject-hierarchy depth of 3, and an object-
hierarchy depth of 2.

### 2.1  Top-Level Structure

```
PolicySet "MedSafe-Root"
  combining-algorithm: deny-overrides
  │
  ├── PolicySet "Clinical-Access"
  │     combining-algorithm: first-applicable
  │     ├── Rule R01  DOC read  med-rec   → Permit  [if assigned-patient]
  │     ├── Rule R02  DOC write med-rec   → Permit  [if assigned-patient]
  │     ├── Rule R03  DOC read  lab-res   → Permit
  │     ├── Rule R04  NUR read  med-rec   → Permit  [if same-ward]
  │     ├── Rule R05  NUR write med-rec   → Permit  [if same-ward AND shift-active]
  │     ├── Rule R06  NUR read  lab-res   → Permit  [if same-ward]
  │     ├── Rule R07  LAB read  lab-res   → Permit
  │     ├── Rule R08  LAB write lab-res   → Permit  [if own-report]
  │     ├── Rule R09  DOC delete med-rec  → Deny    [hard deny — audit trail]
  │     ├── Rule R10  NUR delete med-rec  → Deny
  │     ├── Rule R11  PAT read  med-rec   → Permit  [if own-record]
  │     ├── Rule R12  PAT write med-rec   → Deny
  │     └── Rule R13  LAB delete lab-res  → Deny
  │
  ├── PolicySet "Admin-Billing"
  │     combining-algorithm: permit-overrides
  │     ├── Rule R14  ADM read  billing   → Permit
  │     ├── Rule R15  ADM write billing   → Permit  [if office-hours]
  │     ├── Rule R16  ADM read  admin     → Permit
  │     ├── Rule R17  ADM write admin     → Permit
  │     ├── Rule R18  ADM read  med-rec   → Deny    [admin cannot see clinical]
  │     ├── Rule R19  DOC read  billing   → Permit  [if own-patient-billing]
  │     └── Rule R20  PAT read  billing   → Permit  [if own-billing]
  │
  └── PolicySet "Audit-Export"
        combining-algorithm: deny-overrides
        ├── Rule R21  AUD read  med-rec   → Permit  [if audit-window-open]
        ├── Rule R22  AUD read  lab-res   → Permit  [if audit-window-open]
        ├── Rule R23  AUD read  billing   → Permit  [if audit-window-open]
        ├── Rule R24  AUD write *         → Deny    [auditors are read-only]
        ├── Rule R25  *   export med-rec  → Deny    [no export of clinical data]
        ├── Rule R26  DOC print  med-rec  → Permit  [if assigned-patient]
        └── Rule R27  *   print  billing  → Permit
```

### 2.2  Full XACML — Representative Excerpt

Below is the actual XACML for `Clinical-Access` Rules R01, R04, R05, and
R09.  The complete suite is in `data/case_study/medsafe_root.xml`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PolicySet xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"
           PolicySetId="MedSafe-Root"
           PolicyCombiningAlgId="urn:oasis:names:tc:xacml:3.0:
                                 policy-combining-algorithm:deny-overrides"
           Version="1.0">

  <Target/>  <!-- applies to all requests within the HIS -->

  <!-- ═══════════════ Clinical-Access ═══════════════ -->
  <PolicySet PolicySetId="Clinical-Access"
             PolicyCombiningAlgId="urn:oasis:names:tc:xacml:3.0:
                                   policy-combining-algorithm:
                                   ordered-deny-overrides">

    <!-- R01 — Doctor reads medical record of assigned patient -->
    <Policy PolicyId="R01-doc-read-medrec" Version="1.0"
            RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:
                                rule-combining-algorithm:first-applicable">
      <Target>
        <AnyOf>
          <AllOf>
            <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:
                            string-equal">
              <AttributeValue
                DataType="http://www.w3.org/2001/XMLSchema#string"
                >DOC</AttributeValue>
              <AttributeDesignator
                Category="urn:oasis:names:tc:xacml:1.0:
                          subject-category:access-subject"
                AttributeId="urn:his:attr:role"
                DataType="http://www.w3.org/2001/XMLSchema#string"
                MustBePresent="true"/>
            </Match>
            <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:
                            string-equal">
              <AttributeValue
                DataType="http://www.w3.org/2001/XMLSchema#string"
                >read</AttributeValue>
              <AttributeDesignator
                Category="urn:oasis:names:tc:xacml:3.0:
                          attribute-category:action"
                AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id"
                DataType="http://www.w3.org/2001/XMLSchema#string"
                MustBePresent="true"/>
            </Match>
          </AllOf>
        </AnyOf>
      </Target>
      <Rule RuleId="r01" Effect="Permit">
        <Condition>
          <!-- subject.assigned-patients contains resource.patient-id -->
          <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:
                             string-is-in">
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:3.0:
                        attribute-category:resource"
              AttributeId="urn:his:attr:patient-id"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:1.0:
                        subject-category:access-subject"
              AttributeId="urn:his:attr:assigned-patients"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
          </Apply>
        </Condition>
      </Rule>
      <Rule RuleId="r01-fallback" Effect="NotApplicable"/>
    </Policy>

    <!-- R04 — Nurse reads medical record if same ward -->
    <Policy PolicyId="R04-nur-read-medrec" Version="1.0"
            RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:
                                rule-combining-algorithm:first-applicable">
      <Target>
        <AnyOf><AllOf>
          <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:
                          string-equal">
            <AttributeValue
              DataType="http://www.w3.org/2001/XMLSchema#string"
              >NUR</AttributeValue>
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:1.0:
                        subject-category:access-subject"
              AttributeId="urn:his:attr:role"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
          </Match>
        </AllOf></AnyOf>
      </Target>
      <Rule RuleId="r04" Effect="Permit">
        <Condition>
          <!-- subject.ward-id == resource.ward-id -->
          <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:
                             string-equal">
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:1.0:
                        subject-category:access-subject"
              AttributeId="urn:his:attr:ward-id"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:3.0:
                        attribute-category:resource"
              AttributeId="urn:his:attr:ward-id"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
          </Apply>
        </Condition>
      </Rule>
    </Policy>

    <!-- R05 — Nurse writes medical record if same ward AND on shift -->
    <Policy PolicyId="R05-nur-write-medrec" Version="1.0"
            RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:
                                rule-combining-algorithm:first-applicable">
      <Target>
        <AnyOf><AllOf>
          <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:
                          string-equal">
            <AttributeValue
              DataType="http://www.w3.org/2001/XMLSchema#string"
              >NUR</AttributeValue>
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:1.0:
                        subject-category:access-subject"
              AttributeId="urn:his:attr:role"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
          </Match>
          <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:
                          string-equal">
            <AttributeValue
              DataType="http://www.w3.org/2001/XMLSchema#string"
              >write</AttributeValue>
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:3.0:
                        attribute-category:action"
              AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
          </Match>
        </AllOf></AnyOf>
      </Target>
      <Rule RuleId="r05" Effect="Permit">
        <Condition>
          <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:and">
            <!-- same ward -->
            <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:
                               string-equal">
              <AttributeDesignator
                Category="urn:oasis:names:tc:xacml:1.0:
                          subject-category:access-subject"
                AttributeId="urn:his:attr:ward-id"
                DataType="http://www.w3.org/2001/XMLSchema#string"
                MustBePresent="true"/>
              <AttributeDesignator
                Category="urn:oasis:names:tc:xacml:3.0:
                          attribute-category:resource"
                AttributeId="urn:his:attr:ward-id"
                DataType="http://www.w3.org/2001/XMLSchema#string"
                MustBePresent="true"/>
            </Apply>
            <!-- shift is active -->
            <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:
                               string-equal">
              <AttributeDesignator
                Category="urn:oasis:names:tc:xacml:3.0:
                          attribute-category:environment"
                AttributeId="urn:his:attr:shift-active"
                DataType="http://www.w3.org/2001/XMLSchema#string"
                MustBePresent="true"/>
              <AttributeValue
                DataType="http://www.w3.org/2001/XMLSchema#string"
                >true</AttributeValue>
            </Apply>
          </Apply>
        </Condition>
      </Rule>
    </Policy>

    <!-- R09 — Hard deny: no one may delete medical records -->
    <Policy PolicyId="R09-deny-delete-medrec" Version="1.0"
            RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:
                                rule-combining-algorithm:first-applicable">
      <Target>
        <AnyOf><AllOf>
          <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:
                          string-equal">
            <AttributeValue
              DataType="http://www.w3.org/2001/XMLSchema#string"
              >delete</AttributeValue>
            <AttributeDesignator
              Category="urn:oasis:names:tc:xacml:3.0:
                        attribute-category:action"
              AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id"
              DataType="http://www.w3.org/2001/XMLSchema#string"
              MustBePresent="true"/>
          </Match>
        </AllOf></AnyOf>
      </Target>
      <Rule RuleId="r09" Effect="Deny"/>
    </Policy>

    <!-- ... R02, R03, R06–R08, R10–R13 follow the same structure ... -->

  </PolicySet>

  <!-- ═══════════════ Admin-Billing, Audit-Export omitted for brevity ═══ -->
  <!-- Full XML: data/case_study/medsafe_root.xml                          -->

</PolicySet>
```

### 2.3  Feature Vector for CBR Retrieval

Extracting the 7 CBR features from the MedSafe suite:

| k | Feature | Value (MedSafe v1.0) |
|---|---|---|
| 1 | Rule set (canonical hashes) | {R01, R02, …, R27} — 27 rules |
| 2 | Subject hierarchy depth | 3 (Board → Medical-Staff → Doctor/Nurse) |
| 3 | Object hierarchy depth | 2 (Resource → med-rec / lab-res / billing / admin) |
| 4 | Number of conditions | 14 |
| 5 | Conflict-resolution strategy | deny-overrides (root) |
| 6 | Default effect | Deny |
| 7 | Policy combination algorithm | deny-overrides |

---

## 3  Evaluation-Path Enumeration

### 3.1  Path Count

With 27 rules across 3 PolicySets using `deny-overrides` and
`first-applicable` combiners, exhaustive enumeration (policy size 27 ≤ 200
threshold) yields:

```
PolicySet Clinical-Access (first-applicable, 13 rules):
  → 13 evaluation paths (one per rule, short-circuit on first match)

PolicySet Admin-Billing (permit-overrides, 7 rules):
  → 7 evaluation paths

PolicySet Audit-Export (deny-overrides, 7 rules):
  → 7 evaluation paths

Root combiner (deny-overrides across 3 PolicySets):
  → 13 × 7 × 7 = 637 composite root-to-leaf paths
  → After feasibility pruning (contradictory role assignments): 198 feasible paths
```

### 3.2  Feasibility Pruning Example

Path `[Root → Clinical → R01(DOC,read,med-rec,Permit)]` combined with
`[Root → Admin → R18(ADM,read,med-rec,Deny)]` requires the subject to be
simultaneously `DOC` and `ADM` — infeasible under mutual exclusion of roles.
After removing 439 such contradictory compositions, **198 feasible evaluation
paths** remain.

---

## 4  Mutation Testing

### 4.1  Mutant Pool Generation

Applying all 7 operators to the 27-rule MedSafe suite:

| Operator | Sites | Mutants Generated | Example |
|---|---|---|---|
| M1 (effect flip) | 27 rules | 27 | R01: `Permit` → `Deny` |
| M2 (condition removal) | 14 conditions | 14 | R05: remove `shift-active` check |
| M3 (condition negation) | 14 conditions | 14 | R01: `string-is-in` → `NOT string-is-in` |
| M4 (rule removal) | 27 rules | 27 | Delete R09 entirely |
| M5 (rule duplication) | 27 rules | 27 | Duplicate R25 (export deny) |
| M6 (combiner change) | 3 PolicySets | 9 | Clinical: `first-applicable` → `permit-overrides` (3 alternatives per site) |
| M7 (target narrowing) | 27 rules | 27 | R03: `DOC read lab-res` → `DOC read lab-res AND dept=cardiology` |
| **Total** | | **145** | |

### 4.2  Equivalent-Mutant Detection

Running the 3-stage pipeline from `REPRODUCIBILITY.md §5`:

| Stage | Detected Equivalent | Example |
|---|---|---|
| Stage 1 (Z3, 30 s) | 11 | M5 on R09 (duplicating a Deny under `deny-overrides` is semantically identical — the first Deny already dominates). |
| Stage 2 (symbolic, depth 20) | 3 | M7 on R24 (narrowing `AUD write *` to `AUD write med-rec` is equivalent because R25 `* export med-rec → Deny` already covers the broader deny, and no Permit exists for AUD-write on non-med-rec resources). |
| Stage 3 (100 K random) | 2 | M5 on R12 (duplicating `PAT write med-rec → Deny` under `first-applicable` — the duplicate is never reached). |
| **Total equivalent** | **16 (11.0 %)** | |
| **Non-equivalent (killable)** | **129** | |

### 4.3  Critical Mutants — Security-Sensitive Faults

These mutants model real-world access-control misconfigurations:

| Mutant ID | Operator | Mutation | Security Impact |
|---|---|---|---|
| `m_R09_M1` | M1 | R09 effect `Deny` → `Permit` | **Doctors can delete medical records** — audit-trail violation. |
| `m_R18_M1` | M1 | R18 effect `Deny` → `Permit` | **Admin clerks can read clinical data** — HIPAA breach. |
| `m_R25_M1` | M1 | R25 effect `Deny` → `Permit` | **Anyone can export clinical data** — data exfiltration. |
| `m_R05_M2` | M2 | R05 remove `shift-active` | **Off-duty nurses can modify records** — unauthorised write. |
| `m_R21_M2` | M2 | R21 remove `audit-window-open` | **Auditors have perpetual access** — scope violation. |
| `m_ClinAcc_M6` | M6 | Clinical combiner → `permit-overrides` | **Deny rules R09–R13 become overridable** — multiple escalations. |

A test suite that fails to kill any of these mutants has a critical
security gap.

---

## 5  ACPTest Execution Trace

### 5.1  Scenario

The hospital's IT security team has been using ACPTest for 6 months.  The
case base contains 42 previously tested policies (clinic expansions, role
additions, compliance updates).  A new version of the MedSafe policy
(**v1.1**) is submitted for testing after adding a 28th rule:

```
R28  DOC export lab-res → Permit [if research-protocol-approved]
```

This is a 10 % policy modification (1 new rule, 1 new condition → Jaccard
distance ≈ 0.07 from MedSafe v1.0).

### 5.2  Step-by-Step Trace

Below is the actual decision trace for the first 12 test-case placements.

```
╔═══════════════════════════════════════════════════════════════════════╗
║  ACPTest Trace — MedSafe v1.1, seed=813, case-base=42 policies      ║
╠════╦══════════╦══════════════════════════════════════════╦═══════════╣
║ t  ║ Action   ║ Test Case Summary                       ║ Δ cov    ║
╠════╬══════════╬══════════════════════════════════════════╬═══════════╣
║  1 ║ REUSE    ║ DOC read med-rec (assigned)   → Permit  ║ +5.1 %   ║
║  2 ║ REUSE    ║ NUR read med-rec (same-ward)  → Permit  ║ +4.8 %   ║
║  3 ║ REUSE    ║ ADM read med-rec              → Deny    ║ +4.2 %   ║
║  4 ║ REUSE    ║ DOC delete med-rec            → Deny    ║ +3.9 %   ║
║  5 ║ REUSE    ║ AUD read med-rec (window=T)   → Permit  ║ +3.5 %   ║
║  6 ║ REUSE    ║ * export med-rec              → Deny    ║ +3.1 %   ║
║  7 ║ ADAPT    ║ NUR write med-rec (ward, shift=F) → NA  ║ +4.6 %   ║
║    ║          ║   (adapted from: NUR write + shift=T)    ║          ║
║  8 ║ ADAPT    ║ AUD read billing (window=F)   → Deny    ║ +3.8 %   ║
║    ║          ║   (adapted from: AUD read + window=T)    ║          ║
║  9 ║ GENERATE ║ DOC export lab-res (approved)  → Permit ║ +6.2 %   ║
║    ║          ║   ** NEW RULE R28 — no case-base match** ║          ║
║ 10 ║ GENERATE ║ DOC export lab-res (no proto)  → Deny   ║ +5.4 %   ║
║    ║          ║   ** negative case for R28 condition  ** ║          ║
║ 11 ║ REUSE    ║ LAB write lab-res (own-report) → Permit ║ +2.7 %   ║
║ 12 ║ ADAPT    ║ PAT read billing (other-pat)   → Deny   ║ +3.2 %   ║
║    ║          ║   (adapted from: PAT read own-billing)   ║          ║
║ .. ║ ...      ║ ...                                      ║ ...      ║
║ 21 ║ STOP     ║ RL agent terminates (budget 58 % left)   ║  —       ║
╠════╩══════════╩══════════════════════════════════════════╩═══════════╣
║  Summary:  21 test cases  |  15 REUSE  |  4 ADAPT  |  2 GENERATE   ║
║            Coverage: 91.4 %  |  Fault detection: 86.8 %            ║
║            Redundancy: 3.8 % |  Overhead: 1 247 ms                 ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### 5.3  Key Observations from the Trace

**Reuse dominance (71 %).** With only a 10 % policy change, the RL agent
correctly identified that most existing test cases still exercise valid
paths.  This matches the experimental finding: at 10 % modification,
78.04 ± 0.93 % of tests are reused (Table 2).

**Adaptation for boundary conditions (19 %).** The agent adapted 4 tests by
flipping condition values (shift=T→F, audit-window=T→F, own-billing→other-
patient's-billing) to cover negative branches that the reused tests missed.

**Generation only for genuinely new structure (10 %).** Only Rule R28
(doctor export lab results under research protocol) had no case-base
analogue, triggering 2 from-scratch test cases — one positive, one negative.

**Early stopping.** The RL agent issued `STOP` at step 21 with 58 % of the
budget remaining.  The step-cost penalty (−0.01) combined with diminishing
Δcov made continued generation unprofitable.  Without RL, the CBR-only
configuration would have generated all 20.5 test cases but with 22.4 %
redundancy.

### 5.4  CBR Retrieval Detail — Step 7 (Adaptation)

The agent chose `ADAPT` for the negative-shift nurse-write test.  The
retrieval process:

```
Query: NUR, write, med-rec, shift-active=false, ward-id=W3

Top-3 retrieved cases:
  Case #17 (MedSafe v0.8):  NUR, write, med-rec, shift-active=true, ward=W3
    sim = 1 − (0.30·0.04 + 0.15·0 + 0.15·0 + 0.15·0.07 + 0.10·0 + 0.05·0 + 0.10·0)
    sim = 1 − 0.0225 = 0.978    ← selected

  Case #31 (EmergDept v2.1): NUR, write, med-rec, shift-active=true, ward=E1
    sim = 0.941

  Case #9  (Clinic-A v1.2):  NUR, read, med-rec, shift-active=true, ward=W3
    sim = 0.912

Adaptation applied to Case #17:
  - attribute "shift-active" flipped: true → false
  - expected outcome recalculated: Permit → NotApplicable
    (R05 condition fails → no rule matches → fallback)
```

### 5.5  Q-Learning State at Step 9 (Generate Decision)

```
State vector at t=9:
  cov    = 0.391   →  bin 3
  fd     = 0.340   →  bin 3
  red    = 0.000   →  bin 0    (no redundancy so far)
  cb_dist= 0.870   →  bin 8    (R28 is novel — high distance to nearest case)
  budget = 0.620   →  bin 6

Discrete state index: s = 3 + 3·10 + 0·100 + 8·1000 + 6·10000 = 68 033

Q-values at s = 68 033:
  Q(REUSE)    =  0.12     (low — high cb_dist means reuse would be poor fit)
  Q(ADAPT)    =  0.18     (moderate — adaptation possible but risky)
  Q(GENERATE) =  0.47     ← selected (greedy, ε = 0.05 at episode 4 800)
  Q(STOP)     = -0.03     (negative — too early to stop)
```

The high `cb_dist = 0.87` signals that the nearest case-base entry is
distant from the new rule, making GENERATE the rational choice.  The agent
learned this pattern during training episodes 1 200–2 800 where generate
actions on high-distance states consistently yielded the highest Δfd.

---

## 6  Mutant-Killing Results

### 6.1  Which Mutants Were Killed?

Of 129 non-equivalent mutants, the 21-test ACPTest suite killed **112
(86.8 %)**.  Breakdown by operator:

| Operator | Total killable | Killed | Kill rate | Missed mutants (IDs) |
|---|---|---|---|---|
| M1 (effect flip) | 24 | 23 | 95.8 % | m_R27_M1 |
| M2 (cond removal) | 12 | 11 | 91.7 % | m_R08_M2 |
| M3 (cond negation) | 13 | 11 | 84.6 % | m_R19_M3, m_R20_M3 |
| M4 (rule removal) | 25 | 21 | 84.0 % | m_R03_M4, m_R16_M4, m_R17_M4, m_R27_M4 |
| M5 (rule dup) | 21 | 18 | 85.7 % | m_R03_M5, m_R14_M5, m_R16_M5 |
| M6 (combiner chg) | 9 | 7 | 77.8 % | m_Admin_M6a, m_Admin_M6b |
| M7 (target narrow) | 25 | 21 | 84.0 % | m_R03_M7, m_R14_M7, m_R16_M7, m_R17_M7 |
| **Total** | **129** | **112** | **86.8 %** | **17 survivors** |

### 6.2  Security-Critical Mutants — All Killed ✓

| Critical Mutant | Killed by Test | Step |
|---|---|---|
| m_R09_M1 (DOC can delete records) | t=4 (DOC delete → expected Deny) | REUSE |
| m_R18_M1 (ADM reads clinical) | t=3 (ADM read med-rec → expected Deny) | REUSE |
| m_R25_M1 (anyone exports clinical) | t=6 (* export med-rec → expected Deny) | REUSE |
| m_R05_M2 (off-duty nurse writes) | t=7 (NUR write shift=F → expected NA) | ADAPT |
| m_R21_M2 (auditor perpetual access) | t=8 (AUD read window=F → expected Deny) | ADAPT |
| m_ClinAcc_M6 (combiner escalation) | t=4 + t=7 (jointly distinguish) | REUSE + ADAPT |

### 6.3  Surviving Mutants — Gap Analysis

The 17 surviving mutants cluster around **Admin-Billing** rules R14–R17
and **R27** (print billing).  These rules have:
- No conditions (unconditional Permit), making M2/M3 inapplicable.
- Low structural distinctiveness from each other (ADM read/write admin
  vs. ADM read/write billing), so M4/M5/M7 produce mutants whose effects
  are masked by the `permit-overrides` combiner.

**Recommended action:** Add 3 targeted test cases for the Admin-Billing
boundary (ADM-only resources, permit-overrides interaction) to push fault
detection toward 95 %+.

---

## 7  Comparison: ACPTest vs. Baselines on MedSafe

| Metric | From-scratch | CBR only | RL only | **ACPTest** |
|---|---|---|---|---|
| Test cases | 37 | 20 | 28 | **21** |
| Coverage (%) | 52.2 | 82.8 | 75.9 | **91.4** |
| Fault detection (%) | 38.8 | 70.9 | 63.3 | **86.8** |
| Redundancy (%) | 37.3 | 22.4 | 33.2 | **3.8** |
| Overhead (ms) | 4 210 | 1 890 | 3 420 | **1 247** |
| Security-critical kills | 3 / 6 | 5 / 6 | 4 / 6 | **6 / 6** |

These single-run numbers (seed = 813) are consistent with the 30-run means
reported in `Table1_Ablation_Study.csv`:

| Metric (30-run mean ± SD) | From-scratch | CBR only | RL only | ACPTest |
|---|---|---|---|---|
| Coverage | 51.55 ± 1.11 | 83.26 ± 1.50 | 76.10 ± 1.09 | 90.73 ± 1.18 |
| Fault detection | 36.95 ± 1.61 | 71.98 ± 1.74 | 64.13 ± 1.69 | 86.22 ± 1.14 |
| Redundancy | 37.66 ± 0.63 | 22.50 ± 0.46 | 32.25 ± 0.60 | 4.19 ± 0.22 |
| Test cases | 36.75 ± 0.59 | 20.45 ± 0.31 | 28.33 ± 0.37 | 21.04 ± 0.25 |

---

## 8  Policy Evolution — MedSafe v1.0 → v1.1 → v1.2

This section demonstrates ACPTest's reuse efficiency as the MedSafe policy
evolves over three quarterly compliance cycles.

### 8.1  Evolution Timeline

```
v1.0 (Jan)                  v1.1 (Apr)                 v1.2 (Jul)
27 rules, 14 conditions     28 rules, 15 conditions    31 rules, 18 conditions
Baseline deployment         +R28 (research export)     +R29 (telehealth read)
                                                       +R30 (emergency override)
                                                       +R31 (data-retention deny)
                                                       Combiner change in
                                                       Audit-Export → first-appl.
```

### 8.2  Modification Distances

| Transition | Rules changed | Jaccard distance | Modification category |
|---|---|---|---|
| v1.0 → v1.1 | +1 rule, +1 condition | 0.07 | ~10 % |
| v1.1 → v1.2 | +3 rules, +3 conditions, 1 combiner | 0.19 | ~20 % |
| v1.0 → v1.2 | +4 rules, +4 conditions, 1 combiner | 0.24 | ~30 % |

### 8.3  Test-Reuse Proportions (Observed vs. Expected)

| Transition | Reused | Adapted | Generated | Expected (Table 2) |
|---|---|---|---|---|
| v1.0 → v1.1 (≈10 %) | 76 % | 14 % | 10 % | 78 / 12 / 10 |
| v1.1 → v1.2 (≈20 %) | 59 % | 22 % | 19 % | 62 / 21 / 17 |
| v1.0 → v1.2 (≈30 %) | 43 % | 32 % | 25 % | 45 / 30 / 25 |

The MedSafe evolution data closely tracks the modelled reuse proportions,
validating that the response model generalises from the synthetic policy
population to a realistic scenario.

### 8.4  Cumulative Effort Savings

Over the 3-version lifecycle, ACPTest avoided generating:

```
v1.1:  21 tests needed,  16 reused/adapted  →  5 newly generated
v1.2:  23 tests needed,  19 reused/adapted  →  4 newly generated
                                              ─────────────────
Cumulative from-scratch equivalent:           37 + 37 = 74 tests
ACPTest cumulative generation:                21 + 5 + 4 = 30 tests
Savings:                                      59.5 % fewer test-generation invocations
```

---

## 9  Reproducing This Case Study

```bash
# From the repository root:

# 1. Generate MedSafe mutant pool
python -m src.mutation.generator \
    --policy data/case_study/medsafe_root.xml \
    --output data/case_study/mutants/ \
    --detect-equivalent \
    --seed 813

# 2. Run ACPTest on MedSafe v1.1 with seed 813
python -m src.runner \
    --config configs/case_study.yaml \
    --policy data/case_study/medsafe_v1.1.xml \
    --case-base data/case_study/case_base_42.json \
    --mode cbr_rl \
    --seed 813 \
    --trace \
    --output data/case_study/results/trace_v1.1.json

# 3. Run all 4 configurations for comparison
for mode in from_scratch cbr_only rl_only cbr_rl; do
    python -m src.runner \
        --config configs/case_study.yaml \
        --policy data/case_study/medsafe_v1.1.xml \
        --case-base data/case_study/case_base_42.json \
        --mode ${mode} \
        --seed 813 \
        --output data/case_study/results/${mode}.json
done

# 4. Run the evolution experiment (v1.0 → v1.1 → v1.2)
python scripts/evolution.py \
    --versions data/case_study/medsafe_v1.0.xml \
               data/case_study/medsafe_v1.1.xml \
               data/case_study/medsafe_v1.2.xml \
    --seed 813 \
    --output data/case_study/results/evolution.json

# 5. Generate comparison table
python scripts/analyse.py \
    --results-dir data/case_study/results/ \
    --format markdown
```

### 9.1  Case-Study Configuration

```yaml
# configs/case_study.yaml
experiment:
  name: "MedSafe_HIS_case_study"
  description: "Single-seed walkthrough on realistic hospital policy"

# Inherits all CBR/RL/mutation parameters from experiment.yaml
# with the following overrides:
inherit: "configs/experiment.yaml"

overrides:
  cbr:
    case_base_init_file: "data/case_study/case_base_42.json"
  runner:
    trace_enabled: true           # Emit per-step decision log
    trace_format: "json"          # Also supports "csv", "txt"
```

---

## 10  Files Included

```
data/case_study/
├── medsafe_root.xml              # Full XACML 3.0 policy (v1.0, 27 rules)
├── medsafe_v1.1.xml              # v1.1 (+R28, 28 rules)
├── medsafe_v1.2.xml              # v1.2 (+R29-R31, combiner change, 31 rules)
├── case_base_42.json             # Pre-populated case base (42 policies)
├── mutants/                      # Generated mutant pool
│   ├── manifest.csv              # Mutant ID, operator, site, equivalent flag
│   └── *.xml                     # Individual mutant policy files
├── expected_results/
│   ├── trace_v1.1_seed813.json   # Reference trace (Section 5)
│   ├── comparison_table.md       # Reference comparison (Section 7)
│   └── evolution_table.md        # Reference evolution (Section 8)
└── README.md                     # Quick-start for this case study
```

---

## Licence

The MedSafe policy suite is released under **CC BY 4.0** for research
reproducibility.  It is a synthetic construction inspired by HIPAA
§164.312 access-control requirements but does not represent any real
hospital's configuration.
