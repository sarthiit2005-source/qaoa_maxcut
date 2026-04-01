"""Execute all three local evaluation modes through Qiskit Aer on CPU."""

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from .circuits import bind_parameters, qaoa_circuit
from .noise import NoiseConfig, make_noise_model
from .objective import counts_statistics, cut_diagonal

MODES = ("ideal", "shots", "noisy")


class AerEvaluator:
    """Compile once; bind and execute once per objective or final evaluation.

    ideal: exact pure-state expectation; shots: ideal circuit with sampling;
    noisy: density-matrix simulation of gate/readout errors with sampling.
    """

    def __init__(self, graph, depth: int, mode: str, shots: int, seed: int,
                 noise: NoiseConfig | None = None):
        if mode not in MODES or shots < 1 or seed < 0:
            raise ValueError("Invalid mode, shot count, or seed.")
        if mode == "noisy" and len(graph) > 10:
            raise ValueError("Density-matrix mode is capped at 10 vertices for laptop use.")
        self.mode, self.shots = mode, shots
        self.diagonal = cut_diagonal(graph)
        self.rng = np.random.default_rng(seed)
        circuit, self.order = qaoa_circuit(graph, depth)
        self.logical_depth = circuit.depth()
        self.backend = AerSimulator(
            method="density_matrix" if mode == "noisy" else "statevector",
            device="CPU", max_parallel_threads=1,
            noise_model=make_noise_model(noise or NoiseConfig()) if mode == "noisy" else None,
        )
        if mode != "ideal":
            circuit.measure_all()
        # Fixed basis exposes all two-qubit interactions to the noise model.
        self.circuit = transpile(circuit, basis_gates=["h", "rx", "rz", "cx"],
                                 optimization_level=1, seed_transpiler=seed)
        if mode == "ideal":
            self.circuit.save_statevector()

    def evaluate(self, parameters, shots: int | None = None) -> dict:
        sample_shots = self.shots if shots is None else shots
        if sample_shots < 1:
            raise ValueError("Shots must be positive.")
        circuit = bind_parameters(self.circuit, self.order, parameters)
        seed = int(self.rng.integers(0, 2 ** 31 - 1))
        result = self.backend.run(circuit, shots=sample_shots, seed_simulator=seed).result()
        if not result.success:
            raise RuntimeError(f"Aer failed: {result.status}")
        if self.mode == "ideal":
            probabilities = np.abs(np.asarray(result.get_statevector())) ** 2
            return {
                "mean_cut": float(probabilities @ self.diagonal),
                "standard_error": 0.0, "shots": 0,
                "optimal_probability": float(probabilities[np.isclose(self.diagonal, self.diagonal.max())].sum()),
                "best_observed_cut": None, "best_observed_bitstring": None,
                "counts": None, "simulator_seed": seed,
            }
        counts = {key: int(value) for key, value in result.get_counts().items()}
        return {**counts_statistics(counts, self.diagonal), "counts": counts,
                "simulator_seed": seed}

    def circuit_resources(self) -> dict:
        return {"logical_depth": self.logical_depth, "compiled_depth": self.circuit.depth(),
                "cx_count": int(self.circuit.count_ops().get("cx", 0)),
                "device": "CPU", "basis_gates": ["h", "rx", "rz", "cx"]}
