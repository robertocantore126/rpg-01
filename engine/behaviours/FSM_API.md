Finite State Machine (FSM) API

Overview
- The FSM implementation exposes a StateMachine class (see engine.behaviours.fsm)
- States should provide lifecycle methods: on_enter, update, on_exit

Constructing an FSM
- Create a StateMachine(owner)
- Register states and transitions according to the StateMachine API (see code comments)

Using
- fsm.update(dt)  # advances the active state
- fsm.transition_to("state_name")

Notes
- Ensure your state update method accepts dt if it requires time-based behavior.

