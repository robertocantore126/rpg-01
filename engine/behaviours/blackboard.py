# engine/behaviours/blackboard.py
__all__ = ["Blackboard"]

from typing import Any, Dict, Optional
import threading

class Blackboard:
    def __init__(self):
        self._global: Dict[str, Any] = {}
        self._per_agent: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()  # sicurezza se acceduto da più thread (es. pathfinding async)

    # ----------------------
    # Global values
    # ----------------------
    def set(self, key: str, value: Any):
        with self._lock:
            self._global[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            return self._global.get(key, default)

    def remove(self, key: str):
        with self._lock:
            if key in self._global:
                del self._global[key]

    # ----------------------
    # Per-agent values
    # ----------------------
    def set_for(self, agent_id: int, key: str, value: Any):
        with self._lock:
            if agent_id not in self._per_agent:
                self._per_agent[agent_id] = {}
            self._per_agent[agent_id][key] = value

    def get_for(self, agent_id: int, key: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            return self._per_agent.get(agent_id, {}).get(key, default)

    def remove_for(self, agent_id: int, key: str):
        with self._lock:
            if agent_id in self._per_agent and key in self._per_agent[agent_id]:
                del self._per_agent[agent_id][key]

    def clear_agent(self, agent_id: int):
        """Rimuove tutte le info relative a un agente"""
        with self._lock:
            self._per_agent.pop(agent_id, None)

    # ----------------------
    # Utility
    # ----------------------
    def debug_dump(self) -> Dict[str, Any]:
        """Ritorna una copia leggibile dello stato della blackboard"""
        with self._lock:
            return {
                "global": dict(self._global),
                "per_agent": {aid: dict(data) for aid, data in self._per_agent.items()}
            }
