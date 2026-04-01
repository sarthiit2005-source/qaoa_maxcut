"""QAOA ansatz using U_C(gamma)=exp(-i gamma C), U_B(beta)=exp(-i beta B)."""

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

from .problems import validate_graph


def qaoa_circuit(graph: nx.Graph, depth: int) -> tuple[QuantumCircuit, tuple]:
    """Return circuit and explicit [gamma_0..gamma_p-1, beta_0..beta_p-1] order."""
    validate_graph(graph)
    if not isinstance(depth, int) or depth < 1:
        raise ValueError("Depth must be a positive integer.")
    gammas = ParameterVector("gamma", depth)
    betas = ParameterVector("beta", depth)
    circuit = QuantumCircuit(len(graph))
    circuit.h(range(len(graph)))
    for layer in range(depth):
        for u, v, data in graph.edges(data=True):
            # RZZ(theta)=exp(-i theta ZZ/2). Drop only C's global identity phase.
            circuit.rzz(-gammas[layer] * float(data.get("weight", 1.0)), u, v)
        for qubit in range(len(graph)):
            circuit.rx(2 * betas[layer], qubit)
    return circuit, tuple(gammas) + tuple(betas)


def bind_parameters(circuit: QuantumCircuit, order: tuple, values) -> QuantumCircuit:
    values = np.asarray(values, dtype=float)
    if values.shape != (len(order),) or not np.all(np.isfinite(values)):
        raise ValueError("Parameter vector must have 2p finite values.")
    return circuit.assign_parameters(dict(zip(order, values)))
