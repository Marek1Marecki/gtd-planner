"""Calendar provider ports and interfaces."""

# apps/calendar_app/ports/calendar_provider.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


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

    @abstractmethod
    def get_events_range(self, user_id: int, start_date: date, end_date: date) -> list[FixedEvent]:
        """Pobiera sztywne spotkania w zakresie dat."""
        pass


class ITaskRepository(ABC):
    """Interface for task repository operations."""

    @abstractmethod
    def get_active_tasks(self) -> list[Any]:
        """Get all active tasks (TODO or SCHEDULED)."""
        pass


@dataclass
class UserProfileData:
    """DTO for user profile data instead of Django model."""

    work_start_hour: str
    work_end_hour: str
    personal_start_hour: str
    personal_end_hour: str
    energy_profile: dict[str, Any] | None = None
