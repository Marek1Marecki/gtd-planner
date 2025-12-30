# apps/goals/domain/entities.py
from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass
class GoalEntity:
    id: Optional[int]
    title: str
    motivation: str = ""
    deadline: Optional[date] = None
    progress: float = 0.0 # 0.0 - 1.0 (wyliczane dynamicznie)