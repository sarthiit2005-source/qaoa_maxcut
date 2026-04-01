import json

import numpy as np
import pytest

from qaoa_maxcut.experiments import ExperimentConfig, run_experiment
from qaoa_maxcut.noise import NoiseConfig
from qaoa_maxcut.optimization import OPTIMIZERS, optimize
from qaoa_maxcut.problems import regular_graph
from qaoa_maxcut.reporting import create_report, summarize


class QuadraticEvaluator:
    def evaluate(self, parameters):
        return {"mean_cut": -float(np.dot(parameters, parameters)), "shots": 32, "simulator_seed": 1}


@pytest.mark.parametrize("method", OPTIMIZERS)
def test_hard_budget_and_best_parameters_survive(method):
    result = optimize(QuadraticEvaluator(), [1.0, -0.7], method, 5)
    assert 1 <= result["objective_evaluations"] <= 5
    assert result["training_shots"] == 32 * result["objective_evaluations"]
    assert result["training_best_cut"] == max(h["mean_cut"] for h in result["history"])
    assert QuadraticEvaluator().evaluate(result["parameters"])["mean_cut"] == result["training_best_cut"]


@pytest.mark.parametrize("options", [{"shots": 0}, {"run_seeds": []}, {"depths": [0]},
                                      {"graph_seeds": [11, 11]}, {"optimizers": ["Newton-CG"]},
                                      {"n": 6, "degree": 1}, {"n": 5, "degree": 3}])
def test_invalid_configs_fail_early(options):
    with pytest.raises(ValueError):
        ExperimentConfig(**options).validate()


def test_regular_graph_is_reproducible():
    assert list(regular_graph(8, 3, 11).edges) == list(regular_graph(8, 3, 11).edges)


def test_full_pipeline_reproducible_and_reports_unsmoothed(tmp_path):
    config = ExperimentConfig(n=4, degree=2, depths=[1], evaluation_budget=8,
                              shots=128, final_shots=512)
    first = run_experiment(config, tmp_path / "first", progress=lambda _: None)
    second = run_experiment(config, tmp_path / "second", progress=lambda _: None)
    assert first["status"] == "complete"
    assert len(first["runs"]) == 9
    for a, b in zip(first["runs"], second["runs"]):
        assert a["parameters"] == b["parameters"]
        assert a["final"] == b["final"]
        assert a["history"] == b["history"]
        assert a["objective_evaluations"] <= config.evaluation_budget
        assert a["total_circuit_evaluations"] == a["objective_evaluations"] + 1
        assert a["total_shots"] == a["training_shots"] + a["final"]["shots"]
        assert a["training_seed"] != a["final_seed"]
        assert 0 <= a["final"]["approximation_ratio"] <= 1 + 1e-12
    initial_vectors = {tuple(r["initial_parameters"]) for r in first["runs"]}
    assert len(initial_vectors) == 1
    summary = create_report(tmp_path / "first" / "results.json")
    assert all(r["trial_ratio_sd"] is None for r in summary)
    assert (tmp_path / "first" / "approximation-ratio.png").stat().st_size > 1000
    assert json.loads((tmp_path / "first" / "results.json").read_text())["status"] == "complete"
    with pytest.raises(FileExistsError):
        run_experiment(config, tmp_path / "first", progress=lambda _: None)


def test_variance_distinguishes_graphs_and_starting_seeds():
    runs = []
    for seed, ratios in [(11, [0.5, 0.7]), (23, [0.8, 1.0])]:
        for ratio in ratios:
            runs.append({"mode": "ideal", "optimizer": "COBYLA", "depth": 1,
                         "graph_seed": seed, "final": {"approximation_ratio": ratio},
                         "objective_evaluations": 10, "training_shots": 0, "optimization_seconds": 0.1})
    row = summarize({"runs": runs})[0]
    assert row["mean_ratio"] == pytest.approx(0.75)
    assert row["trial_ratio_variance"] == pytest.approx(np.var([0.5, 0.7, 0.8, 1], ddof=1))
    assert row["graph_mean_ratio_sd"] == pytest.approx(np.std([0.6, 0.9], ddof=1))
    assert row["mean_within_graph_seed_sd"] == pytest.approx(np.std([0.5, 0.7], ddof=1))


def test_zero_noise_matches_shot_statistics():
    from qaoa_maxcut.evaluation import AerEvaluator
    graph = regular_graph(4, 2, 11)
    parameters = [0.67, -0.24]
    exact = AerEvaluator(graph, 1, "ideal", 10, 42).evaluate(parameters)
    noisy = AerEvaluator(graph, 1, "noisy", 16000, 42, NoiseConfig(0, 0, 0)).evaluate(parameters)
    assert abs(exact["mean_cut"] - noisy["mean_cut"]) < 6 * noisy["standard_error"]
