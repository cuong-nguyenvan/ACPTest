# ACPTest — Reproducibility & Technical Specification

> **Version 2.0** | Updated 2026-07-13 | Companion docs: [CASE_STUDY.md](CASE_STUDY.md), [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)

This document specifies every parameter, algorithm, and configuration needed to reproduce the reported results.

---

## 1  Similarity Function

### 1.1  Formula

```
sim(p, c)  =  1  -  sum_{k=1..7}  w_k * d_k(p_k, c_k)
```

### 1.2  Weights and Distance Functions

| k | Feature | Type | w_k | d_k |
|---|---------|------|-----|-----|
| 1 | Rule set | Set | 0.30 | Jaccard: 1 - |A∩B| / |A∪B| |
| 2 | Subject hierarchy depth | Ordinal | 0.15 | |rank(a)-rank(b)| / (L-1) |
| 3 | Object hierarchy depth | Ordinal | 0.15 | same as k=2 |
| 4 | Number of conditions | Numeric | 0.15 | |a-b| / (max-min), min-max scaled |
| 5 | Conflict-resolution strategy | Categorical | 0.10 | 0 if equal, 1 otherwise |
| 6 | Default effect (Permit/Deny) | Binary | 0.05 | 0 if equal, 1 otherwise |
| 7 | Combination algorithm | Categorical | 0.10 | 0 if equal, 1 otherwise |

### 1.3  How Weights Were Selected

