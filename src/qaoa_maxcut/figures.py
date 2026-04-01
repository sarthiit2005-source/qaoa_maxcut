"""Six reproducible README figures from recorded experiments and actual samples.

No smoothing or invented data. The histogram is a fixed-parameter comparison;
the other benchmark figures include every recorded trial.
"""

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import numpy as np

from .circuits import qaoa_circuit
from .data import read_results
from .evaluation import AerEvaluator
from .experiments import write_json
from .noise import NoiseConfig
from .objective import cut_diagonal, cut_value
from .problems import graph_from_dict
from .reporting import summarize

COLORS = {"COBYLA": "#2563eb", "Nelder-Mead": "#d97706", "Powell": "#0f766e"}
MODE_NAMES = {"ideal": "Exact ideal simulation", "shots": "Finite shots, ideal circuit",
              "noisy": "Illustrative noise + finite shots"}
FILES = ("01-depth-comparison", "02-optimizer-convergence", "03-graph-best-cut",
         "04-qaoa-circuit", "05-measurement-distribution", "06-evaluation-cost")


def incumbent_traces(record, mode, method, depth):
    """Best observed training value available at each budget, retaining early stops.

    Holding a stopped incumbent does not count or imply new circuit executions.
    Sampled incumbents are selected observations, not independent final estimates.
    """
    optima = {g["graph_seed"]: g["exact"]["cut"] for g in record["graphs"]}
    budget = record["config"]["evaluation_budget"]
    traces = []
    for run in record["runs"]:
        if (run["mode"], run["optimizer"], run["depth"]) != (mode, method, depth):
            continue
        values = np.array([h["best_so_far_cut"] / optima[run["graph_seed"]] for h in run["history"]])
        if not 1 <= len(values) <= budget:
            raise ValueError("Invalid history length for the recorded budget.")
        traces.append(np.pad(values, (0, budget - len(values)), mode="edge"))
    if not traces:
        raise ValueError("No matching convergence trials.")
    return np.asarray(traces)


def probability_vector(counts, n):
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("Empty measurement distribution.")
    probabilities = np.zeros(2 ** n)
    for bitstring, count in counts.items():
        probabilities[int(bitstring.replace(" ", ""), 2)] += count / total
    return probabilities


def cut_distribution(probabilities, diagonal):
    values = np.unique(diagonal)
    masses = np.array([probabilities[np.isclose(diagonal, value)].sum() for value in values])
    return values, masses


def _save(fig, output, name):
    for suffix in ("png", "svg"):
        fig.savefig(output / f"{name}.{suffix}", dpi=200, bbox_inches="tight", pad_inches=0.18,
                    facecolor="white")
    plt.close(fig)


def _decorate(ax, title, xlabel, ylabel):
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(axis="y", alpha=0.16)
    ax.spines[["top", "right"]].set_visible(False)


def _legend(fig, methods, y=0.01):
    handles = [Line2D([0], [0], color=COLORS[m], marker="o", linewidth=2, label=m) for m in methods]
    fig.legend(handles=handles, loc="lower center", ncol=len(methods), bbox_to_anchor=(0.5, y), frameon=False)


def depth_figure(record, output):
    rows = summarize(record)
    config = record["config"]
    modes, methods = config["modes"], config["optimizers"]
    fig, axes = plt.subplots(1, len(modes), figsize=(16, 5.5), sharey=True, squeeze=False)
    for ax, mode in zip(axes[0], modes):
        for method in methods:
            selected = sorted([r for r in rows if r["mode"] == mode and r["optimizer"] == method],
                              key=lambda r: r["depth"])
            x = [r["depth"] for r in selected]
            y = np.array([r["mean_ratio"] for r in selected])
            spread = np.array([r["graph_mean_ratio_sd"] or 0 for r in selected])
            ax.plot(x, y, color=COLORS[method], marker="o", linewidth=2)
            ax.fill_between(x, y - spread, y + spread, color=COLORS[method], alpha=0.12)
        greedy = np.mean([g["greedy"]["cut"] / g["exact"]["cut"] for g in record["graphs"]])
        random = np.mean([g["random_expected_cut"] / g["exact"]["cut"] for g in record["graphs"]])
        ax.axhline(1, color="#475569", linestyle=":", linewidth=1.3)
        ax.axhline(greedy, color="#166534", linestyle="--", linewidth=1.3)
        ax.axhline(random, color="#a16207", linestyle="--", linewidth=1.3)
        _decorate(ax, MODE_NAMES[mode], "QAOA layers p", "Final expected cut / exact optimum")
        ax.set_xticks(sorted(config["depths"]))
    fig.suptitle("Depth alone does not determine solution quality", fontsize=17, fontweight="bold", y=0.99)
    repeats = len(config["graph_seeds"]) * len(config["run_seeds"])
    fig.text(0.5, 0.91, f"{len(record['graphs'])} graphs | {len(config['run_seeds'])} starts per graph | "
             f"{repeats} final evaluations per point | shaded bands: SD of graph means", ha="center", fontsize=10)
    _legend(fig, methods, y=0.055)
    fig.text(0.5, 0.008, "Baselines: exact optimum (dotted), greedy (green dashed), random expected cut (brown dashed). "
             "Bands are descriptive, not confidence intervals.", ha="center", fontsize=9)
    fig.subplots_adjust(top=0.81, bottom=0.23, wspace=0.18)
    _save(fig, output, FILES[0])


