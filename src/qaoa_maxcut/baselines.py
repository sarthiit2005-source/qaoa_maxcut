"""Exact small-graph and multistart greedy Max-Cut baselines."""

import networkx as nx
import numpy as np

from .objective import cut_diagonal, cut_value
from .problems import validate_graph


def brute_force(graph: nx.Graph) -> dict:
    values = cut_diagonal(graph)
    best = int(np.argmax(values))
    return {"cut": float(values[best]), "bitstring": format(best, f"0{len(graph)}b"),
            "assignments_evaluated": len(values)}


def greedy_cut(graph: nx.Graph, seed: int, restarts: int = 8) -> dict:
    """Start randomly, then repeatedly make the best strictly improving vertex flip."""
    validate_graph(graph)
    if restarts < 1:
        raise ValueError("Greedy restarts must be positive.")
    rng = np.random.default_rng(seed)
    best_value, best_assignment, evaluations = -np.inf, 0, 0
    for _ in range(restarts):
        assignment = int(rng.integers(0, 2 ** len(graph)))
        value = cut_value(graph, assignment)
        evaluations += 1
        while True:
            candidates = [cut_value(graph, assignment ^ (1 << u)) for u in range(len(graph))]
            evaluations += len(graph)
            vertex = int(np.argmax(candidates))
            if candidates[vertex] <= value + 1e-12:
                break
            assignment ^= 1 << vertex
            value = candidates[vertex]
        if value > best_value:
            best_value, best_assignment = value, assignment
    return {"cut": float(best_value), "bitstring": format(best_assignment, f"0{len(graph)}b"),
            "score_evaluations": evaluations, "restarts": restarts, "seed": seed}
