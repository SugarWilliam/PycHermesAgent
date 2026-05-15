"""Bidirectional cross-scale coupling engine with feedback loops."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger("metamodel.coupling")


@dataclass
class CouplingLayer:
    """A single layer in the coupled system."""

    name: str
    adapter_id: str
    state_vars: List[str]
    initial_state: Dict[str, float]
    update_func: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, float]]] = None


class CouplingEngine:
    """
    Bidirectional coupling engine implementing true feedback loops.

    Unlike linear A→B→C pipelines, this engine supports:
    - Layer A outputs influence Layer B
    - Layer B outputs feed back to Layer A (next timestep)
    - Multiple iterations until convergence or max steps
    """

    def __init__(self, max_iterations: int = 10, convergence_tol: float = 1e-4):
        self.layers: List[CouplingLayer] = []
        self.max_iterations = max_iterations
        self.convergence_tol = convergence_tol
        self._history: List[Dict[str, Any]] = []

    def add_layer(self, layer: CouplingLayer) -> "CouplingEngine":
        self.layers.append(layer)
        return self

    def run(
        self,
        framework,
        data: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute bidirectional coupling.

        Each iteration:
        1. Forward pass: each layer calls its adapter
        2. Backward pass: outputs influence upstream layers
        3. Check convergence
        """
        states = {layer.name: dict(layer.initial_state) for layer in self.layers}
        results = {layer.name: {} for layer in self.layers}

        for iteration in range(self.max_iterations):
            # Forward pass
            for layer in self.layers:
                adapter_result = framework.call(layer.adapter_id, data={
                    **data,
                    **states[layer.name],
                    **{f"from_{other.name}": results[other.name] for other in self.layers if other != layer},
                }, extra_params=params)
                results[layer.name] = adapter_result

            # Backward / feedback pass
            for i, layer in enumerate(self.layers):
                if layer.update_func is not None:
                    # Update this layer's state based on downstream results
                    downstream = {self.layers[j].name: results[self.layers[j].name] for j in range(i + 1, len(self.layers))}
                    new_state = layer.update_func(states[layer.name], downstream)
                    states[layer.name] = new_state

            # Convergence check
            if iteration > 0:
                max_delta = 0.0
                for layer in self.layers:
                    for key in layer.state_vars:
                        old = self._history[-1][layer.name].get(key, 0)
                        new = states[layer.name].get(key, 0)
                        max_delta = max(max_delta, abs(new - old))
                if max_delta < self.convergence_tol:
                    logger.info("Coupling converged after %d iterations", iteration + 1)
                    break

            self._history.append({name: dict(state) for name, state in states.items()})

        return {
            "final_states": states,
            "adapter_results": results,
            "iterations": len(self._history),
            "converged": len(self._history) < self.max_iterations,
            "history": self._history,
        }
