"""Max-Cut scores, diagonal Hamiltonian, and measurement statistics.

Qiskit strings read q[n-1] ... q[0]; integer bit u is always vertex u.
"""

import networkx as nx
import numpy as np
from qiskit.quantum_info import SparsePauliOp

from .problems import validate_graph


def cut_value(graph: nx.Graph, assignment: int) -> float:
    """Score an assignment encoded as an integer (bit u is vertex u)."""
    if not 0 <= assignment < 2 ** len(graph):
        raise ValueError("Assignment does not fit the graph.")
    return float(sum(data.get("weight", 1.0)
                     for u, v, data in graph.edges(data=True)
                     if ((assignment >> u) & 1) != ((assignment >> v) & 1)))


def cut_diagonal(graph: nx.Graph) -> np.ndarray:
    """C(z) in statevector basis order, for deliberately small graphs."""
    validate_graph(graph)
    if len(graph) > 20:
        raise ValueError("Exact enumeration is capped at 20 vertices.")
    assignments = np.arange(2 ** len(graph), dtype=np.uint64)
    scores = np.zeros(len(assignments), dtype=float)
    for u, v, data in graph.edges(data=True):
        scores += float(data.get("weight", 1.0)) * (
            ((assignments >> u) & 1) != ((assignments >> v) & 1)
        )
    return scores


def cost_hamiltonian(graph: nx.Graph) -> SparsePauliOp:
    """C = sum_(u,v) w_uv (I - Z_u Z_v)/2, without normalization."""
    validate_graph(graph)
    n = len(graph)
    terms = []
    for u, v, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        pauli = ["I"] * n
        pauli[n - 1 - u] = pauli[n - 1 - v] = "Z"
        terms.extend([("I" * n, weight / 2), ("".join(pauli), -weight / 2)])
    return SparsePauliOp.from_list(terms).simplify()


def counts_statistics(counts: dict[str, int], diagonal: np.ndarray) -> dict:
    """Estimate mean and its shot standard error; preserve observed outcomes."""
    if not counts or any(not isinstance(c, (int, np.integer)) or c < 0
                         for c in counts.values()):
        raise ValueError("Counts must contain nonnegative integer frequencies.")
    counts = {key: int(count) for key, count in counts.items() if count > 0}
    shots = sum(counts.values())
    if shots < 1:
        raise ValueError("Need at least one shot.")
    outcomes = np.array([int(bits.replace(" ", ""), 2) for bits in counts])
    if np.any(outcomes >= len(diagonal)):
        raise ValueError("Measurement bitstrings exceed graph width.")
    weights = np.array(list(counts.values()), dtype=float)
    scores = diagonal[outcomes]
    mean = float(np.dot(weights, scores) / shots)
    variance = float(np.dot(weights, (scores - mean) ** 2) / (shots - 1)) if shots > 1 else None
    best = int(np.argmax(scores))
    return {
        "mean_cut": mean,
        "standard_error": float(np.sqrt(variance / shots)) if variance is not None else None,
        "shots": shots,
        "best_observed_cut": float(scores[best]),
        "best_observed_bitstring": list(counts)[best],
        "optimal_probability": float(weights[np.isclose(scores, diagonal.max())].sum() / shots),
    }
