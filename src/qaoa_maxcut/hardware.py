"""Optional IBM Runtime job mode: prepare locally, submit explicitly, fetch later.

Only submit_job contacts a service to execute circuits. No token is written to results.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager

from .circuits import bind_parameters, qaoa_circuit
from .data import read_results
from .evaluation import AerEvaluator
from .experiments import write_json
from .objective import counts_statistics, cut_diagonal
from .problems import graph_from_dict


def prepare_plan(results: Path, run_index: int, output: Path, shots: int = 1024) -> dict:
    """Select a particular local trial; do not automatically cherry-pick the best."""
    data = read_results(results)
    if not 0 <= run_index < len(data["runs"]) or not 1 <= shots <= 8192:
        raise ValueError("Choose a valid run index and 1..8192 hardware shots per circuit.")
    if output.exists():
        raise FileExistsError(output)
    run = data["runs"][run_index]
    graph_data = next(g for g in data["graphs"] if g["graph_seed"] == run["graph_seed"])
    graph = graph_from_dict(graph_data)
    ideal = AerEvaluator(graph, run["depth"], "ideal", shots, 9876).evaluate(run["parameters"])
    plan = {
        "schema_version": 1, "kind": "hardware_plan", "status": "not_submitted",
        "source_run_id": run["run_id"], "source_mode": run["mode"],
        "graph": {"n": graph_data["n"], "edges": graph_data["edges"]},
        "depth": run["depth"], "parameters": run["parameters"],
        "exact_optimum": graph_data["exact"]["cut"], "ideal_expected_cut": ideal["mean_cut"],
        "shots_per_circuit": shots, "number_of_circuits": 2,
        "circuit_order": ["qaoa", "uniform_reference"], "seed_transpiler": 42,
        "measurement_convention": "Rightmost classical bit is graph vertex 0.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, plan)
    return plan


def plan_circuits(plan: dict) -> list[QuantumCircuit]:
    graph = graph_from_dict(plan["graph"])
    circuit, order = qaoa_circuit(graph, plan["depth"])
    circuit = bind_parameters(circuit, order, plan["parameters"])
    circuit.measure_all()
    reference = QuantumCircuit(len(graph))
    reference.h(range(len(graph)))
    reference.measure_all()
    return [circuit, reference]


def compile_for_backend(plan: dict, backend) -> tuple[list, dict]:
    if backend.num_qubits < plan["graph"]["n"]:
        raise ValueError("Backend has fewer qubits than the graph.")
    manager = generate_preset_pass_manager(backend=backend, optimization_level=1,
                                          seed_transpiler=plan["seed_transpiler"])
    circuits = manager.run(plan_circuits(plan))
    resources = {
        "backend": backend.name,
        "compiled_depths": [c.depth() for c in circuits],
        "operation_counts": [dict(c.count_ops()) for c in circuits],
        "logical_to_physical": [c.layout.final_index_layout() for c in circuits],
    }
    # Measurement classical bits still encode logical vertices after transpilation.
    return circuits, resources


def summarize_sampler_result(plan: dict, result) -> dict:
    if len(result) != 2:
        raise ValueError("Expected exactly two PUB results.")
    diagonal = cut_diagonal(graph_from_dict(plan["graph"]))
    values = {}
    for label, pub in zip(plan["circuit_order"], result):
        counts = pub.data.meas.get_counts()
        statistics = counts_statistics(counts, diagonal)
        statistics["approximation_ratio"] = statistics["mean_cut"] / plan["exact_optimum"]
        values[label] = {**statistics, "counts": counts}
    if len(values) != 2:
        raise ValueError("Expected QAOA and uniform-reference PUB results.")
    return values


def runtime_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = os.environ.get("QISKIT_IBM_TOKEN")
    instance = os.environ.get("QISKIT_IBM_INSTANCE")
    if not token or not instance:
        raise ValueError("Set QISKIT_IBM_TOKEN and QISKIT_IBM_INSTANCE in your terminal first.")
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance=instance)


def submit_job(plan_path: Path, backend_name: str, output: Path) -> dict:
    from qiskit_ibm_runtime import SamplerV2
    if output.exists():
        raise FileExistsError(output)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    service = runtime_service()
    backend = service.backend(backend_name)
    if backend.configuration().simulator:
        raise ValueError("Select a real IBM backend for hardware submission.")
    circuits, resources = compile_for_backend(plan, backend)
    record = {"kind": "hardware_job", "status": "submitting", "plan": plan, **resources,
              "submission_started_utc": datetime.now(timezone.utc).isoformat()}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, record)
    # Job mode avoids assuming the account has session access. Exactly two circuits.
    sampler = SamplerV2(mode=backend, options={"max_execution_time": 300})
    try:
        job = sampler.run(circuits, shots=plan["shots_per_circuit"])
    except Exception:
        record["status"] = "submission_failed_or_unknown_check_ibm_dashboard"
        write_json(output, record)
        raise
    record.update(job_id=job.job_id(), status="submitted")
    write_json(output, record)
    return record


def fetch_job(job_path: Path) -> dict:
    record = json.loads(job_path.read_text(encoding="utf-8"))
    job = runtime_service().job(record["job_id"])
    status = str(job.status())
    record["status"] = status
    if status.upper() == "DONE":
        record["results"] = summarize_sampler_result(record["plan"], job.result())
        record["job_metrics"] = json.loads(json.dumps(job.metrics(), default=str))
    record["last_fetched_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(job_path, record)
    return record


def offline_check(plan_path: Path, output: Path) -> dict:
    """Exercise Runtime's local testing mode on a 5-qubit fake device; no login."""
    from qiskit_ibm_runtime import SamplerV2
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    if output.exists():
        raise FileExistsError(output)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["graph"]["n"] > 5:
        raise ValueError("Offline hardware check uses FakeManilaV2; use configs/hardware.json (4 vertices).")
    backend = FakeManilaV2()
    circuits, resources = compile_for_backend(plan, backend)
    sampler = SamplerV2(mode=backend, options={"simulator": {"seed_simulator": 42}})
    result = sampler.run(circuits, shots=plan["shots_per_circuit"]).result()
    record = {"kind": "offline_hardware_check", "real_hardware": False, "plan": plan,
              **resources, "results": summarize_sampler_result(plan, result)}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, record)
    return record
