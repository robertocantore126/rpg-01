# engine/behaviours/brain.py
__all__ = ["StrategyType", "Brain"]


from engine.behaviours.blackboard import Blackboard
from engine.behaviours.strategies.fsm import StateMachine
from engine.behaviours.strategies.behavior_tree import BehaviourTree, Node, LeafFactory
from engine.behaviours.strategies.goap import GoapPlanner


class StrategyType:
    FSM = "fsm"
    BT = "bt"
    GOAP = "goap"


class Brain:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.blackboard = Blackboard()
        self.enemies = {}  # enemy_id -> strategy instance

    def register_enemy(self, enemy, strategy_type, config=None):
        """Collega un nuovo nemico al cervello e crea la sua strategia"""
        if strategy_type == StrategyType.FSM:
            strategy = StateMachine(enemy)
        elif strategy_type == StrategyType.BT:
            # config may be:
            #  - a dict representing a full tree (use from_config)
            #  - a Node instance or callable representing the root
            if config is None:
                raise ValueError("BT strategy requires a config dict or a root Node/callable")
            if isinstance(config, dict):
                strategy = BehaviourTree.from_config(config, providers={})
            else:
                root = LeafFactory.make(config)
                strategy = BehaviourTree(root)
        elif strategy_type == StrategyType.GOAP:
            strategy = GoapPlanner(enemy, self.blackboard)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        self.enemies[enemy.id] = strategy

    def unregister_enemy(self, enemy):
        self.enemies.pop(enemy.id, None)

    def update(self, dt):
        """Aggiorna tutte le strategie collegate"""
        for strategy in self.enemies.values():
            strategy.update(dt)

    def get_blackboard(self):
        return self.blackboard

