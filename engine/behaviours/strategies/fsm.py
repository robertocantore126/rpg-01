# engine/behaviours/fsm.py
from __future__ import annotations

__all__ = ["State", "StateMachine"]

from typing import Any, Callable, Dict, List, Optional


class State:
    def __init__(self, name: str,
                 on_enter: Optional[Callable[[Any], None]] = None,
                 on_update: Optional[Callable[[Any, float], None]] = None,
                 on_exit: Optional[Callable[[Any], None]] = None):
        self.name = name
        self.on_enter = on_enter
        self.on_update = on_update
        self.on_exit = on_exit

    def enter(self, agent):
        if callable(self.on_enter):
            self.on_enter(agent)

    def update(self, agent, dt: float):
        if callable(self.on_update):
            self.on_update(agent, dt)

    def exit(self, agent):
        if callable(self.on_exit):
            self.on_exit(agent)


class StateMachine:
    def __init__(self, agent: Any, blackboard: Any = None):
        self.agent = agent
        self.blackboard = blackboard
        self.states: Dict[str, State] = {}
        # transitions: from_state -> list of (condition_callable, to_state_name)
        self.transitions: Dict[str, List[tuple]] = {}
        self.current: Optional[State] = None
        self.prev: Optional[State] = None

    def add_state(self, state: State):
        self.states[state.name] = state

    def add_transition(self, from_state: str, to_state: str, condition: Callable[[Any, Any], bool]):
        self.transitions.setdefault(from_state, []).append((condition, to_state))

    def set_state(self, state_name: str):
        if self.current:
            self.current.exit(self.agent)
        self.prev = self.current
        self.current = self.states.get(state_name)
        if not self.current:
            raise KeyError(f"State {state_name} not found")
        self.current.enter(self.agent)

    def update(self, dt: float):
        if self.current:
            # evaluate transitions first
            for cond, to_state in self.transitions.get(self.current.name, []):
                try:
                    if cond(self.agent, self.blackboard):
                        self.set_state(to_state)
                        break
                except Exception:
                    # ignore failing conditions
                    continue
            # call current state's update
            if self.current:
                self.current.update(self.agent, dt)

    # -------------------------
    # Builder from config
    # -------------------------
    @staticmethod
    def _resolve_condition(spec: str) -> Callable[[Any, Any], bool]:
        """
        spec examples:
          - "can_see_player" -> getattr(agent, "can_see_player")
          - "bb.get:alert" -> lambda agent, bb: bool(bb.get('alert'))
        """
        if spec.startswith("bb.get:"):
            key = spec.split(":", 1)[1]
            return lambda ag, bb: bool(bb.get(key))
        # fallback to agent method name
        def cond(agent, bb):
            fn = getattr(agent, spec, None)
            if callable(fn):
                return bool(fn())
            return False
        return cond

    @staticmethod
    def _resolve_callback(spec: Optional[str]):
        if spec is None:
            return None
        if spec.startswith("bb.set:"):
            parts = spec.split(":", 1)[1].split("=", 1)
            k = parts[0]
            v = parts[1] if len(parts) > 1 else True
            # cast attempt
            try:
                if v.lower() in ("true", "false"): # type: ignore
                    vv = v.lower() == "true" # type: ignore
                else:
                    vv = int(v)
            except Exception:
                try:
                    vv = float(v)
                except Exception:
                    vv = v
            return lambda agent: agent.blackboard.set(k, vv) if hasattr(agent, "blackboard") else True
        # otherwise delegate to agent method
        def cb(agent):
            fn = getattr(agent, spec, None)
            if callable(fn):
                return fn()
            return None
        return cb

    @classmethod
    def from_config(cls, agent: Any, blackboard: Any, config: Dict) -> StateMachine:
        sm = cls(agent, blackboard)
        # create states
        for s in config.get("states", []):
            name = s["name"]
            on_enter = cls._resolve_callback(s.get("on_enter"))
            on_update = None
            if s.get("on_update"):
                # on_update is a method name on agent that accepts dt
                name_upd = s["on_update"]
                on_update = lambda a, dt, nm=name_upd: getattr(a, nm)(dt) if hasattr(a, nm) else None
            on_exit = cls._resolve_callback(s.get("on_exit"))
            sm.add_state(State(name, on_enter, on_update, on_exit)) # type: ignore

        # transitions
        for t in config.get("transitions", []):
            from_s = t["from"]
            to_s = t["to"]
            cond_spec = t["condition"]
            cond_fn = cls._resolve_condition(cond_spec)
            sm.add_transition(from_s, to_s, cond_fn)

        # initial
        init = config.get("initial")
        if init:
            sm.set_state(init)
        return sm
