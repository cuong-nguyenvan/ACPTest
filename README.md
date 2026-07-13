# ACPTest 🔐

> **Automated Test Suite Generation for Access Control Policies**
> Using Case-Based Reasoning and Reinforcement Learning

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
  <img src="https://img.shields.io/badge/Status-Research%20Code-orange" />
  <img src="https://img.shields.io/badge/XACML-3.0-blueviolet" />
  <img src="https://img.shields.io/badge/Algorithm-CBR%20%2B%20RL-informational" />
</p>

This repository contains the experimental artifact for the paper:

## Quick Start

```bash
git clone https://github.com/cuong-nguyenvan/ACPTest.git
cd ACPTest
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt              # core (5 packages)
pip install -r requirements-dev.txt          # + pytest, matplotlib, seaborn
pip install -r requirements-optional.txt     # + z3, scikit-learn (optional)

# Run the Hospital Information System case study
bash scripts/run_case_study.sh

# Reproduce all 30 × 4 experiments
bash scripts/run_all.sh
```

## Repository Structure

```
ACPTest/
├── README.md                      ← You are here
├── REPRODUCIBILITY.md             ← Full technical specification
├── CASE_STUDY.md                  ← Hospital Information System walkthrough
├── requirements.txt               ← Runtime dependencies (5 packages)
├── requirements-dev.txt           ← Test + plotting (pytest, matplotlib, seaborn)
├── requirements-optional.txt      ← Optional (z3-solver, scikit-learn, etc.)
├── LICENSE                        ← MIT License
├── .gitignore
│
├── src/                           ← Source code
│   ├── __init__.py
│   ├── runner.py                  ← Experiment orchestrator
│   ├── cbr/                       ← Case-Based Reasoning engine
│   │   ├── __init__.py
│   │   ├── similarity.py          ← Weighted heterogeneous distance
│   │   ├── retrieval.py           ← k-NN retrieval with tie-breaking
│   │   ├── adaptation.py          ← Test-case adaptation operators
│   │   └── case_base.py           ← Case-base management & persistence
│   ├── rl/                        ← Reinforcement Learning module
│   │   ├── __init__.py
│   │   ├── q_learning.py          ← Tabular Q-learning agent
│   │   ├── state.py               ← State discretisation (5-D → bins)
│   │   ├── reward.py              ← Reward function
│   │   └── actions.py             ← Action definitions
│   ├── mutation/                   ← Mutant generation & equivalence
│   │   ├── __init__.py
│   │   ├── operators.py           ← 7 mutation operators
│   │   ├── generator.py           ← First-order mutant generator
│   │   └── equivalence.py         ← 3-stage equivalence pipeline
│   └── policy/                    ← Policy representation & evaluation
│       ├── __init__.py
│       ├── parser.py              ← XACML 3.0 parser
│       ├── evaluator.py           ← Policy evaluation engine
│       └── paths.py               ← Evaluation-path enumeration
│
├── configs/                       ← Experiment configuration
│   ├── experiment.yaml            ← Master config (all parameters)
│   ├── case_study.yaml            ← Case-study overrides
│   └── seeds.txt                  ← 30 random seeds
│
├── data/
│   ├── policies/                  ← Generated policy pool (XACML)
│   ├── case_base_init/            ← Initial case base (5 seed cases)
│   ├── results/                   ← Experiment outputs
│   │   ├── Runs_Raw.csv
│   │   └── tables/                ← Aggregated tables (Table 1–5)
│   └── case_study/                ← MedSafe HIS policies & mutants
│       ├── medsafe_root.xml       ← Full XACML (v1.0, 27 rules)
│       ├── medsafe_v1.1.xml
│       ├── medsafe_v1.2.xml
│       ├── case_base_42.json
│       ├── mutants/
│       └── expected_results/
│
├── scripts/                       ← Reproduction & analysis scripts
│   ├── run_all.sh                 ← Full reproduction (30 × 4)
│   ├── run_case_study.sh          ← MedSafe case study
│   ├── gen_mutants.sh             ← Generate mutant pool
│   └── analyse.py                 ← Post-hoc analysis & table generation
│
├── tests/                         ← Unit tests
│   ├── test_similarity.py
│   ├── test_q_learning.py
│   ├── test_equivalence.py
│   └── test_paths.py
│
└── docs/
    └── figures/
        └── Chart_Panel.png        ← Main results chart
```

## Documentation

| Document | Description |
|---|---|
| **[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)** | **Experimental procedure and reproduction guide** — environment setup, execution of all three experiments, result aggregation, validation, troubleshooting, and customisation |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | Similarity weights, normalisation, path enumeration, Q-learning discretisation, equivalent-mutant detection, seeds, and full run configuration |
| [CASE_STUDY.md](CASE_STUDY.md) | End-to-end walkthrough on a realistic 27-rule Hospital Information System policy suite |

## Citation

```bibtex
@article{nguyen2026acptest,
  title   = {ACPTest: Adaptive Case-Based Policy Testing with
             Reinforcement Learning},
  author  = {Nguyen, Cuong Van},
  year    = {2026}
}
```

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
