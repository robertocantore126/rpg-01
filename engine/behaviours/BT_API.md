Behaviour Tree (BT) API

Overview
- A BehaviourTree is composed of Nodes. Nodes can be composites (Sequence, Selector), decorators (Inverter, Succeeder) or leaves (Action, Condition).

Constructing a tree
- Use BehaviourTree.from_config(config_dict, providers=None) to build a tree from a JSON-like dict.
  Example config:
  {
    "type": "sequence",
    "children": [
      {"type": "condition", "fn": "bb.get:player_visible"},
      {"type": "action", "fn": "attack"}
    ]
  }
- Alternatively, build nodes manually with classes: Sequence([Condition(func), Action(func)])

Leaf functions resolution
- Spec strings are resolved by BehaviourTree._resolve_callable with rules:
  - "bb.get:KEY" -> lambda ag, bb: bb.get(KEY)
  - "bb.set:KEY=VALUE" -> sets value on blackboard and returns True
  - if providers dict passed, it is consulted for function names
  - fallback is to call agent.<fn_spec>(agent, blackboard) or agent.<fn_spec>()

Using
- tree = BehaviourTree.from_config(config)
- status = tree.update(dt, agent, blackboard)  # returns Status.SUCCESS/FAILURE/RUNNING

Notes
- When providing custom callable providers, pass a dict to from_config(providers={"myfn": callable}).


---
