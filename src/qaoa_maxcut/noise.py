"""An explicit illustrative noise model, not a calibration of an IBM device."""

from dataclasses import dataclass

from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error


@dataclass(frozen=True)
class NoiseConfig:
    single_qubit: float = 0.001
    two_qubit: float = 0.01
    readout: float = 0.02

    def __post_init__(self):
        if any(not 0 <= p <= 1 for p in (self.single_qubit, self.two_qubit, self.readout)):
            raise ValueError("Noise parameters must be between 0 and 1.")


def make_noise_model(config: NoiseConfig) -> NoiseModel:
    # Every circuit is compiled to these gates so noise actually attaches.
    model = NoiseModel(basis_gates=["h", "rx", "rz", "cx"])
    model.add_all_qubit_quantum_error(depolarizing_error(config.single_qubit, 1), ["h", "rx", "rz"])
    model.add_all_qubit_quantum_error(depolarizing_error(config.two_qubit, 2), ["cx"])
    p = config.readout
    model.add_all_qubit_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]))
    return model