def convergence_figure(record, output, depth):
    config = record["config"]
    fig, axes = plt.subplots(1, len(config["modes"]), figsize=(16, 5.5), sharey=True, squeeze=False)
    x = np.arange(1, config["evaluation_budget"] + 1)
    for ax, mode in zip(axes[0], config["modes"]):
        for method in config["optimizers"]:
            traces = incumbent_traces(record, mode, method, depth)
            low, middle, high = np.quantile(traces, [0.25, 0.5, 0.75], axis=0)
            ax.step(x, middle, where="post", color=COLORS[method], linewidth=2)
            ax.fill_between(x, low, high, step="post", color=COLORS[method], alpha=0.14)
        ax.axhline(1, color="#475569", linestyle=":")
        _decorate(ax, MODE_NAMES[mode], "Available training-evaluation budget", "Best observed training cut / exact optimum")
    fig.suptitle(f"Optimizer progress at p = {depth}", fontsize=17, fontweight="bold", y=0.99)
    fig.text(0.5, 0.91, "Every starting seed and graph included | median incumbent and middle 50% of trials | "
             "recorded evaluation points, no smoothing", ha="center", fontsize=10)
    _legend(fig, config["optimizers"], y=0.055)
    fig.text(0.5, 0.008, "An early-stopped run retains its incumbent without extra calls. "
             "Sampled training maxima can be optimistic; independent final scores appear in Figure 1.",
             ha="center", fontsize=9)
    fig.subplots_adjust(top=0.81, bottom=0.23, wspace=0.18)
    _save(fig, output, FILES[1])


def graph_figure(graph_data, measurements, output):
    graph = graph_from_dict(graph_data)
    pos = nx.spring_layout(graph, seed=2026)
    cases = [("Exact optimal partition", graph_data["exact"]["bitstring"]),
             ("Best observed noisy-sample partition", measurements["noisy"]["best_observed_bitstring"])]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.3))
    for ax, (title, bits) in zip(axes, cases):
        assignment = int(bits, 2)
        crossed, uncut = [], []
        for u, v in graph.edges:
            (crossed if ((assignment >> u) & 1) != ((assignment >> v) & 1) else uncut).append((u, v))
        nx.draw_networkx_edges(graph, pos, edgelist=uncut, edge_color="#fca5a5", style="dashed", width=2, ax=ax)
        nx.draw_networkx_edges(graph, pos, edgelist=crossed, edge_color="#15803d", width=3, ax=ax)
        nx.draw_networkx_nodes(graph, pos, node_color=["#1d4ed8" if not (assignment >> u) & 1 else "#b45309"
                                                     for u in graph.nodes],
                               node_size=720, edgecolors="white", linewidths=2, ax=ax)
        nx.draw_networkx_labels(graph, pos, font_color="white", font_size=12, font_weight="bold", ax=ax)
        ax.set_title(f"{title}\nCut = {cut_value(graph, assignment):g} / {graph.number_of_edges()} edges | "
                     f"bitstring {bits}", fontsize=12, pad=16)
        ax.set_axis_off()
        ax.margins(0.18)
    fig.suptitle(f"What Max-Cut means on benchmark graph seed {graph_data['graph_seed']}",
                 fontsize=16, fontweight="bold", y=0.98)
    fig.legend(handles=[Line2D([0], [0], color="#15803d", linewidth=3, label="Cut edge"),
                        Line2D([0], [0], color="#fca5a5", linewidth=2, linestyle="--", label="Uncut edge")],
               loc="lower center", bbox_to_anchor=(0.5, 0.055), ncol=2, frameon=False)
    fig.text(0.5, 0.018, "Node colors are the two partitions. The best observed solution is one sample, "
             "not the expected QAOA score. Rightmost bit is vertex 0.", ha="center", fontsize=9)
    fig.subplots_adjust(top=0.82, bottom=0.14)
    _save(fig, output, FILES[2])