| Step | What | Detail |
|------|------|--------|
| 1 | Expert seeding | Two experts (first author + collaborating security architect) independently ranked features. Geometric mean of rankings converted to weights via rank-reciprocal method. |
| 2 | LOO-CV | 50-fold leave-one-out on 50 labelled policy pairs (Cohen's kappa = 0.82). Objective: nearest-neighbour retrieval accuracy. Data: `data/calibration/weight_calibration_50.json`. |
| 3 | Grid refinement | Each weight perturbed in 0.05 steps across [0.00, 0.50], others re-normalised. 7 x 11 = 77 candidates evaluated. Best = 94% accuracy. |
| 4 | Sensitivity check | +/-0.05 perturbation on any weight changes mean coverage by < 0.8 pp. |

### 1.4  Rule Canonicalisation (for Jaccard)

Before comparing rule sets, each rule is reduced to a canonical string:

1. Parse `<Rule>` into (RuleId, Effect, Target, Condition).
2. Sort `<AllOf>`/`<AnyOf>` children by `AttributeId + AttributeValue`.
3. Sort `<Apply>` children by `FunctionId`, then `AttributeId`.
4. Strip comments, processing instructions, inter-element whitespace.
5. Concatenate: `Effect | sorted-Target | sorted-Condition`.

Two rules are identical iff their canonical strings match.

---

## 2  Feature Normalisation

### 2.1  Per-Feature Strategy

| k | Feature | Normalisation | Unseen values |
|---|---------|--------------|---------------|
| 1 | Rule set | None needed (Jaccard is already in [0,1]) | Empty sets: d=0 if both empty, d=1 if one empty |
| 2 | Subject depth | rank / (L-1), L=5 | New depth > L: extend L |
| 3 | Object depth | Same as k=2 | Same |
| 4 | Num conditions | Min-max: (x-min)/(max-min) | Clip to [0,1]; lazy update on new extremes |
| 5-7 | Categorical/Binary | None needed (mismatch=1) | Unseen category: d=1 |

### 2.2  Additional Details

| Topic | Specification |
|-------|--------------|
| **Outlier treatment** | Numeric feature k=4 winsorised at 2nd/98th percentiles before scaling. |
| **Refresh schedule** | Min/max/L recomputed from full case base at power-of-two sizes (8, 16, 32, 64, ...). Between boundaries: clip new values to current range or extend the bound without full recomputation. |
| **Cold start** | Empty case base: all d_k = 1.0, forcing GENERATE for the first test case. Initial case base seeded with 5 cases (`data/case_base_init/seed_cases.json`). |

---

## 3  Evaluation-Path Enumeration

### 3.1  Core Algorithm

```
EVAL-PATHS(node):
    if node is a leaf (rule): return { [node] }
    paths = {}
    for each child c:
        for each sub in EVAL-PATHS(c):
            paths = paths + { [node] ++ sub }
    return paths
```

### 3.2  Scaling Strategy

| Policy size (rules) | Strategy | Key details |
|---------------------|----------|-------------|
| <= 200 | **Exhaustive** (above) | Exact. Real policies yield < 10^4 paths (narrow DAGs, b in [2,4], d in [2,5]). |
| 201 -- 1000 | **Sub-tree pruning** | For `first-applicable` combiners: expand children only up to the first unconditional match. Other combiners: full expansion. Reduces branching ~40-60%. |
| > 1000 | **Monte-Carlo sampling** | Biased random walks using Thompson sampling. At each node, select child c_i by sampling theta_i ~ Beta(1 + new_path_hits_i, 1 + duplicate_hits_i) and choosing argmax. Stop when unique path count grows < 1% over 500 consecutive samples. Validated on 3 policies (800, 1200, 1500 rules) with < 2% error vs exhaustive. Validation data: `data/validation/path_enum_validation/`. |

### 3.3  Path Caching and Delta Enumeration

Paths are cached on disk keyed by SHA-256 of canonicalised policy XML.

**Delta enumeration** (when Jaccard distance to cached policy <= 0.30):
1. Compute symmetric difference of rule sets.
2. Find the lowest-common-ancestor combiner node for each changed rule.
3. Re-enumerate only those dirty sub-trees; retain clean sub-trees from cache.

---

## 4  Q-Learning State Discretisation

### 4.1  State Vector (5 dimensions, all in [0, 1])

| Dim | Symbol | Meaning |
|-----|--------|---------|
| 1 | cov | Cumulative path coverage |
| 2 | fd | Cumulative fault-detection rate |
| 3 | red | Redundancy ratio |
| 4 | cb_dist | Distance to nearest case in case base |
| 5 | budget | Remaining test-generation budget fraction |

### 4.2  Discretisation

Each dimension is split into B = 10 equal-width bins:

```
bin(x) = min(floor(x * 10), 9)
state_index = sum_{k=1..5} bin(x_k) * 10^(k-1)       |S| = 100,000
```

**Why equal-width?** State distributions shift during training (early: cov near 0, late: near 1). Equal-frequency bins computed from early data would become skewed. Equal-width is stable across episodes.

**Why B=10?** Grid search over {5, 8, 10, 15, 20} on 5 calibration policies. B=5 under-resolves gradients; B>=15 causes sparse visitation and non-convergence. Calibration policies: `data/calibration/calibration_policies/`.

### 4.3  Hyperparameters

| Parameter | Value | How selected |
|-----------|-------|-------------|
| alpha (learning rate) | 0.10 | Grid {0.01, 0.05, 0.10, 0.20} on 5 calibration policies |
| gamma (discount) | 0.95 | Validated at {0.90, 0.95, 0.99} |
| epsilon_0 (initial exploration) | 1.00 | Full exploration at start |
| epsilon_min | 0.05 | Residual exploration floor |
| epsilon decay | Linear over 3000 episodes | epsilon(t) = max(0.05, 1.0 - t/3000) |
| Training episodes | 5000 | Convergence: mean |TD-error| < 0.005 over 200 episodes. All 30 runs converged before episode 4200. Plot: `docs/figures/convergence_plot.png`. |
| Horizon (max steps) | 50 | Matches max test-suite size in calibration set |
| Q-table init | All zeros | Optimistic init unnecessary due to per-step cost |
| Tie-breaking | Uniform random among tied actions | Avoids index bias |

### 4.4  Actions

| Action | What it does |
|--------|-------------|
| REUSE (0) | Copy highest-similarity test case from case base as-is |
| ADAPT (1) | Retrieve nearest case, mutate inputs/outcomes to fit new policy |
| GENERATE (2) | Create a fresh test case from scratch |
| STOP (3) | End the test suite early |

### 4.5  Reward Function

```
r_t = 1.0 * delta_cov + 1.5 * delta_fd - 2.0 * delta_red - 0.01
```

| Coefficient | Value | Why |
|-------------|-------|-----|
| delta_cov | 1.0 | Baseline |
| delta_fd | 1.5 | Fault detection is the primary security objective |
| delta_red | -2.0 | Redundant tests waste execution budget |
| step_cost | -0.01 | Encourages shorter suites when marginal gains diminish |

**How coefficients were chosen:** grid search over delta_fd in {1.0, 1.5, 2.0} x delta_red in {-1.0, -1.5, -2.0, -2.5} on 5 calibration policies. Best: (1.5, -2.0) — highest fault detection while keeping redundancy < 5%. Data: `data/calibration/reward_sensitivity.csv`.

---

## 5  Equivalent-Mutant Detection

### 5.1  Mutation Operators (7 first-order)

| ID | Operator | What it does | Applied to |
|----|----------|-------------|------------|
| M1 | Effect flip | Permit <-> Deny | Every rule |
| M2 | Condition removal | Remove one condition | Every condition |
| M3 | Condition negation | c -> NOT(c) | Every condition |
| M4 | Rule removal | Delete entire rule | Every rule |
| M5 | Rule duplication | Insert copy after original | Every rule |
| M6 | Combiner change | Replace combining algorithm | Every PolicySet (3 alternatives each) |
| M7 | Target narrowing | Add an extra `<AllOf>` constraint from the policy's attribute vocabulary | Every rule with non-empty target |

Each operator is applied to every applicable site. Only first-order mutants (one operator, one site).

### 5.2  Three-Stage Equivalence Pipeline

A mutant that survives all three stages is classified as equivalent and excluded from the mutation score.

| Stage | Method | Parameters | What it proves |
|-------|--------|-----------|---------------|
| 1 | **Z3 constraint solving** | Timeout: 30s per mutant | Encodes `exists request: eval(P,req) != eval(M,req)`. UNSAT = provably equivalent. |
| 2 | **Bounded symbolic execution** | Depth limit: 20 rule evaluations | Custom DFS engine explores paths up to bound. No distinguishing input found = suspected equivalent. |
| 3 | **Differential random testing** | 100,000 uniform random requests | Requests sampled from Cartesian product of all roles x actions x resources x {true,false} for each boolean env attribute. No difference found = classified equivalent. |

**Stage 3 false-negative rate:** < 0.3%, estimated by comparison with exhaustive ground truth on 3 small policies (<= 20 rules). Validation data: `data/validation/equiv_detection_validation/`.

**Manual verification:** 30-mutant sample (10 equivalent, 20 non-equivalent) checked by two independent reviewers. Agreement: 100%.

### 5.3  Detection Results

| Statistic | Main experiment | MedSafe case study |
|-----------|----------------|-------------------|
| Mutants generated | 1,247 | 145 |
| Equivalent (Stage 1, Z3) | 89 (7.1%) | 11 (7.6%) |
| Equivalent (Stage 2, symbolic) | 23 (1.8%) | 3 (2.1%) |
| Equivalent (Stage 3, random) | 14 (1.1%) | 2 (1.4%) |
| **Total equivalent removed** | **126 (10.1%)** | **16 (11.0%)** |
| Non-equivalent (used for scoring) | 1,121 | 129 |

**Sensitivity:** removing Stage 3 shifts mean fault-detection by +0.4 pp — within the 95% CI.

---

## 6  Code, Seeds & Run Configuration

### 6.1  Repository Layout

```
ACPTest/
├── src/
│   ├── runner.py              # Experiment orchestrator (includes policy generation)
│   ├── cbr/                   # similarity.py, retrieval.py, adaptation.py, case_base.py
│   ├── rl/                    # q_learning.py, state.py, reward.py, actions.py
│   ├── mutation/              # operators.py, generator.py, equivalence.py
│   └── policy/                # parser.py, evaluator.py, paths.py
├── configs/
│   ├── experiment.yaml        # All parameters (mirrors this document)
│   ├── case_study.yaml        # MedSafe overrides
│   └── seeds.txt              # 30 seeds (listed below)
├── data/
│   ├── calibration/           # Weight calibration, reward sensitivity, calibration policies
│   ├── validation/            # Path-enumeration and equiv-detection validation data
│   ├── case_base_init/        # 5 seed cases (JSON)
│   ├── case_study/            # MedSafe XACML policies + mutants
│   └── results/               # Output (Runs_Raw.csv, Tables 1-5, Chart)
├── scripts/                   # run_all.sh, run_case_study.sh, gen_mutants.sh, analyse.py
└── tests/                     # test_similarity.py, test_q_learning.py, test_equivalence.py, test_paths.py
```

Note: policy generation is in `src/runner.py:_generate_policy()`, not a separate file.

### 6.2  Key Configuration (experiment.yaml)

The actual file uses nested YAML. Flat summary of all parameters:

| Block | Parameter | Value |
|-------|-----------|-------|
| random | seed_file | configs/seeds.txt |
| random | numpy_seed_offset / python_seed_offset | 0 / 1000 |
| cbr | similarity_weights | [0.30, 0.15, 0.15, 0.15, 0.10, 0.05, 0.10] |
| cbr | retrieval_k | 3 |
| cbr | adaptation_operators | input_mutate, outcome_flip, condition_remap |
| cbr | case_base init_size / max_size | 5 / 500 |
| rl | bins_per_dimension / dimensions | 10 / 5 |
| rl | alpha / gamma | 0.10 / 0.95 |
| rl | epsilon: start / min / decay_episodes | 1.00 / 0.05 / 3000 |
| rl | training_episodes / max_steps | 5000 / 50 |
| rl | reward: cov / fd / red / step_cost | 1.0 / 1.5 / -2.0 / -0.01 |
| mutation | operators | M1-M7, first-order only |
| mutation | equiv: z3_timeout / sym_depth / rand_samples | 30s / 20 / 100,000 |
| evaluation | path thresholds: exhaustive / pruning | 200 / 1000 |
| evaluation | MC: convergence_delta / window | 0.01 / 500 |
| policy | num_configurations | 100 |
| policy | modification_levels | 10%, 20%, 30% |
| runs | R / configurations | 30 / 4 (from_scratch, cbr_only, rl_only, cbr_rl) |

### 6.3  Random Seeds (30)

```
42  137  256  314  501  628  739  813  927  1042
1153  1271  1389  1504  1618  1732  1847  1963  2081  2197
2314  2436  2558  2673  2791  2908  3027  3141  3259  3378
```

### 6.4  Policy Generation Parameters

```
num_rules       = linear from 5 (config 1) to 60 (config 100)
subject_depth   = U(1, 5)
object_depth    = U(1, 5)
num_conditions  = U(0, 15)
combiner        = uniform choice from {first-applicable, deny-overrides,
                  permit-overrides, only-one-applicable}
default_effect  = uniform choice from {Permit, Deny}
hierarchy       = balanced tree of given depth, U(2,4) children per level,
                  unique leaf attribute values from namespace vocabulary
```

### 6.5  How to Reproduce

```bash
git clone https://github.com/cuong-nguyenvan/ACPTest.git
cd ACPTest
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt                # core runtime
pip install -r requirements-dev.txt            # + pytest, matplotlib (recommended)
pip install -r requirements-optional.txt       # + z3 (optional)

bash scripts/run_all.sh          # Full experiment: 30 x 4 runs (~14h on 64 cores)
bash scripts/run_case_study.sh   # MedSafe case study (~5 min)
```

Detailed step-by-step instructions: [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

### 6.6  Hardware

| Item | Value |
|------|-------|
| CPU | AMD EPYC 7763, 64 cores |
| GPU | None (CPU-only) |
| RAM | 256 GB DDR4 |
| OS | Ubuntu 22.04 LTS |
| Python | 3.11.7 |
| Full run | ~14 hours |

---

## 7  Data Dictionary

| File | Rows | Content |
|------|------|---------|
| `Runs_Raw.csv` | 480 | Raw values: Run (1-30) x Configuration (4) x Metric (4) |
| `Table1_Ablation_Study.csv` | 4 | Mean +/- SD per configuration (16 cells) |
| `Table1b_Ablation_Delta.csv` | 3 | Deltas vs From-scratch (12 cells) |
| `Table2_Policy_Evolution.csv` | 3 | Reuse/adapt/generate % at 10/20/30% modification |
| `Table3_RL_Contribution.csv` | 4 | CBR-only vs CBR+RL head-to-head |
| `Table4_Descriptive_Stats.csv` | 16 | Mean, SD, 95% CI, min, max, N per metric x config |
| `Table5_Paired_Tests.csv` | 24 | Paired t, Wilcoxon W, Cohen's d, Bonferroni-corrected p-values for all 6 pairs x 4 metrics |
| `Chart_Panel.png` | -- | Coverage + fault-detection (left axis) + overhead (right axis) vs 100 configs, LOESS trends, R=30 scatter |

---

## 8  Dependencies

| File | Packages | Purpose |
|------|----------|---------|
| `requirements.txt` | numpy, scipy, pandas, lxml, pyyaml | Runtime — sufficient to execute all experiments |
| `requirements-dev.txt` | + pytest, matplotlib, seaborn | Testing and figure generation |
| `requirements-optional.txt` | + z3-solver, scikit-learn, statsmodels, tqdm | Z3 for Stage 1 equiv. detection (skipped if absent); extended analysis |

```bash
pip install -r requirements.txt              # minimum
pip install -r requirements-dev.txt          # + test/plot
pip install -r requirements-optional.txt     # + z3, sklearn
```

---

## 9  Threats to Validity

| Type | Threat | Mitigation |
|------|--------|-----------|
| **Internal** | Simulated response model, not live PDP | Validated against Sun XACML PDP on 200 request-policy pairs (100% agreement) |
| **Internal** | Random variation | 30 independent seeds, all reported with SD and 95% CI |
| **External** | Synthetic policy pool | MedSafe case study (27-rule realistic policy) demonstrates applicability |
| **External** | XACML 3.0 only | Other languages (Cedar, OPA/Rego) need new parser + feature extractor |
| **Construct** | Mutation score as fault-detection proxy | 7 operators model common misconfigurations; may not cover all real-world faults |
| **Construct** | Residual false-negative in equiv. detection | < 0.3% (Stage 3); removing Stage 3 shifts results by only +0.4 pp |
| **Statistical** | Sample size R=30 | A priori power analysis: at alpha=0.05/24 (Bonferroni), d>=1.0, power > 0.99. Smallest observed d=1.467. |
