from typing import Any

from apps.tasks.domain.services import RecurrenceService
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generuje instancje zadań powtarzalnych"

    def handle(self, *args: Any, **options: Any) -> None:
        service = RecurrenceService()
        generated = service.generate_daily_instances()

        self.stdout.write(self.style.SUCCESS(f"Wygenerowano {len(generated)} nowych zadań cyklicznych."))
        for t in generated:
            self.stdout.write(f"- {t.title} ({t.due_date})")