def circuit_figure(graph_data, output):
    circuit, _ = qaoa_circuit(graph_from_dict(graph_data), 1)
    fig = circuit.draw(output="mpl", fold=36, style={"fontsize": 11, "subfontsize": 9}, idle_wires=False)
    fig.suptitle(f"Actual QAOA circuit: graph seed {graph_data['graph_seed']}, {graph_data['n']} qubits, p = 1",
                 fontsize=15, fontweight="bold", y=0.91)
    fig.text(0.5, 0.07, "Prepare |+> on each qubit; apply cost gates RZZ(-gamma x weight); "
             "apply mixer gates RX(2 x beta). This layer is repeated in the deeper experiments.",
             ha="center", fontsize=11)
    _save(fig, output, FILES[3])


def distribution_figure(graph_data, measurements, output, selected_run):
    graph = graph_from_dict(graph_data)
    diagonal = cut_diagonal(graph)
    distributions = {mode: probability_vector(measurements[mode]["counts"], len(graph))
                     for mode in ("shots", "noisy")}
    # Display ranking is defined by ideal sampled frequencies; remainder is explicit.
    top = np.argsort(-distributions["shots"], kind="stable")[:12]
    label = [format(int(z), f"0{len(graph)}b") + ("*" if np.isclose(diagonal[z], diagonal.max()) else "") for z in top]
    label.append("Other")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), gridspec_kw={"width_ratios": [1.4, 1]})
    colors = {"shots": "#2563eb", "noisy": "#9333ea"}
    names = {"shots": "Ideal circuit, sampled", "noisy": "Same parameters + noise"}
    x = np.arange(len(label))
    for mode, shift in (("shots", -0.19), ("noisy", 0.19)):
        values = distributions[mode][top]
        values = np.r_[values, 1 - values.sum()]
        axes[0].bar(x + shift, values, 0.38, color=colors[mode], alpha=0.88, label=names[mode])
        scores, mass = cut_distribution(distributions[mode], diagonal)
        spacing = np.min(np.diff(scores))
        axes[1].bar(scores + shift * spacing, mass, 0.38 * spacing, color=colors[mode], alpha=0.88)
    axes[0].set_xticks(x, label, rotation=55, ha="right", fontfamily="monospace", fontsize=9)
    _decorate(axes[0], "Twelve most frequent ideal outcomes + full remainder", "Measured bitstring (* = optimal cut)", "Observed frequency / shots")
    _decorate(axes[1], "All outcomes grouped by cut value", "Cut value C(z)", "Observed frequency / shots")
    axes[0].legend(frameon=False, fontsize=10)
    fig.suptitle("What the optimized circuit actually measures", fontsize=17, fontweight="bold", y=0.99)
    shots = measurements["shots"]["shots"]
    fig.text(0.5, 0.91, f"Fixed parameters from {selected_run['optimizer']}, graph {selected_run['graph_seed']}, "
             f"start {selected_run['run_seed']}, p={selected_run['depth']} | {shots:,} fresh shots per condition",
             ha="center", fontsize=10)
    ratios = {m: measurements[m]["mean_cut"] / graph_data["exact"]["cut"] for m in ("shots", "noisy")}
    fig.text(0.5, 0.025, f"Expected-cut ratio: ideal sampled {ratios['shots']:.4f}; noisy {ratios['noisy']:.4f}. "
             "No retraining between conditions. All probabilities, including 'Other', are retained.",
             ha="center", fontsize=10)
    fig.subplots_adjust(top=0.79, bottom=0.29, wspace=0.25)
    _save(fig, output, FILES[4])


