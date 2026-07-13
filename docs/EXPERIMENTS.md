# Experimental Procedure and Reproduction Guide

> **File:** `docs/EXPERIMENTS.md`
> **Purpose:** This document provides a complete, step-by-step procedure for
> reproducing all experimental results reported in the paper.  It covers
> environment setup, execution of each experiment, result aggregation, and
> validation against reference outputs.  No communication with the authors
> is required; this document and the repository artefacts are self-contained.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Environment Setup](#2-environment-setup)
3. [Experimental Design Overview](#3-experimental-design-overview)
4. [Experiment 1 — Ablation Study (R = 30)](#4-experiment-1--ablation-study-r--30)
5. [Experiment 2 — Policy Evolution](#5-experiment-2--policy-evolution)
6. [Experiment 3 — MedSafe HIS Case Study](#6-experiment-3--medsafe-his-case-study)
7. [Running Individual Modules](#7-running-individual-modules)
8. [Result Aggregation and Table Generation](#8-result-aggregation-and-table-generation)
9. [Result Validation](#9-result-validation)
10. [Troubleshooting](#10-troubleshooting)
11. [Customising the Experiments](#11-customising-the-experiments)
12. [Command Reference](#12-command-reference)

---

## 1  System Requirements

### 1.1  Hardware
workstation equipped with an Intel Core i7-12700H
CPU, 32 GB RAM, and an NVIDIA RTX 3060 GPU. 

### 1.2  Software

| Software | Version | Notes |
|---|---|---|
| Python | 3.10 -- 3.12 | Tested on 3.11.7 |
| pip | >= 22.0 | |
| Git | >= 2.30 | |
| Bash | >= 4.0 | Requires `mapfile` (available on Linux and macOS by default) |
| Z3 (optional) | 4.12.x | Required only for Stage 1 equivalence detection; the pipeline degrades gracefully if Z3 is absent |

### 1.3  Operating System

Tested on Ubuntu 22.04 LTS, Ubuntu 24.04, and macOS 14 (Sonoma).
On Windows, WSL2 is required for the shell scripts.

---

## 2  Environment Setup

### 2.1  Clone the repository and create a virtual environment

```bash
# Step 1: Clone
git clone https://github.com/cuong-nguyenvan/ACPTest.git
cd ACPTest

# Step 2: Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (PowerShell)

# Step 3: Install dependencies
pip install -r requirements.txt              # core runtime (5 packages)
pip install -r requirements-dev.txt          # + pytest, matplotlib (recommended)
pip install -r requirements-optional.txt     # + z3 for equiv. detection (optional)
```

### 2.2  Verify the installation

```bash
python3 -c "
import numpy; print(f'numpy {numpy.__version__} OK')
import scipy; print(f'scipy {scipy.__version__} OK')
import pandas; print(f'pandas {pandas.__version__} OK')
import yaml; print(f'pyyaml OK')
import lxml; print(f'lxml OK')
import statsmodels; print(f'statsmodels OK')
try:
    import z3; print(f'z3 {z3.get_version_string()} OK')
except ImportError:
    print('z3 NOT INSTALLED (Stage 1 equivalence detection will be skipped)')
"
```

All lines should print `OK`.

### 2.3  Run the unit test suite

```bash
python3 -m pytest tests/ -v
# Expected: 15 tests passed, 0 failed
```

### 2.4  Directory layout after setup

```
ACPTest/
├── .venv/                 # virtual environment (not committed)
├── src/                   # source code
├── configs/               # configuration files and seeds
├── data/                  # policies, case base, and results
├── scripts/               # reproduction and analysis scripts
├── tests/                 # unit tests
└── docs/                  # documentation (this file)
```

---

## 3  Experimental Design Overview

The paper reports three experiments.  Each has a dedicated script.

| # | Experiment | Script | Duration | Primary output |
|---|---|---|---|---|
| 1 | Ablation study (30 runs x 4 configs) | `scripts/run_all.sh` | ~14 h | Tables 1--5, Chart |
| 2 | Policy evolution (10 / 20 / 30 % modification) | Integrated in Experiment 1 | -- | Table 2 |
| 3 | MedSafe HIS case study | `scripts/run_case_study.sh` | ~5 min | Execution trace, comparison |

### 3.1  Configurations under comparison

| Configuration | `--mode` flag | Description |
|---|---|---|
| From-scratch | `from_scratch` | All test cases generated de novo; no reuse or learning |
| CBR only | `cbr_only` | Case-Based Reasoning (retrieve, reuse, adapt) without RL |
| RL only | `rl_only` | Q-learning agent selects actions without a case base |
| **CBR + RL (ACPTest)** | `cbr_rl` | Full proposed approach combining both components |

### 3.2  Evaluation metrics

| Metric | Interpretation | Desirable direction |
|---|---|---|
| Coverage (%) | Fraction of evaluation paths exercised | Higher is better |
| Fault Detection (%) | Fraction of non-equivalent mutants killed | Higher is better |
| Test Cases | Number of test cases in the generated suite | Lower is more efficient |
| Redundancy (%) | Fraction of duplicate test cases | Lower is better |

---

## 4  Experiment 1 — Ablation Study (R = 30)

This is the primary experiment: 30 independent runs x 4 configurations x
100 policy configurations = **12 000 evaluations**.

### 4.1  Automated execution (recommended)

```bash
# From the repository root:
bash scripts/run_all.sh
```

The script performs three stages:
1. Generates the mutant pool for all policies.
2. Executes 30 seeds x 4 modes (automatically skipping runs whose output
   files already exist).
3. Aggregates the results into CSV tables.

### 4.2  Manual execution of a single run

To execute a single run (e.g., for debugging or incremental reproduction):

```bash
python3 -m src.runner \
    --config configs/experiment.yaml \
    --mode cbr_rl \
    --seed 813 \
    --run-id 7 \
    --output data/results/run_7_cbr_rl.json
```

### 4.3  Parallel execution across multiple cores

```bash
# Requires GNU Parallel (install: sudo apt install parallel)
cat configs/seeds.txt | parallel -j 8 --eta \
    'for mode in from_scratch cbr_only rl_only cbr_rl; do
        python3 -m src.runner \
            --config configs/experiment.yaml \
            --mode $mode \
            --seed {} \
            --run-id {#} \
            --output data/results/run_{#}_${mode}.json
    done'
```

### 4.4  Monitoring progress

```bash
# Count completed runs (expected: 120 = 30 x 4)
ls data/results/run_*.json 2>/dev/null | wc -l

# Identify missing runs
for r in $(seq 1 30); do
    for m in from_scratch cbr_only rl_only cbr_rl; do
        test -f "data/results/run_${r}_${m}.json" || echo "MISSING: run_${r}_${m}"
    done
done
```

### 4.5  Output format

Each `run_X_MODE.json` file contains:

```json
{
  "run_id": 7,
  "seed": 813,
  "mode": "cbr_rl",
  "num_configurations": 100,
  "elapsed_seconds": 423.5,
  "aggregate": {
    "coverage_percent": 90.6955,
    "fault_detection_percent": 85.4423,
    "redundancy_percent": 4.1602,
    "test_case_count": 21.1637
  },
  "metrics_per_config": [ ... ]
}
```

### 4.6  Reference results

After all 120 runs have completed, the aggregated statistics should
approximate the following values (Table 1):

| Configuration | Coverage (%) | Fault Det. (%) | Test Cases | Redundancy (%) |
|---|---|---|---|---|
| From-scratch | 51.55 +/- 1.11 | 36.95 +/- 1.61 | 36.75 +/- 0.59 | 37.66 +/- 0.63 |
| CBR only | 83.26 +/- 1.50 | 71.98 +/- 1.74 | 20.45 +/- 0.31 | 22.50 +/- 0.46 |
| RL only | 76.10 +/- 1.09 | 64.13 +/- 1.69 | 28.33 +/- 0.37 | 32.25 +/- 0.60 |
| **CBR + RL** | **90.73 +/- 1.18** | **86.22 +/- 1.14** | **21.04 +/- 0.25** | **4.19 +/- 0.22** |

---

## 5  Experiment 2 — Policy Evolution

This experiment evaluates test-reuse efficiency as the policy under test
undergoes incremental modifications at three levels: 10 %, 20 %, and 30 %.

### 5.1  Execution

The policy-evolution analysis is performed automatically as part of
`run_all.sh`.  To execute it independently:

```bash
python3 scripts/analyse.py \
    --results-dir data/results/ \
    --output-dir data/results/tables/
```

Alternatively, the evolution experiment can be run directly on the MedSafe
case-study policies:

```bash
python3 -c "
from src.runner import run_experiment
import yaml

with open('configs/experiment.yaml') as f:
    config = yaml.safe_load(f)

for level in [0.10, 0.20, 0.30]:
    config['policy']['modification_level'] = level
    result = run_experiment(config, 'cbr_rl', seed=813, run_id=1,
                            output_path=f'data/results/evolution_{int(level*100)}.json')
    print(f'{int(level*100)}%: {result[\"aggregate\"]}')"
```

### 5.2  Reference results (Table 2)

| Modification level | Reused (%) | Adapted (%) | Generated (%) |
|---|---|---|---|
| 10 % | 78.04 +/- 0.93 | 12.07 +/- 0.64 | 9.90 +/- 0.50 |
| 20 % | 61.96 +/- 0.78 | 20.83 +/- 0.58 | 17.21 +/- 0.43 |
| 30 % | 45.03 +/- 0.78 | 30.30 +/- 0.54 | 24.67 +/- 0.60 |

---

## 6  Experiment 3 — MedSafe HIS Case Study

This experiment provides an end-to-end walkthrough on a realistic 27-rule
Hospital Information System policy suite.
For a detailed narrative, see [CASE_STUDY.md](../CASE_STUDY.md).

### 6.1  Automated execution

```bash
bash scripts/run_case_study.sh
```

The script performs four stages:
1. Generates 145 first-order mutants from `medsafe_root.xml`.
2. Executes all four configurations on `medsafe_v1.1.xml` (seed = 813).
3. Records a 21-step execution trace for the CBR + RL configuration.
4. Produces a comparison table.

### 6.2  Manual step-by-step execution

```bash
# -- Stage 1: Generate the mutant pool --
python3 -m src.mutation.generator \
    --policy data/case_study/medsafe_root.xml \
    --output-dir data/case_study/mutants/ \
    --operators M1 M2 M3 M4 M5 M6 M7 \
    --detect-equivalent \
    --z3-timeout 30 \
    --sym-depth 20 \
    --rand-samples 100000 \
    --seed 813

# Verify: 145 mutants total, approximately 16 equivalent
wc -l data/case_study/mutants/manifest.csv   # 146 lines (header + 145)

# -- Stage 2: Execute From-scratch baseline --
python3 -m src.runner \
    --config configs/case_study.yaml \
    --mode from_scratch \
    --seed 813 \
    --run-id 1 \
    --output data/case_study/results/from_scratch.json

# -- Stage 3: Execute CBR only --
python3 -m src.runner \
    --config configs/case_study.yaml \
    --mode cbr_only \
    --seed 813 \
    --run-id 1 \
    --output data/case_study/results/cbr_only.json

# -- Stage 4: Execute RL only --
python3 -m src.runner \
    --config configs/case_study.yaml \
    --mode rl_only \
    --seed 813 \
    --run-id 1 \
    --output data/case_study/results/rl_only.json

# -- Stage 5: Execute CBR + RL (ACPTest) with trace --
python3 -m src.runner \
    --config configs/case_study.yaml \
    --mode cbr_rl \
    --seed 813 \
    --run-id 1 \
    --trace \
    --output data/case_study/results/cbr_rl.json

# -- Stage 6: Inspect the execution trace --
python3 -c "
import json
with open('data/case_study/results/cbr_rl.json') as f:
    data = json.load(f)
for step in data.get('trace', [])[:12]:
    print(f\"  Step {step['step']:2d} | {step['action']:8s} | cov={step.get('cov',0):.3f}\")
print('  ...')
print(f\"  Aggregate: {data['aggregate']}\")"
```

### 6.3  Policy evolution (v1.0 --> v1.1 --> v1.2)

```bash
# Evaluate each successive version of the MedSafe policy
for version in medsafe_root medsafe_v1.1 medsafe_v1.2; do
    echo "=== Evaluating ${version} ==="
    python3 -m src.runner \
        --config configs/case_study.yaml \
        --mode cbr_rl \
        --seed 813 \
        --run-id 1 \
        --output "data/case_study/results/${version}_cbr_rl.json"
done

# Compare results across versions
python3 -c "
import json
for v in ['medsafe_root', 'medsafe_v1.1', 'medsafe_v1.2']:
    with open(f'data/case_study/results/{v}_cbr_rl.json') as f:
        d = json.load(f)['aggregate']
    print(f\"{v:20s} | cov={d['coverage_percent']:.1f}%  fd={d['fault_detection_percent']:.1f}%  red={d['redundancy_percent']:.1f}%\")"
```

---

## 7  Running Individual Modules

Each component of the framework can be invoked independently for
inspection, debugging, or integration testing.

### 7.1  CBR Similarity — compute the distance between two policies

```bash
python3 -c "
from src.cbr.similarity import SimilarityEngine, PolicyFeatures

engine = SimilarityEngine()

# MedSafe v1.0
p1 = PolicyFeatures(
    rule_set={'R01','R02','R03','R04','R05','R06','R07','R08','R09',
              'R10','R11','R12','R13','R14','R15','R16','R17','R18',
              'R19','R20','R21','R22','R23','R24','R25','R26','R27'},
    subject_depth=3, object_depth=2, num_conditions=14,
    conflict_resolution='deny-overrides', default_effect='Deny',
    combination_algorithm='deny-overrides',
)

# MedSafe v1.1 (+R28)
p2 = PolicyFeatures(
    rule_set=p1.rule_set | {'R28'},
    subject_depth=3, object_depth=2, num_conditions=15,
    conflict_resolution='deny-overrides', default_effect='Deny',
    combination_algorithm='deny-overrides',
)

sim = engine.similarity(p1, p2)
dist = engine.distance(p1, p2)
print(f'Similarity:  {sim:.4f}')
print(f'Distance:    {dist:.4f}')
print(f'Jaccard distance (rule set): {1 - len(p1.rule_set & p2.rule_set) / len(p1.rule_set | p2.rule_set):.4f}')
"
```

### 7.2  Q-Learning — demonstrate state discretisation

```bash
python3 -c "
from src.rl.state import StateConfig, discretise, make_state_vector, state_to_bins

cfg = StateConfig(bins_per_dimension=10)
print(f'Total state space: {cfg.total_states:,}')

# State vector at step 9 (CASE_STUDY.md Section 5.5)
s = make_state_vector(cov=0.391, fd=0.340, red=0.000, cb_dist=0.870, budget=0.620)
idx = discretise(s, cfg)
bins = state_to_bins(idx, cfg)
print(f'Continuous state: {s}')
print(f'Bin assignments:  {bins}')
print(f'Discrete index:   {idx}')
"
```

### 7.3  Mutation — generate mutants for a single policy

```bash
python3 -m src.mutation.generator \
    --policy data/case_study/medsafe_root.xml \
    --output-dir /tmp/test_mutants/ \
    --operators M1 M4 \
    --seed 42

head -5 /tmp/test_mutants/manifest.csv
```

### 7.4  Path Enumeration — list evaluation paths

```bash
python3 -c "
from src.policy.parser import parse_policy_file
from src.policy.paths import enumerate_paths, _count_rules

policy = parse_policy_file('data/case_study/medsafe_root.xml')
rules = _count_rules(policy)
paths = enumerate_paths(policy, seed=42)
print(f'Rules: {rules}')
print(f'Paths: {len(paths)}')
for p in paths[:5]:
    print(f'  {\" -> \".join(p)}')
print('  ...')
"
```

### 7.5  Equivalence Detection — test a single mutant

```bash
python3 -c "
from src.mutation.equivalence import detect_equivalent

original = {'rules': [{'rule_id': 'R1', 'effect': 'Permit'}], 'policy_sets': []}
mutant   = {'rules': [{'rule_id': 'R1', 'effect': 'Deny'}],   'policy_sets': []}

result = detect_equivalent(original, mutant, z3_timeout=5, rand_samples=1000)
print(f'Equivalent: {result}')   # Expected: False (effect flip is distinguishable)
"
```

---

## 8  Result Aggregation and Table Generation

### 8.1  Generate all tables from raw results

```bash
python3 scripts/analyse.py \
    --results-dir data/results/ \
    --output-dir data/results/tables/ \
    --format csv
```

This produces the following files in `data/results/tables/`:

| File | Content |
|---|---|
| `Runs_Raw.csv` | Raw per-run data (480 rows = 30 runs x 4 configs x 4 metrics) |
| `Table1_Ablation_Study.csv` | Mean +/- SD per configuration |
| `Table4_Descriptive_Stats.csv` | Full descriptive statistics (mean, SD, 95 % CI, min, max) |
| `Table5_Paired_Tests.csv` | Paired t-test, Wilcoxon signed-rank, Cohen's d for all pairwise comparisons |

### 8.2  Output tables in Markdown format

```bash
python3 scripts/analyse.py \
    --results-dir data/results/ \
    --output-dir data/results/tables/ \
    --format markdown
```

### 8.3  Inspect statistical significance

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('data/results/tables/Table5_Paired_Tests.csv')
print(df[['Comparison','Metric','Cohen_d','Sig']].to_string(index=False))
"
```

---

## 9  Result Validation

### 9.1  Compare against reference values

```bash
python3 -c "
import pandas as pd

# Reference values from the paper
ref = {
    ('CBR + RL (ACPTest)', 'Coverage % (modelled)'): 90.73,
    ('CBR + RL (ACPTest)', 'Fault Detection % (modelled)'): 86.22,
    ('CBR + RL (ACPTest)', 'Redundancy % (modelled)'): 4.19,
    ('CBR + RL (ACPTest)', 'Test Cases (modelled)'): 21.04,
}

df = pd.read_csv('data/results/tables/Table4_Descriptive_Stats.csv')
for (config, metric), ref_val in ref.items():
    row = df[(df['Configuration']==config) & (df['Metric']==metric)]
    if not row.empty:
        got = row['Mean'].values[0]
        status = 'PASS' if abs(got - ref_val) < 0.5 else 'FAIL'
        print(f'  [{status}] {metric:35s}  ref={ref_val:.2f}  got={got:.2f}  delta={got-ref_val:+.2f}')
"
```

### 9.2  Internal consistency check

```bash
# Verify that CBR + RL dominates From-scratch on all 30 runs
python3 -c "
import pandas as pd
df = pd.read_csv('data/results/Runs_Raw.csv')
for metric in ['Coverage % (modelled)', 'Fault Detection % (modelled)']:
    cbr_rl = df[(df['Configuration']=='CBR + RL (ACPTest)') & (df['Metric']==metric)]['Value_modelled']
    scratch = df[(df['Configuration']=='From-scratch') & (df['Metric']==metric)]['Value_modelled']
    all_better = all(c > s for c, s in zip(cbr_rl, scratch))
    print(f'{metric}:')
    print(f'  CBR+RL > From-scratch on all 30 runs: {\"PASS\" if all_better else \"FAIL\"}')"
```

---

## 10  Troubleshooting

### 10.1  `ModuleNotFoundError: No module named 'src'`

The runner must be invoked from the repository root using `python3 -m`:

```bash
cd /path/to/ACPTest
python3 -m src.runner ...      # Correct
# python3 src/runner.py ...    # Incorrect
```

### 10.2  `ImportError: cannot import name 'z3'`

Z3 is an optional dependency.  If absent, Stage 1 of the equivalence
detection pipeline is skipped; Stages 2 and 3 operate normally.

```bash
pip install z3-solver==4.12.4.0    # To enable Stage 1
```

### 10.3  `FileNotFoundError: configs/seeds.txt`

Ensure the working directory is the repository root:

```bash
pwd                    # Must print /path/to/ACPTest
ls configs/seeds.txt   # Must exist
```

### 10.4  Results differ across runs with the same seed

With identical seeds, results are deterministic.  If small differences
are observed, verify:

- The same Python version is used (3.10 and 3.12 may produce different
  random sequences).
- The same NumPy version is installed (use the pinned versions in `requirements.txt` and `requirements-dev.txt`).
- Parallel execution does not affect reproducibility, as each run uses
  an independent seed.

### 10.5  Out-of-memory errors during the full 30-run experiment

Execute in smaller batches; the script automatically skips completed runs:

```bash
# The script detects existing output files and resumes
bash scripts/run_all.sh
```

---

## 11  Customising the Experiments

### 11.1  Changing the number of runs

Edit `configs/experiment.yaml`:

```yaml
runs:
  R: 50       # Increase from 30 to 50
```

Add 20 additional seeds to `configs/seeds.txt`.

### 11.2  Modifying Q-learning hyperparameters

Edit `configs/experiment.yaml`:

```yaml
rl:
  hyperparameters:
    alpha: 0.05             # Reduce the learning rate
    epsilon_min: 0.10       # Increase residual exploration
    training_episodes: 8000 # Extend training
```

### 11.3  Evaluating a new policy

Place the XACML file in `data/policies/` and execute:

```bash
python3 -m src.runner \
    --config configs/experiment.yaml \
    --mode cbr_rl \
    --seed 42 \
    --run-id 1 \
    --output data/results/custom_policy.json
```

### 11.4  Adjusting similarity weights

Edit `configs/experiment.yaml` under `cbr.similarity_weights`, or override
programmatically:

```python
from src.cbr.similarity import SimilarityEngine
engine = SimilarityEngine(weights={
    "rule_set_jaccard": 0.40,       # Increased
    "subject_depth": 0.10,
    "object_depth": 0.10,
    "num_conditions": 0.15,
    "conflict_resolution": 0.10,
    "default_effect": 0.05,
    "combination_algorithm": 0.10,
})
```

### 11.5  Executing a single configuration across all seeds

```bash
mapfile -t SEEDS < configs/seeds.txt
for r in $(seq 1 30); do
    python3 -m src.runner \
        --config configs/experiment.yaml \
        --mode cbr_rl \
        --seed ${SEEDS[$((r-1))]} \
        --run-id $r \
        --output data/results/run_${r}_cbr_rl.json
done
```

---

## 12  Command Reference

| Command | Description |
|---|---|
| `bash scripts/run_all.sh` | Reproduce all experiments (30 x 4 = 120 runs) |
| `bash scripts/run_case_study.sh` | Execute the MedSafe HIS case study (~5 min) |
| `bash scripts/gen_mutants.sh` | Generate the mutant pool for all policies |
| `python3 -m pytest tests/ -v` | Run the unit test suite |
| `python3 -m src.runner --config ... --mode ... --seed ... --run-id ... --output ...` | Execute a single experimental run |
| `python3 -m src.mutation.generator --policy ... --output-dir ...` | Generate mutants for a single policy |
| `python3 scripts/analyse.py --results-dir ... --output-dir ...` | Aggregate raw results into tables |

---

## Cross-References

| Topic | Document |
|---|---|
| Similarity weights, normalisation, discretisation, equivalence detection | [REPRODUCIBILITY.md](../REPRODUCIBILITY.md) |
| MedSafe HIS scenario, execution trace, mutant-killing analysis | [CASE_STUDY.md](../CASE_STUDY.md) |
| Project overview and repository structure | [README.md](../README.md) |
| All parameters in a single file | [configs/experiment.yaml](../configs/experiment.yaml) |
