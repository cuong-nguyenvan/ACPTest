# Quick Start — How to Run ACPTest

Tested on Ubuntu 22.04 / Python 3.11. All commands run from the repository root.

---

## Step 1 — Download and Install

```bash
git clone https://github.com/cuong-nguyenvan/ACPTest.git
cd ACPTest

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt                # 5 core packages (numpy, scipy, pandas, lxml, pyyaml)
pip install -r requirements-dev.txt            # + pytest, matplotlib, seaborn
pip install -r requirements-optional.txt       # + z3-solver (optional)
```

## Step 2 — Verify Installation

```bash
python3 -c "
import numpy, scipy, pandas, lxml, yaml
print('All core packages OK')
"
```

Expected output: `All core packages OK`

---

## Step 3 — Run a Single Experiment

```bash
python3 -m src.runner \
    --config configs/experiment.yaml \
    --mode cbr_rl \
    --seed 813 \
    --run-id 1 \
    --output data/results/run_1_cbr_rl.json
```

**What this does:** runs the CBR+RL (ACPTest) configuration with seed 813
across 100 synthetic policy configurations and writes results to JSON.

**Expected output:**
```
INFO:src.policy.paths:Using exhaustive enumeration (5 rules)
INFO:src.policy.paths:Using exhaustive enumeration (6 rules)
...
INFO:__main__:Run 1 [cbr_rl] seed=813: coverage=...%, fd=...%, ...
```

**Inspect the result:**
```bash
python3 -c "
import json
with open('data/results/run_1_cbr_rl.json') as f:
    d = json.load(f)
for k, v in d['aggregate'].items():
    print(f'  {k}: {v}')
"
```

---

## Step 4 — Compare All 4 Configurations

```bash
for mode in from_scratch cbr_only rl_only cbr_rl; do
    echo "Running: $mode"
    python3 -m src.runner \
        --config configs/experiment.yaml \
        --mode $mode \
        --seed 813 \
        --run-id 1 \
        --output data/results/run_1_${mode}.json
done
```

**The 4 modes:**

| Mode | `--mode` flag | What it does |
|------|--------------|-------------|
| Baseline | `from_scratch` | Generate all tests from scratch, no reuse |
| CBR only | `cbr_only` | Retrieve + reuse/adapt from case base, no RL |
| RL only | `rl_only` | Q-learning selects actions, no case base |
| **ACPTest** | `cbr_rl` | Full method: CBR + RL combined |

---

## Step 5 — Generate Analysis Tables

```bash
python3 scripts/analyse.py \
    --results-dir data/results/ \
    --output-dir data/results/tables/ \
    --format csv
```

**Output files in `data/results/tables/`:**

| File | Content |
|------|---------|
| `Runs_Raw.csv` | Raw per-run values |
| `Table1_Ablation_Study.csv` | Mean +/- SD per configuration |
| `Table4_Descriptive_Stats.csv` | Full statistics (mean, SD, CI, min, max) |
| `Table5_Paired_Tests.csv` | Statistical tests (t-test, Wilcoxon, Cohen's d) |

---

## Step 6 — Full Reproduction (30 runs x 4 modes)

```bash
bash scripts/run_all.sh
```

This runs 120 experiments (30 seeds x 4 configurations x 100 policies each).
Takes ~14 hours on 64 cores, ~48 hours on 4 cores.
Automatically skips runs whose output files already exist.

---

## Step 7 — MedSafe Hospital Case Study

```bash
bash scripts/run_case_study.sh
```

This runs the end-to-end case study on a realistic 27-rule hospital
access-control policy. Takes ~5 minutes. Outputs to `data/case_study/results/`.

---

## Individual Module Demos

### Similarity — compute distance between two policies

```bash
python3 -c "
from src.cbr.similarity import SimilarityEngine, PolicyFeatures
engine = SimilarityEngine()
p1 = PolicyFeatures(rule_set={'R1','R2','R3'}, subject_depth=2, num_conditions=5)
p2 = PolicyFeatures(rule_set={'R1','R2','R4'}, subject_depth=3, num_conditions=8)
print(f'similarity = {engine.similarity(p1,p2):.4f}')
print(f'distance   = {engine.distance(p1,p2):.4f}')
"
```

Expected: `similarity = 0.7825`, `distance = 0.2175`

### Q-Learning State — discretise a continuous state

```bash
python3 -c "
from src.rl.state import StateConfig, discretise, make_state_vector, state_to_bins
cfg = StateConfig(bins_per_dimension=10)
s = make_state_vector(cov=0.391, fd=0.340, red=0.000, cb_dist=0.870, budget=0.620)
idx = discretise(s, cfg)
print(f'state index = {idx}')
print(f'bin indices = {list(state_to_bins(idx, cfg))}')
print(f'total |S|   = {cfg.total_states:,}')
"
```

Expected: `state index = 68033`, `bins = [3, 3, 0, 8, 6]`, `total = 100,000`

### Reward — compute a single-step reward

```bash
python3 -c "
from src.rl.reward import compute_reward
r = compute_reward(delta_cov=0.05, delta_fd=0.04, delta_red=0.001)
print(f'reward = {r:.4f}')
"
```

Expected: `reward = 0.0980` (= 1.0*0.05 + 1.5*0.04 - 2.0*0.001 - 0.01)

---

## Command Summary

| What | Command |
|------|---------|
| Install | `pip install -r requirements.txt` |
| Single run | `python3 -m src.runner --config configs/experiment.yaml --mode cbr_rl --seed 813 --run-id 1 --output out.json` |
| All 120 runs | `bash scripts/run_all.sh` |
| Case study | `bash scripts/run_case_study.sh` |
| Generate tables | `python3 scripts/analyse.py --results-dir data/results/ --output-dir data/results/tables/` |
| Run tests | `python3 -m pytest tests/ -v` (requires `requirements-dev.txt`) |

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| `ModuleNotFoundError: No module named 'src'` | Run from repo root with `python3 -m src.runner`, not `python3 src/runner.py` |
| `No module named 'yaml'` | `pip install -r requirements.txt` |
| `No module named 'z3'` | Optional — Stage 1 equiv. detection is skipped. Install: `pip install z3-solver` |
| `No module named 'pytest'` | `pip install -r requirements-dev.txt` |
| Different results with same seed | Check Python and NumPy versions match `requirements.txt` |
