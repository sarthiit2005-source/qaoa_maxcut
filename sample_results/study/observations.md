# Observations from the included study

These statements describe this saved run only: three eight-vertex graphs, three starting seeds, and an 80-evaluation training cap. Each table entry averages nine trials.

| Mode | Optimizer | p=1 mean ratio | p=2 mean ratio | p=3 mean ratio |
|---|---|---:|---:|---:|
| ideal | COBYLA | 0.8156 | 0.8840 | 0.8980 |
| ideal | Nelder-Mead | 0.8156 | 0.8729 | 0.8497 |
| ideal | Powell | 0.8142 | 0.8629 | 0.8469 |
| shots | COBYLA | 0.7803 | 0.8070 | 0.8165 |
| shots | Nelder-Mead | 0.7821 | 0.7486 | 0.7674 |
| shots | Powell | 0.8115 | 0.8431 | 0.8265 |
| noisy | COBYLA | 0.7550 | 0.7400 | 0.7433 |
| noisy | Nelder-Mead | 0.7366 | 0.7096 | 0.7062 |
| noisy | Powell | 0.7634 | 0.7625 | 0.7436 |

The greedy heuristic found an exact optimum on each of these three small graphs. QAOA mean expected-cut ratios were below that reference. This is a negative quality comparison for QAOA on these particular instances; it is not a speed comparison.

Ideal optimization and finite-shot/noisy optimization behave differently. More layers do not consistently improve results under the limited budget. Some runs stop well before the cap, especially COBYLA; inspect actual evaluation counts rather than interpreting the cap as work always spent.

Each mode retrains its own parameters. Differences therefore combine objective noise, sampling, and optimizer behavior. They do not isolate hardware noise applied to one fixed state.

Use [report.md](report.md) and [summary.csv](summary.csv) for variance and evaluation counts. Training traces and final measurements are preserved in [results.json](results.json). No outcomes were smoothed or selected for inclusion after the run.

These graphs are too small and this sample too narrow to infer a universal optimizer ranking or quantum advantage.
