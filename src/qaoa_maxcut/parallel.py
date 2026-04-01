"""Optional laptop runner: independent graph/start shards, unchanged trial math.

This is execution plumbing; understanding it is not needed to study QAOA.
Each process calls the ordinary serial runner on one graph and starting seed.
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from time import perf_counter

from .experiments import environment_info, run_experiment, write_json


def _run_shard(config, output):
    return run_experiment(config, output, progress=partial(print, flush=True))


def run_parallel_experiment(config, output: Path, workers: int = 4, progress=print):
    """Merge complete shards without changing seeds, budgets, or final evaluation."""
    config.validate()
    if not 1 <= workers <= 4:
        raise ValueError("Use 1..4 workers to keep this laptop workflow bounded.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1, "status": "running", "config": asdict(config),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": environment_info(), "graphs": [], "runs": [],
        "execution": {"workers": workers, "aer_threads_per_worker": 1,
                      "sharding": "one graph seed and one run seed per process task"},
    }
    write_json(output / "results.json", record)
    started = perf_counter()
    seen = set()
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            tasks = []
            for graph_seed in config.graph_seeds:
                for run_seed in config.run_seeds:
                    shard = replace(config, graph_seeds=[graph_seed], run_seeds=[run_seed])
                    directory = output / "_shards" / f"g{graph_seed}-s{run_seed}"
                    tasks.append(pool.submit(_run_shard, shard, directory))
            for future in as_completed(tasks):
                data = future.result()
                for graph in data["graphs"]:
                    if graph["graph_seed"] not in seen:
                        record["graphs"].append(graph)
                        seen.add(graph["graph_seed"])
                record["runs"].extend(data["runs"])
                write_json(output / "results.json", record)
                progress(f"Merged {len(record['runs'])} completed trials.")
        # Stable order irrespective of operating-system process scheduling.
        record["graphs"].sort(key=lambda g: config.graph_seeds.index(g["graph_seed"]))
        record["runs"].sort(key=lambda r: (
            config.graph_seeds.index(r["graph_seed"]), config.depths.index(r["depth"]),
            config.run_seeds.index(r["run_seed"]), config.modes.index(r["mode"]),
            config.optimizers.index(r["optimizer"]),
        ))
        record["status"] = "complete"
    except BaseException:
        record["status"] = "interrupted_or_failed"
        raise
    finally:
        record["elapsed_seconds"] = perf_counter() - started
        write_json(output / "results.json", record)
    return record
