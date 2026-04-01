# README figures and experiment design

The six figures are produced by the project's code from saved Aer experiments. They are scientific plots and a drawing of the actual circuit, not generated illustrations. PNG files are embedded in the README; SVG files provide scalable versions. Every source record and the fresh histogram measurements are preserved.

## Expanded laptop benchmark

| Setting | Value |
|---|---|
| Graphs | Five pairwise non-isomorphic, eight-vertex, 3-regular graphs; 12 edges each |
| Graph seeds | 11, 23, 37, 71, 89 |
| Starting seeds | 101, 202, 303 on every graph |
| Depths | p = 1, 2, 3, 4, 5, 6 |
| Optimizers | COBYLA, Nelder-Mead, Powell |
| Modes | Exact ideal, finite-shot ideal, illustrative noisy simulation |
| Training cap | 240 actual objective evaluations per trial; early stopping allowed |
| Training shots | 2,048 per sampled evaluation |
| Independent final shots | 16,384 per sampled trial |
| Total trials | 5 × 3 × 6 × 3 × 3 = 810 |
| Local execution | Four processes; one Aer thread per process; CPU |

This is a substantial small-scale QAOA experiment suitable for a laptop and an introductory research project. Eight qubits keep exact classical optima available for verification. Six depths probe increasing circuit complexity; p=6 has 12 trainable angles. Multiple graphs and starts reveal dependence on graph structure and initialization. The budget is a fixed experimental constraint, not a claim that every optimizer has converged. More shots reduce sampling variation without removing optimizer limitations.

The graph seeds were checked for distinct structure before the benchmark. They were not selected for favorable QAOA scores. Five graphs still provide a small sample; there is no claim of performance on arbitrary large instances, quantum advantage, or an industrial workload.

Noise uses depolarization probabilities 0.001 for one-qubit gates and 0.01 for two-qubit gates, with symmetric readout error 0.02. This is an explicit illustrative model, not measured IBM calibration. These plots contain no real QPU result. The hardware workflow remains optional and separate.

## What each image means

1. **Depth comparison:** independently evaluated final expected cut divided by each graph's exact optimum. Each method/mode/depth point includes all 15 graph/start trials. Shading is sample SD of the five per-graph means, not a confidence interval. Exact, greedy, and random references are included.
2. **Optimizer convergence:** at the preselected depth p=3, median best observed training ratio and the middle 50% of all 15 trials. These are recorded evaluation points shown as steps, without smoothing. A stopped run retains its last incumbent across larger available budgets; no extra calls are invented. Sampled training maxima can be optimistic, so Figure 1 uses independent final evaluations.
3. **Graph and best cut:** the first configured graph, seed 11. The exact optimum and one best observed noisy measurement are drawn using the same layout. A single good sampled bitstring is not the expected QAOA score. Vertex 0 is the rightmost bit.
4. **Circuit:** Qiskit's drawing of the actual parameterized eight-qubit p=1 circuit on graph 11. The displayed cost and mixer layer repeats in deeper trials. The figure uses one layer for readability; it does not represent all experiments as p=1.
5. **Measurement distribution:** fresh 16,384-shot measurements with and without noise at identical fixed parameters. Parameters come from graph 11, start 101, p=3, ideal COBYLA training, chosen by this rule rather than the best result. The left panel shows the 12 most frequent ideal bitstrings plus every remaining outcome in “Other”; the right panel includes all outcomes grouped by cut value. No reoptimization occurs between the conditions.
6. **Evaluation cost:** actual training calls versus depth, and final quality versus training work. Sampled work is also expressed in shots. Error bars describe trial SD. Calls differ in gate count as depth grows, so equal calls do not imply equal execution time. The dots do not estimate the minimum work needed to reach a target quality.

The histogram adds two evaluations and 32,768 shots outside the 810 optimization trials. The graph's sampled partition uses that same fresh noisy histogram. `docs/images/measurement-data.json` preserves parameters, counts, seeds, and measurement statistics. `figure-manifest.json` records the benchmark configuration, source hash, image hashes, and representative selection rule.

## Reproduce

Install the optional circuit drawing dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[figures]"
.\.venv\Scripts\python.exe -m qaoa_maxcut run --config configs/readme-benchmark.json --workers 4 --output results/readme-benchmark
.\.venv\Scripts\python.exe -m qaoa_maxcut figures --results results/readme-benchmark/results.json --output docs/images
```

Use a fresh output directory for a new benchmark. `--workers 1` runs serially. A numerical integration test compares serial and parallel records, excluding timings. Parallelism does not change seeds, budgets, objectives, or selection rules.

The included benchmark's raw record is compressed losslessly as `sample_results/readme-benchmark/results.json.gz` to keep the repository practical. Both the report and figure commands read JSON or gzip JSON directly:

```powershell
.\.venv\Scripts\python.exe -m qaoa_maxcut report sample_results/readme-benchmark/results.json.gz
.\.venv\Scripts\python.exe -m qaoa_maxcut figures --results sample_results/readme-benchmark/results.json.gz --output docs/images
```

Seeds and pinned dependencies enable repeatable numerical experiments on this environment. Execution times and file generation timestamps can change. Images should be regenerated together with their manifest rather than manually altering values or curves.
