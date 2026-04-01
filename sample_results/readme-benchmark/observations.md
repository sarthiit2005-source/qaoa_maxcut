# Expanded benchmark observations

These observations describe the saved 810-trial local Aer experiment, not universal optimizer rankings or IBM hardware performance. Configuration and limitations are documented in `../../docs/figures.md`.

For COBYLA, means over all five graphs and three starts were:

| p | Exact ideal | Finite-shot ideal | Illustrative noisy |
|---:|---:|---:|---:|
| 1 | 0.7830 | 0.7631 | 0.7468 |
| 2 | 0.8499 | 0.8026 | 0.7434 |
| 3 | 0.8671 | 0.7931 | 0.7114 |
| 4 | 0.9026 | 0.8274 | 0.7222 |
| 5 | 0.9106 | 0.8098 | 0.6752 |
| 6 | 0.8464 | 0.8031 | 0.6533 |

Ideal mean quality increased through p=5 and then declined at p=6 under the fixed 240-evaluation budget. Deeper circuits have more parameters; these trials do not establish the globally optimal parameters at any depth. The noisy curves generally declined at larger depths. Gate errors accumulating in deeper circuits are a plausible contributor, but separately optimized modes also differ in their trained parameters, so that plot alone cannot isolate every cause.

The separate histogram controls the parameters: graph 11, start 101, p=3, ideal COBYLA, selected by a fixed rule. Fresh ideal and noisy measurements gave ratios 0.9653 and 0.8513 respectively, using 16,384 shots each. That controlled comparison illustrates execution noise for one circuit; its favorable ideal ratio is not the aggregate benchmark score.

Greedy search reached the exact optimum on all five small graphs. QAOA therefore did not beat this classical quality reference. Graph and starting-seed variation remains substantial, as shown by the figure bands and CSV statistics. This negative comparison is retained rather than hidden.

520 trials exhausted their evaluation budget and 290 returned optimizer convergence statuses. A convergence message is not a guarantee of global optimality. A larger budget, more starts, or another initialization strategy could change outcomes; those would be separate experiments.

See `report.md`, `summary.csv`, `runs.csv`, and `history.csv` for all methods and conditions. `results.json.gz` preserves every trial, parameter vector, training history, final measurement, and seed. `validation.json` records the completed audit.
