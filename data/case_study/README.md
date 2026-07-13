# MedSafe Hospital Case Study — Data Files

See [CASE_STUDY.md](../../CASE_STUDY.md) for the full walkthrough.

| File | Description |
|---|---|
| `medsafe_root.xml` | XACML 3.0 policy v1.0 (27 rules, 14 conditions) |
| `medsafe_v1.1.xml` | v1.1 (+R28 research export, 28 rules) |
| `medsafe_v1.2.xml` | v1.2 (+R29-R31 + combiner change, 31 rules) |
| `case_base_42.json` | Pre-populated case base (42 policies) |
| `mutants/` | Generated mutant pool with manifest |
| `expected_results/` | Reference outputs for validation |

## Quick Start

```bash
bash scripts/run_case_study.sh
```

## License

CC BY 4.0 — synthetic policies, not a real hospital configuration.
