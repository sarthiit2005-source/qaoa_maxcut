"""Terminal entry point. The experiment code is also directly importable in Python."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .experiments import ExperimentConfig, run_experiment
from .reporting import create_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reproducible QAOA Max-Cut study")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run local simulations and save reports")
    run.add_argument("--config", type=Path, default=Path("configs/quick.json"))
    run.add_argument("--output", type=Path)
    run.add_argument("--workers", type=int, default=1, help="1..4 independent laptop worker processes")
    report = sub.add_parser("report", help="Regenerate reports from saved raw data")
    report.add_argument("results", type=Path)
    figures = sub.add_parser("figures", help="Generate six README figures from completed experiment data")
    figures.add_argument("--results", type=Path, required=True)
    figures.add_argument("--output", type=Path, default=Path("docs/images"))
    figures.add_argument("--example-depth", type=int, default=3)
    prepare = sub.add_parser("hardware-prepare", help="Prepare two hardware circuits locally, no login")
    prepare.add_argument("--results", type=Path, required=True)
    prepare.add_argument("--run-index", type=int, default=0)
    prepare.add_argument("--shots", type=int, default=1024)
    prepare.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("hardware-check", help="Offline Runtime integration check on a fake device")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    submit = sub.add_parser("hardware-submit", help="Submit to real IBM hardware using your account")
    submit.add_argument("--plan", type=Path, required=True)
    submit.add_argument("--backend", required=True)
    submit.add_argument("--output", type=Path, required=True)
    fetch = sub.add_parser("hardware-fetch", help="Fetch status/results of a previously submitted job")
    fetch.add_argument("job", type=Path)
    args = parser.parse_args(argv)
    if args.command == "run":
        output = args.output or Path("results") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        config = ExperimentConfig.from_file(args.config)
        if args.workers == 1:
            run_experiment(config, output)
        else:
            from .parallel import run_parallel_experiment
            run_parallel_experiment(config, output, args.workers)
        create_report(output / "results.json")
        print(f"Saved results and report: {output.resolve()}")
    elif args.command == "report":
        create_report(args.results)
        print(f"Updated reports in {args.results.parent.resolve()}")
    elif args.command == "figures":
        from .figures import create_figures
        manifest = create_figures(args.results, args.output, args.example_depth)
        print(f"Saved six PNG/SVG figures from {manifest['benchmark_trials']} trials: {args.output.resolve()}")
    else:
        from .hardware import fetch_job, offline_check, prepare_plan, submit_job
        if args.command == "hardware-prepare":
            plan = prepare_plan(args.results, args.run_index, args.output, args.shots)
            print(f"Prepared {plan['source_run_id']}; 2 circuits, {args.shots} shots each. No job submitted.")
        elif args.command == "hardware-check":
            offline_check(args.plan, args.output)
            print(f"Offline fake-device result saved: {args.output}. This is not real hardware.")
        elif args.command == "hardware-submit":
            result = submit_job(args.plan, args.backend, args.output)
            print(f"Submitted job {result['job_id']}. Fetch it with hardware-fetch {args.output}")
        elif args.command == "hardware-fetch":
            result = fetch_job(args.job)
            print(f"Job {result['job_id']}: {result['status']}")
