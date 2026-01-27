# engine/behaviours/goap.py
from __future__ import annotations

__all__ = ["GoapPlanner"]

from typing import Any, Dict, List, Optional, Tuple, Callable
import heapq
from dataclasses import dataclass, field


@dataclass
class GoapAction:
    name: str
    preconditions: Dict[str, Any]
    effects: Dict[str, Any]
    cost: float = 1.0
    perform: Optional[Callable[[Any, Any], bool]] = None
    """
    perform(agent, blackboard) -> bool
    If perform is None the planner will apply effects to the blackboard automatically.
    """

    def is_applicable(self, state: Dict[str, Any]) -> bool:
        for k, v in self.preconditions.items():
            if state.get(k) != v:
                return False
        return True

    def apply(self, state: Dict[str, Any]) -> Dict[str, Any]:
        new = dict(state)
        for k, v in self.effects.items():
            new[k] = v
        return new

    def execute(self, agent: Any, blackboard: Any) -> bool:
        if self.perform:
            return bool(self.perform(agent, blackboard))
        # default: write effects into blackboard and return True
        for k, v in self.effects.items():
            blackboard.set(k, v)
        return True


class GoapPlanner:
    def __init__(self, agent: Any, blackboard: Any, actions: Optional[List[GoapAction]] = None):
        self.agent = agent
        self.blackboard = blackboard
        self.actions: List[GoapAction] = actions or []

        # plan execution state
        self._plan: List[GoapAction] = []
        self._current_index = 0

    def add_action(self, action: GoapAction):
        self.actions.append(action)

    def clear_actions(self):
        self.actions.clear()

    def _state_to_key(self, state: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
        # deterministic, hashable
        return tuple(sorted(state.items()))

    def _heuristic(self, state: Dict[str, Any], goal: Dict[str, Any]) -> int:
        # simple heuristic: number of mismatched key/value pairs
        mismatch = 0
        for k, v in goal.items():
            if state.get(k) != v:
                mismatch += 1
        return mismatch

    def plan(self, goal: Dict[str, Any], initial: Optional[Dict[str, Any]] = None) -> Optional[List[GoapAction]]:
        """
        A* search in abstract state-space where nodes are world states (dicts).
        Returns ordered list of actions or None if no plan.
        """
        start_state = initial if initial is not None else self._read_world_state()
        start_key = self._state_to_key(start_state)
        goal_key = self._state_to_key(goal)

        open_heap = []
        heapq.heappush(open_heap, (0 + self._heuristic(start_state, goal), 0, start_state, []))
        closed = set()

        while open_heap:
            f, g, state, path = heapq.heappop(open_heap)
            state_key = self._state_to_key(state)
            if state_key in closed:
                continue
            closed.add(state_key)

            # goal test
            matched = True
            for k, v in goal.items():
                if state.get(k) != v:
                    matched = False
                    break
            if matched:
                return path  # list of GoapAction

            # expand: consider all applicable actions
            for action in self.actions:
                if action.is_applicable(state):
                    new_state = action.apply(state)
                    new_g = g + action.cost
                    new_f = new_g + self._heuristic(new_state, goal)
                    new_path = path + [action]
                    heapq.heappush(open_heap, (new_f, new_g, new_state, new_path))

        return None

    def _read_world_state(self) -> Dict[str, Any]:
        # By convention blackboard should expose a dict-like interface or provide get_all
        try:
            return dict(self.blackboard.debug_dump().get("global", {}))
        except Exception:
            # fallback: if blackboard has `get` only, we can't enumerate; return empty
            return {}

    def start_plan(self, goal: Dict[str, Any]) -> bool:
        plan = self.plan(goal)
        if not plan:
            self._plan = []
            self._current_index = 0
            return False
        self._plan = plan
        self._current_index = 0
        return True

    def update(self, dt: float) -> bool:
        """
        Call every frame. Executes the current action (atomic by default).
        Returns True if there is still work to do (plan running), False if done/no plan.
        """
        if not self._plan or self._current_index >= len(self._plan):
            return False
        action = self._plan[self._current_index]
        success = action.execute(self.agent, self.blackboard)
        # atomic: if succeeded advance
        if success:
            self._current_index += 1
        else:
            # failure: abort current plan
            self._plan = []
            self._current_index = 0
            return False
        return self._current_index < len(self._plan)

    def current_plan_actions(self) -> List[str]:
        return [a.name for a in self._plan]
