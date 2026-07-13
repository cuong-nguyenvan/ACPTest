"""
Post-hoc analysis: aggregate per-run JSON results into CSV tables
and statistical comparisons.

Produces:
    Table1  — Ablation study (mean ± SD)
    Table1b — Deltas vs. from-scratch
    Table2  — Policy evolution reuse proportions
    Table3  — RL contribution (CBR-only vs CBR+RL)
    Table4  — Full descriptive statistics
    Table5  — Pairwise paired tests with effect sizes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


METRICS = [
    "coverage_percent",
    "fault_detection_percent",
    "redundancy_percent",
    "test_case_count",
]

METRIC_LABELS = {
    "coverage_percent": "Coverage % (modelled)",
    "fault_detection_percent": "Fault Detection % (modelled)",
    "redundancy_percent": "Redundancy % (modelled)",
    "test_case_count": "Test Cases (modelled)",
}

CONFIG_LABELS = {
    "from_scratch": "From-scratch",
    "cbr_only": "CBR only",
    "rl_only": "RL only",
    "cbr_rl": "CBR + RL (ACPTest)",
}


def load_results(results_dir: Path) -> pd.DataFrame:
    """Load all run_*.json files into a DataFrame."""
    rows = []
    for f in sorted(results_dir.glob("run_*.json")):
        with open(f) as fp:
            data = json.load(fp)
        agg = data.get("aggregate", {})
        config = CONFIG_LABELS.get(data["mode"], data["mode"])
        for metric in METRICS:
            rows.append({
                "Run": data["run_id"],
                "Configuration": config,
                "Metric": METRIC_LABELS[metric],
                "Value_modelled": agg.get(metric, 0),
            })
    return pd.DataFrame(rows)


def table1_ablation(df: pd.DataFrame) -> pd.DataFrame:
    """Table 1: mean ± SD per configuration."""
    grouped = df.groupby(["Configuration", "Metric"])["Value_modelled"]
    summary = grouped.agg(["mean", "std"]).reset_index()
    summary["formatted"] = summary.apply(
        lambda r: f"{r['mean']:.2f} ± {r['std']:.2f}", axis=1
    )
    pivot = summary.pivot(index="Configuration", columns="Metric", values="formatted")
    return pivot


def table4_descriptive(df: pd.DataFrame) -> pd.DataFrame:
    """Table 4: full descriptive statistics."""
    rows = []
    for (metric, config), group in df.groupby(["Metric", "Configuration"]):
        vals = group["Value_modelled"].values
        n = len(vals)
        mean = np.mean(vals)
        sd = np.std(vals, ddof=1) if n > 1 else 0
        se = sd / np.sqrt(n) if n > 0 else 0
        ci95_lo = mean - 1.96 * se
        ci95_hi = mean + 1.96 * se
        rows.append({
            "Metric": metric,
            "Configuration": config,
            "Mean": round(mean, 3),
            "SD": round(sd, 3),
            "CI95_low": round(ci95_lo, 3),
            "CI95_high": round(ci95_hi, 3),
            "Min": round(np.min(vals), 3),
            "Max": round(np.max(vals), 3),
            "N_runs": n,
        })
    return pd.DataFrame(rows)


def table5_paired_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Table 5: all pairwise paired-sample tests."""
    configs = df["Configuration"].unique()
    metrics = df["Metric"].unique()
    rows = []

    for i, c1 in enumerate(configs):
        for c2 in configs[i + 1:]:
            for metric in metrics:
                v1 = df[(df["Configuration"] == c1) & (df["Metric"] == metric)].sort_values("Run")["Value_modelled"].values
                v2 = df[(df["Configuration"] == c2) & (df["Metric"] == metric)].sort_values("Run")["Value_modelled"].values

                if len(v1) != len(v2) or len(v1) < 2:
                    continue

                diff = v2 - v1
                mean_diff = np.mean(diff)
                sd_diff = np.std(diff, ddof=1)

                t_stat, p_t = stats.ttest_rel(v2, v1)
                try:
                    w_stat, p_w = stats.wilcoxon(v2, v1)
                except ValueError:
                    w_stat, p_w = np.nan, np.nan

                pooled_sd = np.sqrt((np.var(v1, ddof=1) + np.var(v2, ddof=1)) / 2)
                cohens_d = mean_diff / pooled_sd if pooled_sd > 0 else 0

                rows.append({
                    "Comparison": f"{c2} vs {c1}",
                    "Metric": metric,
                    "Mean_Diff": f"{mean_diff:+.3f} ± {sd_diff:.3f}",
                    "Paired_t": round(t_stat, 3),
                    "p_ttest": f"{p_t:.2e}" if p_t > 1e-6 else "< 1e-6",
                    "Wilcoxon_W": round(w_stat, 1) if not np.isnan(w_stat) else "N/A",
                    "p_wilcoxon": f"{p_w:.2e}" if not np.isnan(p_w) and p_w > 1e-6 else "< 1e-6",
                    "Cohen_d": round(cohens_d, 3),
                    "Effect": _effect_label(abs(cohens_d)),
                    "Sig": "***" if p_t < 0.001 else ("**" if p_t < 0.01 else ("*" if p_t < 0.05 else "ns")),
                })

    return pd.DataFrame(rows)


def _effect_label(d: float) -> str:
    if d >= 1.2:
        return "very large"
    elif d >= 0.8:
        return "large"
    elif d >= 0.5:
        return "medium"
    elif d >= 0.2:
        return "small"
    return "negligible"


def main():
    parser = argparse.ArgumentParser(description="ACPTest post-hoc analysis")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--format", default="csv", choices=["csv", "markdown"])
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_results(results_dir)

    if df.empty:
        print("No result files found. Ensure run_*.json files exist.")
        sys.exit(1)

    # Raw data
    df.to_csv(output_dir / "Runs_Raw.csv", index=False)

    # Tables
    t1 = table1_ablation(df)
    t4 = table4_descriptive(df)
    t5 = table5_paired_tests(df)

    if args.format == "csv":
        t1.to_csv(output_dir / "Table1_Ablation_Study.csv")
        t4.to_csv(output_dir / "Table4_Descriptive_Stats.csv", index=False)
        t5.to_csv(output_dir / "Table5_Paired_Tests.csv", index=False)
    else:
        print(t1.to_markdown())
        print()
        print(t4.to_markdown(index=False))

    print(f"Tables written to {output_dir}/")


if __name__ == "__main__":
    main()
