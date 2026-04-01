"""Paired, seeded experiments; every trial survives in a machine-readable record."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np

from .baselines import brute_force, greedy_cut
from .evaluation import AerEvaluator, MODES
from .noise import NoiseConfig
from .optimization import OPTIMIZERS, optimize
from .problems import graph_to_dict, regular_graph


@dataclass
class ExperimentConfig:
    n: int = 6
    degree: int = 3
    graph_seeds: list[int] = field(default_factory=lambda: [11])
    run_seeds: list[int] = field(default_factory=lambda: [101])
    depths: list[int] = field(default_factory=lambda: [1, 2])
    optimizers: list[str] = field(default_factory=lambda: list(OPTIMIZERS))
    modes: list[str] = field(default_factory=lambda: list(MODES))
    evaluation_budget: int = 40
    shots: int = 256
    final_shots: int = 4096
    greedy_restarts: int = 8
    noise: NoiseConfig = field(default_factory=NoiseConfig)

    def validate(self):
        for name in ("graph_seeds", "run_seeds", "depths", "optimizers", "modes"):
            items = getattr(self, name)
            if not items or len(set(items)) != len(items):
                raise ValueError(f"{name} must be nonempty and contain no duplicates.")
        for name in ("graph_seeds", "run_seeds"):
            if any(type(s) is not int or s < 0 for s in getattr(self, name)):
                raise ValueError("Seeds must be nonnegative integers.")
        if any(type(d) is not int or not 1 <= d <= 10 for d in self.depths):
            raise ValueError("Depths must be integers in 1..10.")
        if set(self.optimizers) - set(OPTIMIZERS) or set(self.modes) - set(MODES):
            raise ValueError("Unknown optimizer or evaluation mode.")
        for name in ("evaluation_budget", "shots", "final_shots", "greedy_restarts"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if "noisy" in self.modes and self.n > 10:
            raise ValueError("Noisy simulation supports at most 10 vertices.")
        regular_graph(self.n, self.degree, self.graph_seeds[0])

    @classmethod
    def from_file(cls, path: str | Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["noise"] = NoiseConfig(**data.get("noise", {}))
        config = cls(**data)
        config.validate()
        return config


def write_json(path: Path, data: dict) -> None:
    """Replace only a complete JSON file, so interrupted jobs retain prior trials."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def environment_info() -> dict:
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {name: version(name) for name in
                     ["qiskit", "qiskit-aer", "numpy", "scipy", "networkx", "matplotlib"]},
    }


def derived_seed(*values: int) -> int:
    return int(np.random.SeedSequence(values).generate_state(1)[0])


def run_experiment(config: ExperimentConfig, output: Path, progress=print) -> dict:
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1, "status": "running",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config), "environment": environment_info(),
        "graphs": [], "runs": [],
    }
    write_json(output / "results.json", record)
    started = perf_counter()
    total = (len(config.graph_seeds) * len(config.run_seeds) * len(config.depths)
             * len(config.modes) * len(config.optimizers))
    try:
        for graph_seed in config.graph_seeds:
            graph = regular_graph(config.n, config.degree, graph_seed)
            tick = perf_counter()
            exact = brute_force(graph)
            exact["seconds"] = perf_counter() - tick
            tick = perf_counter()
            greedy = greedy_cut(graph, graph_seed, config.greedy_restarts)
            greedy["seconds"] = perf_counter() - tick
            total_weight = sum(float(d.get("weight", 1.0)) for _, _, d in graph.edges(data=True))
            record["graphs"].append({"graph_seed": graph_seed, **graph_to_dict(graph),
                                     "exact": exact, "greedy": greedy,
                                     "random_expected_cut": total_weight / 2})
            for depth in config.depths:
                for run_seed in config.run_seeds:
                    # Same initial vector across optimizers and modes for a paired comparison.
                    initial_seed = derived_seed(graph_seed, run_seed, depth, 0)
                    initial = np.random.default_rng(initial_seed).uniform(0, np.pi, 2 * depth)
                    training_seed = derived_seed(graph_seed, run_seed, depth, 1)
                    final_seed = derived_seed(graph_seed, run_seed, depth, 2)
                    for mode in config.modes:
                        for method in config.optimizers:
                            tick = perf_counter()
                            evaluator = AerEvaluator(graph, depth, mode, config.shots,
                                                     training_seed, config.noise)
                            result = optimize(evaluator, initial, method, config.evaluation_budget)
                            # New RNG stream and larger shot count reduce selection bias in reporting.
                            final_evaluator = AerEvaluator(graph, depth, mode, config.final_shots,
                                                           final_seed, config.noise)
                            final = final_evaluator.evaluate(result["parameters"])
                            final["approximation_ratio"] = final["mean_cut"] / exact["cut"]
                            final["cut_fraction"] = final["mean_cut"] / total_weight
                            final["ratio_standard_error"] = (
                                final["standard_error"] / exact["cut"]
                                if final["standard_error"] is not None else None
                            )
                            run = {
                                "run_id": f"g{graph_seed}-s{run_seed}-p{depth}-{mode}-{method}",
                                "graph_seed": graph_seed, "run_seed": run_seed,
                                "depth": depth, "mode": mode,
                                "initial_seed": initial_seed, "training_seed": training_seed,
                                "final_seed": final_seed, **result, "final": final,
                                "final_evaluations": 1,
                                "total_circuit_evaluations": result["objective_evaluations"] + 1,
                                "total_shots": result["training_shots"] + final["shots"],
                                "resources": evaluator.circuit_resources(),
                                "total_seconds": perf_counter() - tick,
                            }
                            record["runs"].append(run)
                            write_json(output / "results.json", record)
                            progress(f"[{len(record['runs'])}/{total}] {run['run_id']}: "
                                     f"ratio={final['approximation_ratio']:.4f}, "
                                     f"evaluations={result['objective_evaluations']}")
        record["status"] = "complete"
    except BaseException:
        record["status"] = "interrupted_or_failed"
        raise
    finally:
        record["elapsed_seconds"] = perf_counter() - started
        write_json(output / "results.json", record)
    return record
