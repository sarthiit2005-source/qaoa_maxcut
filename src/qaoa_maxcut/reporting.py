"""Raw CSV, descriptive statistics, and saved plots; no GUI and no smoothing."""

from collections import defaultdict
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .data import read_results


def _sd(values):
    return float(np.std(values, ddof=1)) if len(values) > 1 else None


def summarize(record: dict) -> list[dict]:
    groups = defaultdict(list)
    for run in record["runs"]:
        groups[(run["mode"], run["optimizer"], run["depth"])].append(run)
    rows = []
    for (mode, method, depth), runs in sorted(groups.items()):
        per_graph = defaultdict(list)
        for run in runs:
            per_graph[run["graph_seed"]].append(run["final"]["approximation_ratio"])
        ratios = [r["final"]["approximation_ratio"] for r in runs]
        within = [_sd(values) for values in per_graph.values() if len(values) > 1]
        graph_means = [float(np.mean(values)) for values in per_graph.values()]
        rows.append({
            "mode": mode, "optimizer": method, "depth": depth,
            "trials": len(runs), "graphs": len(per_graph),
            "mean_ratio": float(np.mean(ratios)), "trial_ratio_sd": _sd(ratios),
            "trial_ratio_variance": float(np.var(ratios, ddof=1)) if len(ratios) > 1 else None,
            "graph_mean_ratio_sd": _sd(graph_means),
            "mean_within_graph_seed_sd": float(np.mean(within)) if within else None,
            "mean_objective_evaluations": float(np.mean([r["objective_evaluations"] for r in runs])),
            "mean_training_shots": float(np.mean([r["training_shots"] for r in runs])),
            "mean_optimization_seconds": float(np.mean([r["optimization_seconds"] for r in runs])),
        })
    return rows


def _csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def create_report(results_path: str | Path) -> list[dict]:
    results_path = Path(results_path)
    record = read_results(results_path)
    if not record["runs"]:
        raise ValueError("No completed trials to report.")
    output = results_path.parent
    summary = summarize(record)
    _csv(output / "summary.csv", summary)
    _csv(output / "runs.csv", [{
        "run_id": run["run_id"], "graph_seed": run["graph_seed"], "run_seed": run["run_seed"],
        "mode": run["mode"], "optimizer": run["optimizer"], "depth": run["depth"],
        "approximation_ratio": run["final"]["approximation_ratio"],
        "ratio_standard_error": run["final"]["ratio_standard_error"],
        "objective_evaluations": run["objective_evaluations"], "training_shots": run["training_shots"],
        "final_shots": run["final"]["shots"], "status": run["status"],
        "optimization_seconds": run["optimization_seconds"],
    } for run in record["runs"]])
    _csv(output / "history.csv", [{
        "run_id": run["run_id"], "evaluation": h["evaluation"], "mean_cut": h["mean_cut"],
        "best_so_far_cut": h["best_so_far_cut"], "shots": h["shots"],
        "simulator_seed": h["simulator_seed"],
    } for run in record["runs"] for h in run["history"]])
    greedy_ratio = float(np.mean([g["greedy"]["cut"] / g["exact"]["cut"] for g in record["graphs"]]))
    random_ratio = float(np.mean([g["random_expected_cut"] / g["exact"]["cut"] for g in record["graphs"]]))
    modes = [m for m in record["config"]["modes"] if any(r["mode"] == m for r in summary)]
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(1, len(modes), figsize=(5.2 * len(modes), 4.2),
                                 squeeze=False, sharey=True)
        for ax, mode in zip(axes[0], modes):
            for method in record["config"]["optimizers"]:
                rows = sorted([r for r in summary if r["mode"] == mode and r["optimizer"] == method],
                              key=lambda r: r["depth"])
                if rows:
                    ax.errorbar([r["depth"] for r in rows], [r["mean_ratio"] for r in rows],
                                yerr=[r["graph_mean_ratio_sd"] or 0 for r in rows],
                                marker="o", capsize=3, label=method)
            ax.axhline(1, color="#64748b", linestyle=":", label="Exact optimum")
            ax.axhline(greedy_ratio, color="#166534", linestyle="--", label="Greedy mean")
            ax.axhline(random_ratio, color="#a16207", linestyle="--", label="Random expected mean")
            ax.set(title=mode, xlabel="QAOA layers p", ylabel="Expected cut / exact optimum")
            ax.set_xticks(sorted(record["config"]["depths"]))
            ax.grid(alpha=0.2)
        axes[0][-1].legend(fontsize=8, loc="best")
        caption = ("Error bars: SD of graph means, not confidence intervals"
                   if len(record["graphs"]) > 1 else "Single graph: between-graph variation not estimated")
        fig.suptitle(f"Raw depth comparison | {caption}", fontsize=11)
        fig.tight_layout()
        fig.savefig(output / "approximation-ratio.png", dpi=160)
        plt.close(fig)
    lines = ["# Experiment results", "", f"Experiment status: {record['status']}.", "",
             "Metric: independently evaluated expected cut divided by the exact graph optimum.",
             "Standard deviations and variances describe this finite sample, not universal performance.",
             "Graph means average the starting seeds first; their SD measures between-graph variation.",
             "Trial SD mixes graph and starting-seed variation. Final shot standard errors are separate in runs.csv.",
             "A single graph/seed cannot estimate the corresponding variation (blank CSV values).", "",
             f"Greedy mean ratio: {greedy_ratio:.4f}. Random-cut expected mean ratio: {random_ratio:.4f}.",
             "Greedy returns one classical solution; QAOA's main metric is an expected solution score.",
             "These are quality baselines, not equal-time demonstrations of quantum advantage.", "",
             "| Mode | Optimizer | p | Trials | Mean ratio | Trial SD | Mean evaluations |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for row in summary:
        deviation = f"{row['trial_ratio_sd']:.4f}" if row["trial_ratio_sd"] is not None else "N/A"
        lines.append(f"| {row['mode']} | {row['optimizer']} | {row['depth']} | {row['trials']} | "
                     f"{row['mean_ratio']:.4f} | {deviation} | {row['mean_objective_evaluations']:.1f} |")
    lines += ["", "![Approximation ratio](approximation-ratio.png)", "",
              "The evaluation cap is shared, but optimizers may converge early. Actual evaluation counts are recorded.",
              "An exact expectation and a shot-based circuit execution have different costs; compare modes accordingly.",
              "Final evaluation uses one additional circuit execution and is excluded from the training budget.",
              "No real hardware was involved in these local experiment results.", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