def cost_figure(record, output):
    config = record["config"]
    rows = summarize(record)
    groups = defaultdict(list)
    for run in record["runs"]:
        groups[(run["mode"], run["optimizer"], run["depth"])].append(run)
    fig, axes = plt.subplots(2, len(config["modes"]), figsize=(16, 9), squeeze=False)
    for col, mode in enumerate(config["modes"]):
        for method in config["optimizers"]:
            subset = sorted([r for r in rows if r["mode"] == mode and r["optimizer"] == method], key=lambda r:r["depth"])
            depths = [r["depth"] for r in subset]
            calls = [r["mean_objective_evaluations"] for r in subset]
            deviations = [np.std([t["objective_evaluations"] for t in groups[(mode, method, r["depth"])]], ddof=1)
                          if r["trials"] > 1 else 0 for r in subset]
            axes[0, col].errorbar(depths, calls, yerr=deviations, color=COLORS[method], marker="o", capsize=3)
            work = calls if mode == "ideal" else [r["mean_training_shots"] / 1000 for r in subset]
            axes[1, col].plot(work, [r["mean_ratio"] for r in subset], color=COLORS[method], linewidth=1.2, alpha=0.6)
            for r, x in zip(subset, work):
                axes[1, col].scatter(x, r["mean_ratio"], color=COLORS[method], s=35 + 12 * r["depth"],
                                     edgecolor="white", linewidth=0.6, zorder=3)
        axes[0, col].axhline(config["evaluation_budget"], color="#64748b", linestyle=":", label="Common cap")
        _decorate(axes[0, col], MODE_NAMES[mode], "QAOA layers p", "Training circuit evaluations (mean +/- SD)")
        axes[0, col].set_xticks(config["depths"])
        axes[1, col].axhline(1, color="#64748b", linestyle=":")
        _decorate(axes[1, col], "Independent final quality versus training work",
                  "Training circuit evaluations (mean)" if mode == "ideal" else "Training measurement shots (thousands, mean)",
                  "Final expected cut / exact optimum")
    _legend(fig, config["optimizers"], y=0.045)
    fig.suptitle("Measured computational cost, not an iteration-count proxy", fontsize=17, fontweight="bold", y=0.99)
    fig.text(0.5, 0.945, "Top: actual calls used, with descriptive SD across trials. "
             "Bottom: each point averages all graph/start trials at one depth; larger dots mean deeper circuits.",
             ha="center", fontsize=10)
    fig.text(0.5, 0.01, f"Sampled modes spend {config['shots']:,} shots per training call. "
             "Costs exclude final evaluation. Ideal calls still cost CPU time despite using zero measurement shots.",
             ha="center", fontsize=9)
    fig.subplots_adjust(top=0.87, bottom=0.14, hspace=0.53, wspace=0.3)
    _save(fig, output, FILES[5])


def create_figures(results_path, output, example_depth=3):
    """Write six PNG/SVG pairs and provenance, using a predeclared representative."""
    results_path, output = Path(results_path), Path(output)
    record = read_results(results_path)
    if record["status"] != "complete":
        raise ValueError("README figures require a complete experiment record.")
    output.mkdir(parents=True, exist_ok=True)
    config = record["config"]
    graph_seed, run_seed = config["graph_seeds"][0], config["run_seeds"][0]
    if example_depth not in config["depths"]:
        raise ValueError("Example depth must be present in the benchmark.")
    method = "COBYLA" if "COBYLA" in config["optimizers"] else config["optimizers"][0]
    selected = next(r for r in record["runs"] if (r["graph_seed"], r["run_seed"], r["depth"], r["mode"], r["optimizer"])
                    == (graph_seed, run_seed, example_depth, "ideal", method))
    graph_data = next(g for g in record["graphs"] if g["graph_seed"] == graph_seed)
    graph = graph_from_dict(graph_data)
    measurement_seed = 20261011
    measurements = {}
    for mode in ("shots", "noisy"):
        evaluator = AerEvaluator(graph, example_depth, mode, config["final_shots"], measurement_seed,
                                 NoiseConfig(**config["noise"]))
        measurements[mode] = evaluator.evaluate(selected["parameters"])
    write_json(output / "measurement-data.json", {
        "source_run_id": selected["run_id"], "fixed_parameters": selected["parameters"],
        "graph": graph_data, "noise": config["noise"], "measurement_seed": measurement_seed,
        "real_hardware": False, "measurements": measurements,
    })
    style = {"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 12,
             "axes.labelsize": 10, "svg.fonttype": "none", "axes.titlepad": 14}
    with plt.rc_context(style):
        depth_figure(record, output)
        convergence_figure(record, output, example_depth)
        graph_figure(graph_data, measurements, output)
        circuit_figure(graph_data, output)
        distribution_figure(graph_data, measurements, output, selected)
        cost_figure(record, output)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_relative_to_images": os.path.relpath(results_path, output).replace("\\", "/"),
        "source_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest(),
        "config": config, "benchmark_trials": len(record["runs"]), "real_hardware": False,
        "representative_rule": f"First configured graph and starting seed, {method} ideal training, fixed p={example_depth}; not the best trial.",
        "representative_run_id": selected["run_id"],
        "histogram_extra_evaluations": 2, "histogram_extra_shots": 2 * config["final_shots"],
        "convergence_note": "Raw recorded incumbents; early-stopped incumbents retained without extra calls; training selection can be optimistic.",
        "files": {f"{name}.{suffix}": hashlib.sha256((output/f"{name}.{suffix}").read_bytes()).hexdigest()
                  for name in FILES for suffix in ("png", "svg")},
    }
    write_json(output / "figure-manifest.json", manifest)
    return manifest
