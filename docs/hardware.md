# Optional IBM hardware experiment

The core study runs locally. This extension evaluates already optimized parameters on a real device and compares them with a uniform-superposition reference. It does not run the full optimizer on a QPU. That design bounds circuit submissions and makes the distinction between optimization and hardware execution easy to explain.

## 1. Install the optional dependency

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,hardware]"
```

The pinned IBM Runtime version is 0.43.1. Hardware APIs and available backends can change; this integration is tested locally against the pinned version.

## 2. Optimize a small four-vertex instance locally

```powershell
.\.venv\Scripts\python.exe -m qaoa_maxcut run --config configs/hardware.json --output results/hardware-training
.\.venv\Scripts\python.exe -m qaoa_maxcut hardware-prepare --results results/hardware-training/results.json --run-index 0 --shots 1024 --output results/hardware-plan.json
```

Preparation does not use credentials or submit a job. The plan records the graph, parameters, source run, exact optimum, ideal expectation, shot count, and circuit ordering. Choose `--run-index` explicitly if using a larger study; the command does not select the best noisy observation automatically.

## 3. Test the Runtime path offline

```powershell
.\.venv\Scripts\python.exe -m qaoa_maxcut hardware-check --plan results/hardware-plan.json --output results/hardware-offline.json
```

This uses IBM Runtime's local testing mode with `FakeManilaV2`, a five-qubit fake backend. It exercises compilation, SamplerV2 result decoding, and statistics without contacting IBM. It is a simulation using a fake device snapshot, not a hardware result or a current calibration. Plans larger than five vertices are rejected by this check.

## 4. Set account information and choose a real backend

Use your IBM Quantum Platform account to obtain an API key, service instance CRN, and the name of an accessible backend. This project reads the two environment variables below; it does not save them to disk:

```powershell
$env:QISKIT_IBM_TOKEN = 'YOUR_API_KEY'
$env:QISKIT_IBM_INSTANCE = 'YOUR_INSTANCE_CRN'
```

Replace these example values in your own terminal. Do not put credentials in repository files or result JSON. Account plans determine access and usage limits; the code does not assume that a free allocation is available.

## 5. Submit, then retrieve

```powershell
.\.venv\Scripts\python.exe -m qaoa_maxcut hardware-submit --plan results/hardware-plan.json --backend YOUR_BACKEND_NAME --output results/hardware-job.json
.\.venv\Scripts\python.exe -m qaoa_maxcut hardware-fetch results/hardware-job.json
```

**`hardware-submit` executes on your account and consumes its available allocation.** It compiles for the named backend and submits exactly two circuits with the plan's shots per circuit (1,024 each in the example). It uses job mode and sets a 300-second execution limit; that limit is not a wall-clock queue timeout or a guarantee of pricing. Submission returns the job ID without waiting for the queue. Fetch again later if the job is not `DONE`; fetching does not resubmit it.

The job file stores the job ID immediately after submission, backend name, compiled depths, operation counts, logical-to-physical mapping, and the full plan. Once completed, it also stores counts and measured quality for both circuits. If the connection is lost during submission before a job ID is saved, inspect your IBM jobs dashboard before submitting again.

Transpilation preserves the logical classical-bit ordering. The scorer uses the measurement register's classical bits, not the device's physical qubit numbers. A test deliberately maps logical vertex 0 onto physical qubit 4 and checks the resulting cut score.

## What to report

Report backend, job ID, execution date, circuit depth/operation counts, shots, graph, parameters, ideal expected score, measured expected score, and sampling error. Keep the classical baseline and uniform-reference results beside the QAOA result. A hardware run worse than the ideal simulation is still a valid measurement. Do not label local fake-backend outputs as QPU outputs or infer quantum advantage from this small experiment.

No actual IBM job is executed by installation, tests, quick experiments, or plan preparation.
