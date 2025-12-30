# apps/projects/domain/entities.py
from dataclasses import dataclass
from typing import Optional, List
from datetime import date


@dataclass
class ProjectEntity:
    id: Optional[int]
    title: str
    description: str = ""
    status: str = "active"  # active, completed, on_hold

    # Hierarchia
    parent_project_id: Optional[int] = None
    goal_id: Optional[int] = None

    # Terminy
    deadline: Optional[date] = None

    def is_root(self) -> bool:
        return self.parent_project_id is None