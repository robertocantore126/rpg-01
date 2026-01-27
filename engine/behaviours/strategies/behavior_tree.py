# engine/behaviours/bt.py
from __future__ import annotations

__all__ = ["BehaviourTree"]

from enum import Enum, auto
from typing import Callable, Any, Dict, List, Optional


class Status(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


class Node:
    def tick(self, agent: Any, blackboard: Any) -> Status:
        raise NotImplementedError()


class LeafFactory:
    """Small helper to construct leaf nodes from a spec or a callable.

    This centralizes the logic so callers (like Brain) can provide either:
      - a prebuilt Node instance
      - a config dict describing a leaf (type/action/condition)
      - a callable to be wrapped in Action/Condition
    """
    @staticmethod
    def make(obj, providers: Optional[Dict[str, Callable]] = None) -> Node:
        # already a node
        if isinstance(obj, Node):
            return obj
        # dict spec -> use BehaviourTree._make_leaf
        if isinstance(obj, dict):
            return BehaviourTree._make_leaf(obj, providers)
        # callable -> treat as action
        if callable(obj):
            return Action(obj)
        raise ValueError("Unsupported leaf spec for BehaviorTree")


# -----------------------
# Composites
# -----------------------
class Sequence(Node):
    def __init__(self, children: List[Node]):
        self.children = children
        self._running_index = 0

    def tick(self, agent, blackboard):
        while self._running_index < len(self.children):
            status = self.children[self._running_index].tick(agent, blackboard)
            if status is Status.RUNNING:
                return Status.RUNNING
            if status is Status.FAILURE:
                self._running_index = 0
                return Status.FAILURE
            # SUCCESS -> continue
            self._running_index += 1
        self._running_index = 0
        return Status.SUCCESS


class Selector(Node):
    def __init__(self, children: List[Node]):
        self.children = children
        self._running_index = 0

    def tick(self, agent, blackboard):
        while self._running_index < len(self.children):
            status = self.children[self._running_index].tick(agent, blackboard)
            if status is Status.RUNNING:
                return Status.RUNNING
            if status is Status.SUCCESS:
                self._running_index = 0
                return Status.SUCCESS
            self._running_index += 1
        self._running_index = 0
        return Status.FAILURE


# -----------------------
# Decorators
# -----------------------
class Inverter(Node):
    def __init__(self, child: Node):
        self.child = child

    def tick(self, agent, blackboard):
        st = self.child.tick(agent, blackboard)
        if st is Status.SUCCESS:
            return Status.FAILURE
        if st is Status.FAILURE:
            return Status.SUCCESS
        return Status.RUNNING


class Succeeder(Node):
    def __init__(self, child: Node):
        self.child = child

    def tick(self, agent, blackboard):
        _ = self.child.tick(agent, blackboard)
        return Status.SUCCESS


# -----------------------
# Leaves
# -----------------------
class Condition(Node):
    def __init__(self, func: Callable[[Any, Any], bool]):
        self.func = func

    def tick(self, agent, blackboard):
        try:
            return Status.SUCCESS if bool(self.func(agent, blackboard)) else Status.FAILURE
        except Exception:
            return Status.FAILURE


class Action(Node):
    def __init__(self, func: Callable[[Any, Any], Any]):
        """
        func(agent, blackboard) -> can return:
          - Status (preferred)
          - True/False (mapped to SUCCESS/FAILURE)
          - None  (treated as SUCCESS)
        """
        self.func = func
        self._running = False

    def tick(self, agent, blackboard):
        res = self.func(agent, blackboard)
        if isinstance(res, Status):
            return res
        if res is True or res is None:
            return Status.SUCCESS
        if res is False:
            return Status.FAILURE
        # If func chooses to return a dict {"running": True}, handle gracefully
        if isinstance(res, dict) and res.get("running"):
            return Status.RUNNING
        return Status.FAILURE


# -----------------------
# BehaviorTree wrapper
# -----------------------
class BehaviourTree:
    def __init__(self, root: Node):
        self.root = root

    def update(self, dt: float, agent: Any, blackboard: Any) -> Status:
        # dt provided for actions that need time, but nodes receive agent/blackboard
        return self.root.tick(agent, blackboard)

    # Helper to build a tree from a simple dict config
    @staticmethod
    def _make_leaf(node_cfg: Dict, agent_providers: Optional[Dict[str, Callable]] = None):
        t = node_cfg.get("type")
        if t == "condition":
            fn_name = node_cfg["fn"]
            func = BehaviourTree._resolve_callable(fn_name, agent_providers)
            return Condition(func)
        if t == "action":
            fn_name = node_cfg["fn"]
            func = BehaviourTree._resolve_callable(fn_name, agent_providers)
            return Action(func)
        raise ValueError(f"Unknown leaf type {t}")

    @staticmethod
    def _resolve_callable(fn_spec: str, providers: Optional[Dict[str, Callable]] = None) -> Callable:
        """
        Resolution rules:
         - if starts with "bb.get:" -> lambda ag, bb: bb.get(key)
         - if starts with "bb.set:" -> lambda ag, bb: bb.set(key, value) and return True
         - otherwise try providers dict mapping or fallback to getattr(agent, fn_spec)
        """
        if fn_spec.startswith("bb.get:"):
            key = fn_spec.split(":", 1)[1]
            return lambda a, bb: bb.get(key)
        if fn_spec.startswith("bb.set:"):
            parts = fn_spec.split(":", 2)[1].split("=", 1)
            key = parts[0]
            val = parts[1] if len(parts) > 1 else True
            # try to interpret value as int/float/bool
            try:
                if val.lower() in ("true", "false"): # type: ignore
                    val_cast = val.lower() == "true" # type: ignore
                else:
                    val_cast = int(val)
            except Exception:
                try:
                    val_cast = float(val)
                except Exception:
                    val_cast = val
            return lambda a, bb: (bb.set(key, val_cast) or True)
        # provider override (useful to inject test functions)
        if providers and fn_spec in providers:
            return providers[fn_spec]
        # fallback to agent method resolver (callable)
        def caller(agent, bb):
            fn = getattr(agent, fn_spec, None)
            if callable(fn):
                try:
                    return fn(agent, bb)
                except TypeError:
                    # fall back to no-arg call if agent method doesn't accept bb
                    return fn()
            # if attribute exists and is not callable, return its truthiness
            if hasattr(agent, fn_spec):
                return bool(getattr(agent, fn_spec))
            return False
        return caller

    @staticmethod
    def from_config(config: Dict, providers: Optional[Dict[str, Callable]] = None) -> "BehaviourTree":
        """
        config example:
        {"type": "sequence", "children": [
            {"type": "condition", "fn": "can_see_player"},
            {"type": "action", "fn": "attack"}
         ]}
        Allowed composite types: sequence, selector
        """
        def build_node(node_cfg):
            t = node_cfg.get("type")
            if t in ("sequence", "selector"):
                children = [build_node(c) for c in node_cfg.get("children", [])]
                return Sequence(children) if t == "sequence" else Selector(children)
            if t in ("inverter", "succeeder"):
                child = build_node(node_cfg["child"])
                return Inverter(child) if t == "inverter" else Succeeder(child)
            # leaf
            return BehaviourTree._make_leaf(node_cfg, providers)

        root = build_node(config)
        return BehaviourTree(root)
