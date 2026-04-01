import networkx as nx
import numpy as np
import pytest
from qiskit.quantum_info import Statevector
from scipy.linalg import expm

from qaoa_maxcut.baselines import brute_force, greedy_cut
from qaoa_maxcut.circuits import bind_parameters, qaoa_circuit
from qaoa_maxcut.evaluation import AerEvaluator
from qaoa_maxcut.noise import NoiseConfig
from qaoa_maxcut.objective import cost_hamiltonian, counts_statistics, cut_diagonal, cut_value


def weighted_star():
    graph = nx.Graph()
    graph.add_weighted_edges_from([(0, 1, 1), (0, 2, 2)])
    return graph


def test_hamiltonian_matches_hand_calculated_asymmetric_graph():
    graph = weighted_star()
    # Basis order 000,001,...111. Vertex 0 is the RIGHTMOST bit.
    expected = np.array([0, 3, 1, 2, 2, 1, 3, 0], dtype=float)
    np.testing.assert_array_equal(cut_diagonal(graph), expected)
    np.testing.assert_allclose(cost_hamiltonian(graph).to_matrix(), np.diag(expected))
    assert cut_value(graph, int("001", 2)) == 3
    assert cut_value(graph, int("100", 2)) == 2


def test_count_scoring_and_standard_error():
    values = counts_statistics({"001": 3, "100": 1}, cut_diagonal(weighted_star()))
    assert values["mean_cut"] == 2.75
    assert values["standard_error"] == pytest.approx(0.25)
    assert values["optimal_probability"] == 0.75
    assert values["best_observed_bitstring"] == "001"
    assert counts_statistics({"001": 1}, cut_diagonal(weighted_star()))["standard_error"] is None


def test_qaoa_matches_independent_matrix_exponentials():
    graph = weighted_star()
    n, p = 3, 2
    gamma, beta = [0.23, -0.42], [-0.17, 0.31]
    # Construct B directly by flipping one integer bit, independent of Qiskit gates.
    mixer = np.zeros((2 ** n, 2 ** n))
    for z in range(2 ** n):
        for u in range(n):
            mixer[z ^ (1 << u), z] = 1
    diagonal = np.array([0, 3, 1, 2, 2, 1, 3, 0])
    state = np.ones(2 ** n, dtype=complex) / np.sqrt(2 ** n)
    for g, b in zip(gamma, beta):
        state = expm(-1j * b * mixer) @ (np.exp(-1j * g * diagonal) * state)
    circuit, order = qaoa_circuit(graph, p)
    actual = np.asarray(Statevector.from_instruction(bind_parameters(circuit, order, gamma + beta)))
    assert abs(np.vdot(state, actual)) ** 2 == pytest.approx(1, abs=1e-12)


def test_zero_angles_give_random_cut_expectation():
    evaluator = AerEvaluator(weighted_star(), 2, "ideal", 10, 7)
    assert evaluator.evaluate([0, 0, 0, 0])["mean_cut"] == pytest.approx(1.5)


def test_exact_and_sampled_expectations_agree():
    graph = weighted_star()
    parameters = [0.71, -0.22]
    exact = AerEvaluator(graph, 1, "ideal", 10, 42).evaluate(parameters)
    sampled = AerEvaluator(graph, 1, "shots", 16000, 42).evaluate(parameters)
    assert abs(exact["mean_cut"] - sampled["mean_cut"]) < 6 * sampled["standard_error"]


def test_noise_attaches_to_compiled_gates_and_changes_result():
    graph = nx.path_graph(2)
    parameters = [np.pi / 2, np.pi / 8]
    exact = AerEvaluator(graph, 1, "ideal", 10, 42).evaluate(parameters)
    noisy = AerEvaluator(graph, 1, "noisy", 8192, 42, NoiseConfig(1, 1, 0))
    result = noisy.evaluate(parameters)
    assert exact["mean_cut"] == pytest.approx(1, abs=1e-12)
    assert result["mean_cut"] == pytest.approx(0.5, abs=0.035)
    assert noisy.circuit_resources()["cx_count"] == 2


@pytest.mark.parametrize("graph, optimum", [(nx.cycle_graph(3), 2), (nx.cycle_graph(4), 4),
                                            (nx.complete_graph(4), 4), (weighted_star(), 3)])
def test_classical_baselines_on_known_graphs(graph, optimum):
    exact = brute_force(graph)
    greedy = greedy_cut(graph, 17)
    assert exact["cut"] == optimum
    assert greedy["cut"] <= optimum
    assert cut_value(graph, int(greedy["bitstring"], 2)) == greedy["cut"]
    assert greedy == greedy_cut(graph, 17)
