# apps/calendar_app/adapters/google_calendar.py
from typing import List
from datetime import datetime, time, timedelta
import pytz
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from django.conf import settings
from apps.calendar_app.ports.calendar_provider import ICalendarProvider, FixedEvent
from apps.core.models import GoogleCredentials


class GoogleCalendarAdapter(ICalendarProvider):

    def _fetch_from_google(self, service, t_min: str, t_max: str) -> List[FixedEvent]:
        """Metoda pomocnicza do pobierania i parsowania zdarzeń z API."""
        try:
            events_result = service.events().list(
                calendarId='primary',
                timeMin=t_min,
                timeMax=t_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            fixed_events = []

            for event in events:
                # Ignoruj wydarzenia całodniowe
                if 'dateTime' not in event.get('start', {}):
                    continue

                start_str = event['start'].get('dateTime')
                end_str = event['end'].get('dateTime')

                try:
                    start_dt = datetime.fromisoformat(start_str)
                    end_dt = datetime.fromisoformat(end_str)
                except ValueError:
                    continue

                fixed_events.append(FixedEvent(
                    title=event.get('summary', 'Bez tytułu'),
                    start_time=start_dt,
                    end_time=end_dt,
                    is_work=True
                ))

            return fixed_events

        except Exception as e:
            print(f"GCal API Error: {e}")
            return []

    def _get_service(self, user_id: int):
        """Buduje klienta API dla danego usera."""
        try:
            creds_db = GoogleCredentials.objects.get(user_id=user_id)
        except GoogleCredentials.DoesNotExist:
            return None

        creds = Credentials(
            token=creds_db.token,
            refresh_token=creds_db.refresh_token,
            token_uri=creds_db.token_uri,
            client_id=creds_db.client_id,
            client_secret=creds_db.client_secret,
            scopes=creds_db.scopes.split()
        )

        try:
            return build('calendar', 'v3', credentials=creds)
        except RefreshError:
            print("Token wygasł.")
            return None
        except Exception as e:
            print(f"Błąd budowania serwisu: {e}")
            return None

    def get_events(self, user_id: int, day: datetime.date) -> List[FixedEvent]:
        """Pobiera wydarzenia na jeden dzień."""
        service = self._get_service(user_id)
        if not service: return []

        # Zakres czasu (cały dzień w UTC)
        # Google wymaga 'Z' na końcu
        day_start = datetime.combine(day, time.min).isoformat() + 'Z'
        day_end = datetime.combine(day, time.max).isoformat() + 'Z'

        return self._fetch_from_google(service, day_start, day_end)

    def get_events_range(self, user_id: int, start_date: datetime.date, end_date: datetime.date) -> List[FixedEvent]:
        """Pobiera wydarzenia z zakresu dat."""
        service = self._get_service(user_id)
        if not service: return []

        t_min = datetime.combine(start_date, time.min).isoformat() + 'Z'
        t_max = datetime.combine(end_date, time.max).isoformat() + 'Z'

        return self._fetch_from_google(service, t_min, t_max)