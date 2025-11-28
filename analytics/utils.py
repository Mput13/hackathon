import yaml
import os
import urllib.parse
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


def get_readable_page_name(url: str) -> str:
    """
    Convert a raw URL/path into a short human-friendly name for UI display.
    Examples:
      https://mai.ru/priem/ -> "Priem"
      /forms/apply_it -> "Forms Apply It"
    """
    if not url:
        return "Unknown page"

    parsed = urllib.parse.urlparse(url)
    path = parsed.path or url

    # Strip leading/trailing slashes and collapse empty paths
    clean = path.strip('/')
    if not clean:
        return "Homepage"

    # Use the last path segment as the primary label
    segment = clean.split('/')[-1]
    segment = urllib.parse.unquote(segment)

    # Drop file extensions like ".php" for readability
    if '.' in segment:
        segment = segment.split('.')[0]

    friendly = segment.replace('-', ' ').replace('_', ' ').strip()
    # Title-case words, but keep digits as-is
    return friendly.title() or path
