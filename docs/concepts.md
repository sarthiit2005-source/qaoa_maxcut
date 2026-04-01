# Reading map for this repository

This is a map for a later study conversation, not an expectation that you already know all these topics. Read only the optional hardware section after the local study makes sense.

## The one experiment

A graph has vertices and weighted edges. Assign each vertex to one of two groups. An edge contributes its weight when its endpoints are in different groups. Max-Cut asks for the largest possible sum.

For a bit assignment z:

`C(z) = sum_edges w_uv [z_u != z_v]`.

The diagonal observable is:

`C = sum_edges (w_uv / 2) (I - Z_u Z_v)`.

The expected score of independently assigning every vertex at random is half the total edge weight. Exact enumeration gives the optimum for our small instances. The greedy baseline repeatedly flips the vertex whose change gives the largest strict improvement, starting from several seeded assignments.

## Circuit convention

Start from `|+>^n`. Each of p layers applies `exp(-i gamma C)` followed by `exp(-i beta B)`, where `B = sum_u X_u`.

For an edge, dropping only an unobservable global phase yields `RZZ(-gamma * weight)`. The mixer uses `RX(2 * beta)` on each qubit. All gamma values precede all beta values in saved parameter arrays. Explicit parameter bindings avoid depending on alphabetical ordering.

The original notebook used a different gamma sign/scale convention. That can describe the same ansatz family after reparameterization; it was not, by itself, proof of a faulty circuit. This project makes one convention explicit and verifies it against matrix exponentials.

## Hybrid loop

The quantum circuit prepares a distribution over cuts. The evaluator obtains its mean cut value. A classical optimizer minimizes the negative mean because SciPy solves minimization problems. Each optimizer receives the same initial parameters and at most the configured number of evaluations. Parameters are unconstrained; the trigonometric ansatz accepts any real angles. The initial angles are drawn from `[0, pi)`.

COBYLA builds local linear approximations within a trust region. Nelder-Mead moves a simplex of parameter points. Powell uses a sequence of directional searches. All three use objective values without an explicitly supplied gradient. Their implementations come from SciPy; the project supplies the objective, budget boundary, seeds, and result accounting.

More layers mean more parameters and gates. With a finite training budget, a deeper run can be worse. The plotted measured results are not forced to improve.

## Noise and statistics

- Exact statevector expectation has no shot sampling error.
- Finite shots estimate the mean from measurement outcomes, giving sampling uncertainty.
- The noisy mode adds specified gate and readout errors before sampling.
- Training chooses the best observed parameters; final evaluation uses a different random stream so its reported score is not just the luckiest training observation.
- Approximation ratio is expected cut divided by the exact maximum cut. Cut fraction divides by total edge weight; it is separately recorded.
- SD across starting seeds describes training variability. SD across graph means describes instance variability. Shot standard error describes uncertainty of one measured mean. These are not interchangeable.

An exact expectation still costs classical computation. One circuit evaluation is not a universal unit of time: gate count, depth, shots, simulator mode, and hardware affect cost. The project records these quantities rather than claiming equal runtime from equal iteration limits.

## Suggested seven-day reading sequence

| Day | Read | Be able to explain |
|---|---|---|
| 1 | `problems.py`, `objective.py`, `baselines.py` | A cut, its integer representation, brute force, greedy search, and the optimum |
| 2 | `circuits.py` and quantum correctness tests | Cost observable, mixer, p, gamma/beta, gate signs, Qiskit bit ordering |
| 3 | `evaluation.py`, `noise.py` | Statevector versus samples, depolarization, readout error, shot standard error |
| 4 | `optimization.py` | The hybrid loop, three methods at a high level, local optima, evaluation budgets |
| 5 | `experiments.py`, configs, saved JSON | Paired initialization, graph seeds versus run seeds, independent final evaluation |
| 6 | `reporting.py`, actual results, `changes.md` | Approximation ratios, variance, limitations, why some changes were necessary |
| 7 | `hardware.py`, hardware guide, tests | Transpilation, physical versus logical qubits, shots, job IDs, honest hardware reporting |

This is a suggested reading order, not a guarantee of mastery in seven days. Focus on tracing one small run end to end and explaining your own experimental results.

## Prompt for another study chat

Open `changes.md`, this reading map, and the source files. Explain one module at a time, using a concrete small graph and the saved experiment records. Connect each equation to its implementation, distinguish implemented behavior from optional extensions, and ask me a few questions before advancing. Treat the source project as the acknowledged starting reference and explain which contributions belong to this reimplementation.
