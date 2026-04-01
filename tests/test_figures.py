import gzip
import json

import networkx as nx
import numpy as np
import pytest

from qaoa_maxcut.data import read_results
from qaoa_maxcut.figures import cut_distribution, incumbent_traces, probability_vector
from qaoa_maxcut.objective import cut_diagonal


def test_stopped_incumbent_is_retained_without_inventing_evaluations():
    history = [{"best_so_far_cut": x} for x in (2, 4, 4)]
    record = {"config": {"evaluation_budget": 5},
              "graphs": [{"graph_seed": 11, "exact": {"cut": 8}}],
              "runs": [{"mode": "shots", "optimizer": "COBYLA", "depth": 2,
                        "graph_seed": 11, "history": history}]}
    np.testing.assert_array_equal(incumbent_traces(record, "shots", "COBYLA", 2),
                                  [[0.25, 0.5, 0.5, 0.5, 0.5]])
    assert len(history) == 3
    with pytest.raises(ValueError, match="No matching"):
        incumbent_traces(record, "ideal", "COBYLA", 2)


def test_histogram_preserves_all_probability_and_expected_cut():
    graph = nx.Graph()
    graph.add_weighted_edges_from([(0, 1, 2), (1, 2, 1)])
    probabilities = probability_vector({"001": 2, "100": 1, "000": 1}, 3)
    assert probabilities[1] == 0.5
    assert probabilities[4] == 0.25
    diagonal = cut_diagonal(graph)
    values, masses = cut_distribution(probabilities, diagonal)
    assert masses.sum() == pytest.approx(1)
    assert values @ masses == pytest.approx(probabilities @ diagonal)
    assert values @ masses == pytest.approx(1.25)


def test_gzip_records_are_lossless_and_readable(tmp_path):
    record = {"runs": [{"parameters": [0.123456789], "counts": {"001": 17}}]}
    payload = json.dumps(record).encode("utf-8")
    plain, compressed = tmp_path / "results.json", tmp_path / "results.json.gz"
    plain.write_bytes(payload)
    compressed.write_bytes(gzip.compress(payload, mtime=0))
    assert read_results(plain) == read_results(compressed) == record
