"""Run this file from VS Code after installing the project in your selected .venv."""

from datetime import datetime, timezone
from pathlib import Path

from qaoa_maxcut.experiments import ExperimentConfig, run_experiment
from qaoa_maxcut.reporting import create_report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    config = ExperimentConfig.from_file(root / "configs" / "quick.json")
    output = root / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_experiment(config, output)
    create_report(output / "results.json")
    print(f"Open {output / 'report.md'}")
