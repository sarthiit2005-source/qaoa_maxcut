# Verification record

Initial verification date: 10 October 2026 (India time). Expanded-benchmark checks: 11 October 2026.

## Environment

- Windows, Python 3.12.14, isolated project `.venv`.
- Qiskit 2.2.3, Qiskit Aer 0.17.2, SciPy 1.16.3, NumPy 2.3.5.
- NetworkX 3.5, Matplotlib 3.10.7, pytest 8.4.2.
- Optional IBM Runtime 0.43.1 installed for offline integration testing.
- `requirements-lock.txt` records the complete verified dependency snapshot. Its `sspilib` entry is Windows-only.
- `pip check`: no broken requirements.

Top-level dependencies are pinned in `pyproject.toml`; the complete snapshot also pins transitive packages. Local results record package versions and the platform. Python 3.13 and Linux are included in the CI configuration, but were not locally tested in this session. No remote GitHub CI run is claimed.

## Automated tests

The initial full test run completed with **28 passed**. It covered:

- All basis-state cut scores and the cost Hamiltonian on an asymmetric weighted graph.
- QAOA states checked against independent matrix exponentials.
- Exact/sampled expectation agreement and a known two-qubit optimum.
- Noise attachment and zero-noise consistency.
- Exact and greedy baselines on known graphs.
- Hard evaluation limits and preservation of the best evaluated parameters for all three optimizers.
- Input validation, seeded graph generation, and repeatability of complete local experiments.
- Accounting for training versus final calls and shots.
- Variance calculation, report output, and prevention of accidental output-directory overwrites.
- Logical-bit interpretation after a nontrivial physical layout.
- IBM Runtime SamplerV2 with a fake device, without account access.
- Mocked submission/retrieval bookkeeping, refusal to overwrite a job record, and missing-credential handling.

Runtime 0.43.1 emits an upstream deprecation warning for `IBMFractionalTranslationPlugin` during plugin discovery. Tests still pass. This project does not select that deprecated plugin. The separate warning about combining a backend and custom basis in local compilation was addressed by compiling the illustrative all-to-all circuits directly to the explicit basis.

## Executed workflows

- The quick configuration completed all 18 trials and generated raw data, CSV tables, a report, and a plot.
- The small hardware-training configuration completed its local optimization.
- Hardware-plan preparation completed without credentials.
- The standalone hardware-check command completed both circuits on `FakeManilaV2` with 1,024 shots each. Its result is explicitly labeled `real_hardware: false`.
- The directly runnable VS Code example completed when launched from outside the repository directory, confirming that paths are resolved from the file location.
- Its 18 trials matched the earlier quick run exactly in parameters, histories, final results, evaluation counts, and circuit resources; timings were excluded from that comparison.
- The three main-study graph instances were checked with NetworkX and are pairwise non-isomorphic.
- The main study completed all 243 trials in approximately 552 seconds on this machine. It recorded 16,717 training circuit evaluations and 6,241,280 total simulated measurement shots, including final evaluations. Exact statevector evaluations contribute zero shots to that count.
- All 243 records passed budget, shot-count, parameter-length, and approximation-ratio range checks. The summary has 27 groups of nine trials, each spanning all three graphs.
- Quick and study plots were visually inspected after report regeneration.

The checked-in examples are actual outputs of these commands, not manually invented scores. Each result contains seeds and graph edges. Wall-clock times are observations from a shared development machine, not a controlled performance benchmark.

## Limits of verification

- At the initial verification, no IBM QPU job had been submitted. A later completed live job is recorded below; it verifies this account/backend workflow, not every backend or account configuration.
- No GPU path is implemented or claimed.
- The noise model is illustrative; it was not fitted to a real backend.
- The graph sample is small. Seeded generation can produce isomorphic instances, so results are not universal optimizer rankings.
- Classical baselines are quality references; no quantum speedup is established.
- Package installation succeeded in an isolated local environment. Long-term reproducibility still depends on compatible Python/platform binaries being available.

One isolated test invocation encountered a Windows native-library initialization error while importing Aer, before any test ran. The complete suite and the same isolated hardware subset subsequently passed. No project-code change was needed to resolve that transient invocation; its root cause was not established.

## Expanded benchmark and figure checks (11 October 2026)

- The extended full suite completed with **32 passed** in 12.62 seconds. Added tests verify serial/parallel numerical equivalence, retention of stopped convergence histories without invented calls, histogram probability and expected-cut preservation, and lossless gzip record reading.
- The first extended test invocation could not create pytest temporary directories inside the restricted system temp location. Running with `--basetemp .tmp/tests-readme` in the writable project directory resolved those setup errors; all tests passed.
- Optional `pylatexenc==2.10` was installed for actual Qiskit circuit drawings, the editable project metadata was refreshed, and `pip check` reported no broken requirements.
- All six figure layouts were first generated from the completed initial study and visually inspected before using the expanded benchmark. Preview outputs stay in the ignored `.tmp/` folder.
- The expanded benchmark completed all **810 trials** in **1,182.65 seconds** (about 20 minutes) with four worker processes. It recorded **149,778 training evaluations**, **150,588 total evaluations**, and **202,463,232 simulated measurement shots**, including independent final evaluations. Exact statevector calls use zero shots.
- All records passed history-length, parameter-length, hard-budget, final-count, shot-accounting, and ratio-range checks. Five graphs were verified pairwise non-isomorphic. All 54 summary groups include 15 trials across all five graphs. There were 290 reported converged runs and 520 budget-exhausted runs; convergence messages are optimizer termination statuses, not proof of global optima.
- The 78,405,209-byte raw record was compressed losslessly to 11,107,643 bytes. Reading the gzip record reproduced the complete JSON object exactly. `sample_results/readme-benchmark/validation.json` records the audit and compressed-file hash. The uncompressed local file and redundant worker checkpoints are excluded from the distributed repo.
- Reports were successfully regenerated directly from gzip data. All six final PNG figures were visually inspected; matching SVGs are included. The manifest's source hash and all 12 image hashes were checked against the actual files.
- The fixed-parameter histogram completed two extra evaluations of 16,384 shots each, outside the benchmark totals above. Actual counts and fixed parameters are preserved in `docs/images/measurement-data.json`.

## Completed live hardware workflow (11 October 2026)

The user submitted and fetched job `db5iv1svf2bc73d00bd0` on `ibm_kingston`. The saved record has status DONE and both 4,096-shot results. QAOA expected cut was 2.92236328125 (SE 0.0176873), versus ideal 2.99999997992 and uniform-reference hardware mean 1.96923828125. The four-cycle optimum is 4. Compilation recorded depths 43/4 and 14 CZ gates for QAOA. IBM metrics report completion at 2026-10-11T07:12:50.24588Z and 4 seconds of quantum usage.

The completed job is preserved as `sample_results/hardware-kingston.json`. The downloaded histogram PNG was visually inspected; the downloaded circuit SVG was parsed and rendered for inspection. Both exports are included in the README. This confirms one live submission/retrieval workflow; no further job was submitted while preparing this documentation.
