from django.core.management.base import BaseCommand
from apps.tasks.domain.services import RecurrenceService


class Command(BaseCommand):
    help = 'Generuje instancje zadań powtarzalnych'

    def handle(self, *args, **options):
        service = RecurrenceService()
        generated = service.generate_daily_instances()

        self.stdout.write(self.style.SUCCESS(f'Wygenerowano {len(generated)} nowych zadań cyklicznych.'))
        for t in generated:
            self.stdout.write(f"- {t.title} ({t.due_date})")