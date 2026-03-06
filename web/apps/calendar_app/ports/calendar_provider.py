"""Calendar provider ports and interfaces."""

# apps/calendar_app/ports/calendar_provider.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class FixedEvent:
    """Represents a fixed calendar event."""

    title: str
    start_time: datetime
    end_time: datetime
    is_work: bool = True  # Czy to spotkanie służbowe?


class ICalendarProvider(ABC):
    """Interface for calendar providers."""

    @abstractmethod
    def get_events(self, user_id: int, day: date) -> list[FixedEvent]:
        """Pobiera sztywne spotkania na dany dzień."""
        pass
