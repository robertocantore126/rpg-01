GOAP Planner API

Overview
- The GOAP planner provides a Planner/GoapPlanner class to compute goal-achieving action sequences.
- Actions should expose preconditions and effects compatible with the planner implementation.

Using
- planner = GoapPlanner(agent, blackboard)
- plan = planner.plan(current_state, goal_state)
- planner.execute(plan)

Notes
- Refer to engine.behaviours.goap for implementation details and expected action interface.

