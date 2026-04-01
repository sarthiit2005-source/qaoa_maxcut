"""Three SciPy methods sharing a hard objective-evaluation budget."""

from time import perf_counter

import numpy as np
from scipy.optimize import minimize

OPTIMIZERS = ("COBYLA", "Nelder-Mead", "Powell")


class EvaluationBudgetReached(Exception):
    """Normal stopping condition; never discard the best evaluated parameters."""


def optimize(evaluator, initial, method: str, budget: int) -> dict:
    if method not in OPTIMIZERS or budget < 1:
        raise ValueError("Unsupported optimizer or nonpositive evaluation budget.")
    initial = np.asarray(initial, dtype=float)
    history = []
    best_value, best_parameters = -np.inf, initial.copy()
    started = perf_counter()

    def objective(parameters):
        nonlocal best_value, best_parameters
        if len(history) >= budget:
            raise EvaluationBudgetReached
        measurement = evaluator.evaluate(parameters)
        value = measurement["mean_cut"]
        if not np.isfinite(value):
            raise RuntimeError("Nonfinite objective returned by simulator.")
        if value > best_value:
            best_value, best_parameters = value, np.array(parameters, copy=True)
        history.append({
            "evaluation": len(history) + 1, "mean_cut": value,
            "best_so_far_cut": float(best_value),
            "parameters": np.asarray(parameters).tolist(),
            "shots": measurement["shots"], "simulator_seed": measurement["simulator_seed"],
        })
        return -value

    # Library stopping tolerances may finish before the common cap. Record actual work.
    options = {"maxiter": max(1000, budget * 10)}
    if method == "COBYLA":
        options = {"maxiter": max(budget + 1, len(initial) + 2), "rhobeg": 0.5, "tol": 1e-4}
    else:
        options["maxfev"] = budget + 1
    try:
        result = minimize(objective, initial, method=method, options=options)
        status = "converged" if result.success else "optimizer_stopped"
        message = str(result.message)
        success = bool(result.success)
    except EvaluationBudgetReached:
        status, message, success = "budget_exhausted", "Reached objective-evaluation cap.", False
    return {
        "optimizer": method, "parameters": best_parameters.tolist(),
        "initial_parameters": initial.tolist(), "training_best_cut": float(best_value),
        "objective_evaluations": len(history), "training_shots": sum(h["shots"] for h in history),
        "budget": budget, "status": status, "optimizer_success": success, "message": message,
        "optimization_seconds": perf_counter() - started, "history": history,
    }
