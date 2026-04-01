from qaoa_maxcut.experiments import ExperimentConfig, run_experiment
from qaoa_maxcut.parallel import run_parallel_experiment


def test_parallel_runner_preserves_serial_trial_results(tmp_path):
    config = ExperimentConfig(n=4, degree=2, graph_seeds=[11, 23], run_seeds=[101],
                              depths=[1], optimizers=["COBYLA"], modes=["ideal", "shots"],
                              evaluation_budget=5, shots=64, final_shots=128)
    serial = run_experiment(config, tmp_path / "serial", progress=lambda _: None)
    parallel = run_parallel_experiment(config, tmp_path / "parallel", workers=2, progress=lambda _: None)
    assert parallel["status"] == "complete"
    assert len(parallel["runs"]) == 4
    for a, b in zip(serial["runs"], parallel["runs"]):
        for key in ("run_id", "parameters", "final", "history", "objective_evaluations"):
            assert a[key] == b[key]
