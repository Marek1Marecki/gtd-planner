# apps/projects/services/project_service.py
from apps.tasks.models import Task
from apps.projects.domain.services import CPMService, CPMNode


class ProjectService:
    def recalculate_cpm(self, project_id: int):
        # 1. Pobierz zadania projektu
        tasks = Task.objects.filter(project_id=project_id, status__in=['todo', 'scheduled', 'blocked', 'inbox'])
        if not tasks: return

        # 2. Konwersja na nody CPM
        nodes = []
        for t in tasks:
            # duration w minutach
            duration = t.duration_max or t.duration_min or 30
            # dependencies (pobieramy ID)
            deps = list(t.blocked_by.values_list('id', flat=True))

            nodes.append(CPMNode(task_id=t.id, duration=duration, dependencies=deps))

        # 3. Oblicz CPM
        cpm_service = CPMService()
        result_map = cpm_service.calculate_critical_path(nodes)

        # 4. Zapisz wyniki w bazie (Bulk Update dla wydajności)
        tasks_to_update = []
        for t in tasks:
            node = result_map.get(t.id)
            if node:
                is_crit = node.is_critical
                if t.is_critical_path != is_crit:
                    t.is_critical_path = is_crit
                    tasks_to_update.append(t)

        if tasks_to_update:
            Task.objects.bulk_update(tasks_to_update, ['is_critical_path'])
            print(f"CPM: Zaktualizowano {len(tasks_to_update)} zadań w projekcie {project_id}")