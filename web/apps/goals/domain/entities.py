"""Goal domain entities."""

# apps/goals/domain/entities.py
from dataclasses import dataclass
from datetime import date


@dataclass
class GoalEntity:
    """Represents a goal in the domain layer."""

    id: int | None
    title: str
    motivation: str = ""
    deadline: date | None = None
    progress: float = 0.0  # 0.0 - 1.0 (wyliczane dynamicznie)
