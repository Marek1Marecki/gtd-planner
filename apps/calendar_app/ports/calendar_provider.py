# apps/calendar_app/ports/calendar_provider.py
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FixedEvent:
    title: str
    start_time: datetime
    end_time: datetime
    is_work: bool = True # Czy to spotkanie służbowe?

class ICalendarProvider(ABC):
    @abstractmethod
    def get_events(self, user_id: int, day: datetime.date) -> List[FixedEvent]:
        """Pobiera sztywne spotkania na dany dzień."""
        pass