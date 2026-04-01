"""Graph validation, seeded graph generation, and JSON serialization."""

import math

import networkx as nx


def validate_graph(graph: nx.Graph) -> None:
    """Require a simple, nonempty graph with positive weights and labels 0..n-1."""
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("Use a simple undirected graph.")
    if set(graph.nodes) != set(range(len(graph))):
        raise ValueError("Vertices must be labeled 0 through n-1.")
    if graph.number_of_edges() == 0 or nx.number_of_selfloops(graph):
        raise ValueError("The graph needs edges and must not contain self-loops.")
    for _, _, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("Edge weights must be finite and positive.")


def regular_graph(n: int, degree: int, seed: int) -> nx.Graph:
    """Generate one connected graph, with bounded retries for connectedness."""
    if not 2 <= n <= 16:
        raise ValueError("This small-graph study supports 2..16 vertices.")
    if not 1 <= degree < n or (n * degree) % 2:
        raise ValueError("Require 1 <= degree < n and even n*degree.")
    if degree == 1 and n != 2:
        raise ValueError("A connected 1-regular graph has exactly two vertices.")
    if seed < 0:
        raise ValueError("Seeds must be nonnegative.")
    for attempt in range(100):
        graph = nx.random_regular_graph(degree, n, seed=seed + attempt)
        if nx.is_connected(graph):
            # Stable edge and node order makes circuit construction reproducible.
            ordered = nx.Graph()
            ordered.add_nodes_from(range(n))
            ordered.add_edges_from(sorted(tuple(sorted(e)) for e in graph.edges))
            return ordered
    raise ValueError("No connected graph found after 100 seeded attempts.")


def graph_to_dict(graph: nx.Graph) -> dict:
    validate_graph(graph)
    return {
        "n": len(graph),
        "edges": [[int(u), int(v), float(d.get("weight", 1.0))]
                  for u, v, d in graph.edges(data=True)],
    }


def graph_from_dict(data: dict) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(data["n"]))
    graph.add_weighted_edges_from(data["edges"])
    validate_graph(graph)
    return graph
