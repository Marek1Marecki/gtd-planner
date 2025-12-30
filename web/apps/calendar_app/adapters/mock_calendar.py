# apps/calendar_app/adapters/mock_calendar.py
from typing import List
from datetime import datetime, timedelta, time
import pytz
from apps.calendar_app.ports.calendar_provider import ICalendarProvider, FixedEvent


class MockCalendarProvider(ICalendarProvider):
    def get_events(self, user_id: int, day: datetime.date) -> List[FixedEvent]:
        # Ustawiamy strefę czasową (ważne w Django!)
        tz = pytz.UTC

        # Tworzymy sztywne spotkanie: Lunch 12:00 - 13:00
        start = datetime.combine(day, time(12, 0)).replace(tzinfo=tz)
        end = start + timedelta(hours=1)

        return [
            FixedEvent(title="Lunch (Fixed)", start_time=start, end_time=end, is_work=True)
        ]