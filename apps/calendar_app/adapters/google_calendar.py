# apps/calendar_app/adapters/google_calendar.py
from google.auth.exceptions import RefreshError
from typing import List
from datetime import datetime, time, timedelta
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from apps.calendar_app.ports.calendar_provider import ICalendarProvider, FixedEvent
from apps.core.models import GoogleCredentials


class GoogleCalendarAdapter(ICalendarProvider):
    def get_events(self, user_id: int, day: datetime.date) -> List[FixedEvent]:
        # 1. Pobierz tokeny usera z bazy
        try:
            creds_db = GoogleCredentials.objects.get(user_id=user_id)
        except GoogleCredentials.DoesNotExist:
            print("Brak tokenu Google dla usera. Zwracam pustą listę.")
            return []

        # 2. Zbuduj obiekt Credentials (z biblioteki google)
        creds = Credentials(
            token=creds_db.token,
            refresh_token=creds_db.refresh_token,
            token_uri=creds_db.token_uri,
            client_id=creds_db.client_id,
            client_secret=creds_db.client_secret,
            scopes=creds_db.scopes.split()
        )

        try:
            # 3. Połącz się z API
            service = build('calendar', 'v3', credentials=creds)

            # 4. Ustal zakres czasu (cały dzień w UTC)
            # Uwaga: Google wymaga formatu ISO z 'Z' na końcu (dla UTC)
            day_start = datetime.combine(day, time.min).isoformat() + 'Z'
            day_end = datetime.combine(day, time.max).isoformat() + 'Z'

            print(f"Pobieram eventy z Google dla: {day}")

            # 5. Wykonaj zapytanie
            events_result = service.events().list(
                calendarId='primary',
                timeMin=day_start,
                timeMax=day_end,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            fixed_events = []

            # 6. Przetwórz wyniki na nasz format domenowy
            for event in events:
                # Ignoruj wydarzenia całodniowe (te bez 'dateTime') na potrzeby harmonogramu godzinowego
                if 'dateTime' not in event.get('start', {}):
                    continue

                start_str = event['start'].get('dateTime')
                end_str = event['end'].get('dateTime')

                # Parsowanie ISO stringa do datetime
                # (Python 3.7+ obsługuje fromisoformat, ale Google dodaje 'Z' lub offset, co bywa trudne.
                # Użyjmy dateutil lub prostego replace dla 'Z' jeśli biblioteka to zwraca)
                try:
                    start_dt = datetime.fromisoformat(start_str)
                    end_dt = datetime.fromisoformat(end_str)
                except ValueError:
                    # Fallback dla starszych pythonów lub dziwnych formatów
                    continue

                fixed_events.append(FixedEvent(
                    title=event.get('summary', 'Bez tytułu'),
                    start_time=start_dt,
                    end_time=end_dt,
                    is_work=True  # Domyślnie traktujemy jako "zajęte"
                ))

            return fixed_events

        except RefreshError:
            print("Błąd Google API: Token wygasł. Wymagane ponowne logowanie.")
            # Opcjonalnie: Możemy tu usunąć nieważny token z bazy
            # creds_db.delete()
            return []  # Zwracamy pustą listę, żeby aplikacja działała dalej (tylko bez GCal)

        except Exception as e:
            print(f"Błąd Google API: {e}")
            return []