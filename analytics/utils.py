import yaml
import os
from typing import List, Dict, Any

class GoalParser:
    def __init__(self, config_path='goals.yaml'):
        self.config_path = config_path
        self.goals = self._load_goals()

    def _load_goals(self) -> List[Dict[str, Any]]:
        """Load goals from YAML configuration file."""
        if not os.path.exists(self.config_path):
            print(f"Warning: Goals config not found at {self.config_path}")
            return []
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or []
        except Exception as e:
            print(f"Error loading goals config: {e}")
            return []

    def get_goals(self) -> List[Dict[str, Any]]:
        return self.goals

    def get_goal_by_code(self, code: str) -> Dict[str, Any]:
        for goal in self.goals:
            if goal.get('code') == code:
                return goal
        return None
