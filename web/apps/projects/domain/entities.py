"""Project domain entities."""

# apps/projects/domain/entities.py
from dataclasses import dataclass
from datetime import date


@dataclass
class ProjectEntity:
    """Represents a project in the domain layer."""

    id: int | None
    title: str
    description: str = ""
    status: str = "active"  # active, completed, on_hold

    # Hierarchia
    parent_project_id: int | None = None
    goal_id: int | None = None

    # Terminy
    deadline: date | None = None

    def is_root(self) -> bool:
        """Check if project is a root project (no parent)."""
        return self.parent_project_id is None
