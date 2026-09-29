"""StateReducerService for deterministic merging of multi-agent execution outputs."""

from typing import Any


class StateReducerService:
    """Combines concurrent or sequential execution outputs into the workflow state."""

    def reduce(
        self,
        base_state: dict[str, Any],
        updates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Merges multiple state updates into base_state, concatenating lists without loss."""
        merged = dict(base_state)
        for update in updates:
            for key, value in update.items():
                if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = list(merged[key]) + list(value)
                else:
                    merged[key] = value
        return merged

    def reduce_namespaced(
        self,
        base_state: dict[str, Any],
        agent_updates: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Isolates agent outputs under a dedicated 'agent_outputs' dictionary namespace."""
        merged = dict(base_state)
        if "agent_outputs" not in merged or not isinstance(merged["agent_outputs"], dict):
            merged["agent_outputs"] = {}
        for agent_name, update in agent_updates.items():
            merged["agent_outputs"][agent_name] = update
        return merged
