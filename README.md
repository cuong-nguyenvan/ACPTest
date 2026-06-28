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

> *Automated Test Suite Generation for Access Control Policies
Using Case-Based Reasoning and Reinforcement Learning*


---

## 📌 Overview

**ACPTest** is a research framework that automatically generates and refines test suites for **XACML 3.0 access control policies**. It integrates two complementary AI techniques:

- **Case-Based Reasoning (CBR)** — retrieves and adapts test cases from a repository of previously tested policies, reducing cold-start overhead.
- **Reinforcement Learning (RL / Q-learning)** — iteratively refines the test suite by learning which actions (add / modify / remove test cases) maximise coverage and fault detection while minimising redundancy.
- **Policy Evolution Handling (Algorithm 3)** — when a policy changes, only the affected subset of tests is re-generated, keeping regression testing cost low.

The framework targets the three core quality metrics used in software testing:

| Metric | Symbol | Goal |
|--------|--------|------|
| Structural Coverage | Cov | ↑ Maximise |
| Fault Detection Rate | FDR | ↑ Maximise |
| Test Redundancy | Red | ↓ Minimise |

---

## 📂 Repository Structure

```
ACPTest/
├── acptest_final_experiment.py   # Main experiment script (100 XACML policies)
├── Table1_Stage_Effectiveness.csv   # Results: per-stage quality metrics
├── Table2_Policy_Evolution.csv      # Results: test reuse under policy changes
├── Table3_RL_Contribution.csv       # Results: RL contribution (before vs after)
├── Figure3_ACPTest_Quality_Runtime.png  # Quality & runtime chart
└── README.md
```

---

## 🔬 Methodology

### Three-Algorithm Pipeline

```
Policy P  ──►  [Algorithm 1: CBR Retrieval]  ──►  Initial Suite T_CBR
                       │  (Similarity Eq.2–4)
                       ▼
              [Algorithm 2: RL Refinement]   ──►  Optimised Suite T_RL
                       │  (Q-learning Eq.6–10)
                       ▼
           Policy evolves? ──► [Algorithm 3: Evolution Handling] ──► T_updated
```

#### Algorithm 1 — CBR-Based Test Reuse

Each policy is represented as a 7-dimensional feature vector:

```
F(P) = ⟨n_r, n_c, n_d, n_p, depth, branching, algorithm⟩
```

Similarity between a query policy and a case in the case base is computed as a weighted sum (Eq. 2):

```
Sim(P_q, C_i) = Σ w_k · sim_k(f_q^k, f_i^k)
```

where numerical features use ratio similarity (Eq. 3) and categorical features use exact match (Eq. 4).  
The top-**K** most similar cases are retrieved and their test cases adapted to the target policy.

#### Algorithm 2 — RL-Based Test Refinement

The RL agent operates on state `s = ⟨Cov, FDR, Red, Size⟩` and selects one of three actions per episode:

| Action | Effect |
|--------|--------|
| `a_add` | Add a new test case targeting an uncovered path |
| `a_modify` | Replace a low-value test case |
| `a_remove` | Remove a redundant test case |

**Reward function (Eq. 9):**

```
R = α·ΔCov + β·ΔFDR − γ·ΔRed − δ·ΔSize
```

**Q-update (Eq. 10, η = 0.20, λ = 0.90):**

```
Q(s,a) ← Q(s,a) + η · [R + λ · max_{a'} Q(s',a') − Q(s,a)]
```

#### Algorithm 3 — Policy Evolution Handling

When policy P evolves to P′, the framework computes the graph difference ΔG = G_P′ \ G_P (Eq. 11), identifies affected nodes and impacted test cases (Eqs. 12–13), and only re-generates tests for those paths. Unchanged tests are reused directly.

---

## 📊 Experimental Results

Experiments were conducted on **100 synthetic XACML 3.0 policies** (avg. 106 rules each), with parameters **K = 5** nearest cases and **EP = 30** RL episodes per policy.

### Table 1 — Stage Effectiveness

| Stage | Test Cases | Coverage (%) | Fault Detection (%) | Redundancy (%) |
|-------|-----------|-------------|-------------------|---------------|
| Initial Policy | 36.99 | 52.11 | 35.55 | 37.80 |
| After CBR Reuse | 20.46 | 85.79 | 75.08 | 30.28 |
| **After CBR + RL** | **21.06** | **93.15** | **84.79** | **4.15** |

> CBR raises coverage by **+33.68 pp** over random; RL further adds **+7.36 pp** while reducing redundancy from 30.28% to **4.15%**.

### Table 2 — Policy Evolution Impact

| Policy Modification | Reused Tests (%) | Adapted Tests (%) | Newly Generated (%) |
|--------------------|-----------------|------------------|-------------------|
| 10% | 89.20 | 6.24 | 4.56 |
| 20% | 78.88 | 10.67 | 10.45 |
| 30% | 69.20 | 16.16 | 14.64 |

