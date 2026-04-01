# Provenance and attribution

The starting reference was the user-supplied archive `Hybrid-Quantum-Classical-Algorithms-main (1).zip`, containing the notebook `Hybrid Quantum-Classical Algorithms.ipynb`, a README, and a presentation. The user identified the original project as a friend's work. Its QAOA Max-Cut optimizer-comparison idea informed this project.

This repository was written as a separate implementation. The original notebook, presentation, images, README wording, personal affiliations, and result plots are not included in this repository. The reference archive was extracted outside this repository for inspection and remains unmodified. The new implementation uses standard QAOA, Max-Cut, Qiskit, NetworkX, and SciPy methods; no claim of inventing those algorithms is made.

New work includes the explicitly verified cost/circuit conventions, classical baselines, controlled three-optimizer experiment, objective-call accounting, independent final evaluation, seeded shot/noise experiments, modular source code, tests, reports, and optional hardware workflow. `changes.md` records how these differ from the supplied reference.

The original archive had conflicting labels: its README/contribution guide referred to MIT while its LICENSE file contained Apache 2.0 text. This project does not resolve that discrepancy or strip notices from the reference files. No third-party source code from that archive is copied into this repository. If original material is later copied in, its applicable notices must be assessed and retained.

The user plans to obtain an institute license. No license file is issued for this new code at this stage. Dependencies retain their respective licenses. The user's application materials should accurately identify the project as an attributed reimplementation and experimental extension, with results described only to the extent they were actually run and understood.
