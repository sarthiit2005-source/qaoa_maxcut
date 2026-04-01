# Saved experimental evidence

These are actual local simulation outputs from this implementation, generated on 10 October 2026. Each local result JSON includes its configuration, package versions, seeds, full graph, baseline scores, parameters, and evaluation history.

| Location | Purpose |
|---|---|
| `quick/` | 18-trial demonstration; repeated successfully via the directly runnable Python example |
| `study/` | 243-trial study on three eight-vertex, pairwise non-isomorphic 3-regular graphs |
| `hardware-training/` | One local ideal optimization on a four-vertex cycle |
| `hardware-plan.json` | Locally prepared two-circuit plan derived from the hardware-training run |
| `hardware-offline.json` | Runtime SamplerV2 execution on FakeManilaV2, explicitly not real hardware |

Quick and main-study results use the illustrative noise parameters in their configuration. The fake-backend workflow uses a separate device snapshot model, so its noise is not identical to the study's model.

The offline hardware-path example produced an expected-cut ratio of approximately 0.7051 for QAOA and 0.4907 for the uniform reference, with 1,024 shots per circuit. The plan's ideal QAOA ratio is 0.75. These observations demonstrate the workflow; they do not establish hardware performance or quantum advantage.

The raw files are authoritative. Reports can be regenerated with `python -m qaoa_maxcut report <path-to-results.json>`. Do not compare timing numbers as controlled benchmarks: other verification work was running on the same machine.