> Even with 30% policy change, **69.2%** of existing test cases are reused directly, significantly reducing re-testing cost.

### Table 3 — RL Contribution

| Metric | Without RL (CBR only) | With RL (CBR + RL) | Improvement |
|--------|-----------------------|--------------------|-------------|
| Coverage (%) | 85.79 | 93.15 | **+7.36 pp** |
| Fault Detection (%) | 75.08 | 84.79 | **+9.71 pp** |
| Test Cases | 20.46 | 21.06 | −0.60 (reduced) |
| Redundancy (%) | 30.28 | 4.15 | **−26.13 pp** |

### Runtime Complexity

Cumulative execution time for 100 policies grows **linearly O(n)**, reaching only **~170 ms** total — confirming practical scalability.

| Rules per Policy | CBR Retrieval (ms) | RL Refinement (ms) | Total (ms) |
|-----------------|-------------------|-------------------|-----------|
| 2 | 0.33 | 4.39 | 4.72 |
| 3 | 0.30 | 5.41 | 5.71 |
| 4 | 0.28 | 6.25 | 6.53 |
| 5 | 0.31 | 6.77 | 7.08 |

---

## 🚀 Getting Started

### Prerequisites

```bash
Python >= 3.8
numpy
pandas
matplotlib
```

Install dependencies:

```bash
pip install numpy pandas matplotlib
```

### Run the Experiment

```bash
python acptest_final_experiment.py
```

This will:

1. Generate 100 synthetic XACML 3.0 policies
2. Run the full CBR + RL pipeline (Algorithm 1 + 2)
3. Simulate policy evolution scenarios (Algorithm 3)
4. Output **3 result tables** (CSV) and **1 chart** (PNG + PDF)

### Output Files

| File | Description |
|------|-------------|
| `Table1_Stage_Effectiveness.csv` | Coverage, FDR, redundancy per pipeline stage |
| `Table2_Policy_Evolution.csv` | Test reuse/adaptation ratios under policy change |
| `Table3_RL_Contribution.csv` | Before/after RL comparison |
| `Figure3_ACPTest_Quality_Runtime.png` | Quality metrics + cumulative runtime chart |
| `Figure3_ACPTest_Quality_Runtime.pdf` | Same chart, vector format |

---

## ⚙️ Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `N` | 100 | Number of policies in the experiment |
| `K` | 5 | Top-K similar cases retrieved by CBR |
| `EP` | 30 | RL episodes per policy |
| `ALPHA` | 0.35 | Reward weight for Δ Coverage |
| `BETA` | 0.40 | Reward weight for Δ Fault Detection |
| `GAMMA` | 0.80 | Penalty weight for Δ Redundancy |
| `DELTA` | 0.02 | Penalty weight for Δ Suite Size |
| `ETA` | 0.20 | Q-learning rate |
| `LAM` (λ) | 0.90 | Q-learning discount factor |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ACPTest Framework                     │
├──────────────────┬─────────────────────┬────────────────────┤
│   Policy Flow    │    Case Base (CB)    │  RL Q-Table        │
│   Graph G_P      │  {C_1, …, C_m}      │  Q: S × A → ℝ     │
│  (Definition 1)  │  (Definition 3)     │  (Equation 10)    │
└────────┬─────────┴──────────┬──────────┴────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────────┐
   │ Feature  │──Sim──►│ CBR Retrieve │──► T_CBR
   │ Vector   │        │ (Algo. 1)    │
   │ F(P)     │        └──────────────┘
   └──────────┘                │
                               ▼
                       ┌──────────────┐
                       │ RL Refine    │──► T_RL (final suite)
                       │ (Algo. 2)    │
                       └──────────────┘
                               │
                    Policy evolves?
                               ▼
                       ┌──────────────┐
                       │ Evolution    │──► T_updated
                       │ (Algo. 3)    │
                       └──────────────┘
```

---

## 📋 Policy Domain

The framework is evaluated on **XACML 3.0** healthcare access control policies with the following attribute space:

- **Roles:** `doctor`, `nurse`, `admin`, `patient`, `researcher`
- **Departments:** `cardiology`, `neurology`, `oncology`, `radiology`, `ICU`
- **Resources:** `patient_record`, `lab_result`, `prescription`, `imaging`, `billing`
- **Actions:** `read`, `write`, `delete`, `update`
- **Combining algorithms:** `permit-overrides`, `deny-overrides`, `first-applicable`

---

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- XACML 3.0 standard — [OASIS](https://www.oasis-open.org/committees/xacml/)
- Q-learning algorithm — Watkins & Dayan (1992)
- Case-Based Reasoning — Aamodt & Plaza (1994)

---

<p align="center">
  Made with ❤️ for reproducible access control policy testing research
</p>
