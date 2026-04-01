import json

import networkx as nx
import pytest
from qiskit import transpile
from qiskit.primitives import BackendSamplerV2
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_aer import AerSimulator

from qaoa_maxcut.hardware import compile_for_backend, summarize_sampler_result
from qaoa_maxcut.problems import graph_to_dict


def test_logical_bit_order_survives_nontrivial_physical_layout():
    graph = nx.Graph()
    graph.add_weighted_edges_from([(0, 1, 1), (0, 2, 2)])
    plan = {"graph": graph_to_dict(graph), "depth": 1, "parameters": [0.6, -0.2],
            "seed_transpiler": 42, "exact_optimum": 3,
            "circuit_order": ["qaoa", "uniform_reference"]}
    backend = GenericBackendV2(5, basis_gates=["rz", "sx", "x", "cx"], seed=42)
    circuits, _ = compile_for_backend(plan, backend)
    # Replace the prepared state with logical vertex 0=1, then map it to physical qubit 4.
    from qiskit import QuantumCircuit
    known = QuantumCircuit(3)
    known.x(0)
    known.measure_all()
    known = transpile(known, backend=backend, initial_layout=[4, 1, 3], optimization_level=0)
    sampler = BackendSamplerV2(backend=AerSimulator(max_parallel_threads=1),
                               options={"default_shots": 64, "seed_simulator": 42})
    result = sampler.run([known, known]).result()
    stats = summarize_sampler_result(plan, result)
    assert stats["qaoa"]["counts"] == {"001": 64}
    assert stats["qaoa"]["mean_cut"] == 3
    assert all(c.num_clbits == 3 for c in circuits)


def test_runtime_offline_workflow(tmp_path):
    pytest.importorskip("qiskit_ibm_runtime")
    from qaoa_maxcut.hardware import offline_check
    plan = {"graph": graph_to_dict(nx.cycle_graph(4)), "depth": 1,
            "parameters": [0.6, -0.2], "seed_transpiler": 42, "exact_optimum": 4,
            "shots_per_circuit": 128, "circuit_order": ["qaoa", "uniform_reference"]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    result = offline_check(plan_path, tmp_path / "result.json")
    assert result["real_hardware"] is False
    assert set(result["results"]) == {"qaoa", "uniform_reference"}
    assert result["results"]["qaoa"]["shots"] == 128


def test_submission_and_fetch_save_job_without_credentials(tmp_path, monkeypatch):
    """Exercise job bookkeeping without contacting IBM or spending allocation."""
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    from types import SimpleNamespace
    from qaoa_maxcut import hardware
    plan = {"graph": graph_to_dict(nx.cycle_graph(4)), "depth": 1,
            "parameters": [0.6, -0.2], "seed_transpiler": 42, "exact_optimum": 4,
            "shots_per_circuit": 16, "circuit_order": ["qaoa", "uniform_reference"]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    pub = SimpleNamespace(data=SimpleNamespace(meas=SimpleNamespace(get_counts=lambda: {"0101": 16})))
    job = SimpleNamespace(job_id=lambda: "test-job-id", status=lambda: "DONE",
                          result=lambda: [pub, pub], metrics=lambda: {"timestamps": {"finished": "test"}})
    backend = SimpleNamespace(configuration=lambda: SimpleNamespace(simulator=False))
    service = SimpleNamespace(backend=lambda _: backend, job=lambda _: job)
    calls = []

    class SamplerStub:
        def __init__(self, mode, options):
            assert mode is backend

        def run(self, circuits, shots):
            calls.append((len(circuits), shots))
            return job

    monkeypatch.setattr(hardware, "runtime_service", lambda: service)
    monkeypatch.setattr(hardware, "compile_for_backend", lambda plan, backend: ([None, None], {"backend": "test"}))
    monkeypatch.setattr(runtime, "SamplerV2", SamplerStub)
    output = tmp_path / "job.json"
    submitted = hardware.submit_job(plan_path, "test", output)
    assert submitted["job_id"] == "test-job-id"
    assert calls == [(2, 16)]
    fetched = hardware.fetch_job(output)
    assert fetched["status"] == "DONE"
    assert fetched["results"]["qaoa"]["approximation_ratio"] == 1
    assert "last_fetched_utc" in fetched
    assert "token" not in output.read_text().lower()
    with pytest.raises(FileExistsError):
        hardware.submit_job(plan_path, "test", output)
    assert calls == [(2, 16)]


def test_missing_account_variables_fail_before_service_creation(monkeypatch):
    pytest.importorskip("qiskit_ibm_runtime")
    from qaoa_maxcut.hardware import runtime_service
    monkeypatch.delenv("QISKIT_IBM_TOKEN", raising=False)
    monkeypatch.delenv("QISKIT_IBM_INSTANCE", raising=False)
    with pytest.raises(ValueError, match="Set QISKIT_IBM_TOKEN"):
        runtime_service()
