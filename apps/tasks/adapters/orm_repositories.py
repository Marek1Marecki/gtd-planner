# apps/tasks/adapters/orm_repositories.py
from typing import List, Optional
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository
from apps.tasks.models import Task as TaskModel

class DjangoTaskRepository(ITaskRepository):
    def to_entity(self, model: TaskModel) -> TaskEntity:
        """Konwertuje Model Django -> Czystą Encję."""
        return TaskEntity(
            id=model.id,
            title=model.title,
            description=model.description,
            status=TaskStatus(model.status),
            duration_min=model.duration_min,
            duration_max=model.duration_max,
            due_date=model.due_date,
            is_fixed_time=model.is_fixed_time,
            priority=model.priority,
            energy_required=model.energy_required,
            complexity=model.complexity,
            is_private=model.is_private,
            percent_complete=model.percent_complete,
            is_critical_path=model.is_critical_path,
            project_id=model.project_id if model.project_id else None,
            context_id=model.context_id if model.context_id else None,
            area_id=model.area_id if model.area_id else None,
            # Pobieramy kolor z relacji (jeśli istnieje)
            # Dzięki select_related w zapytaniu, nie spowoduje to dodatkowego strzału do DB
            area_color=model.area.color if model.area else None
        )

    def get_by_id(self, task_id: int) -> Optional[TaskEntity]:
        try:
            task = TaskModel.objects.get(id=task_id)
            return self.to_entity(task)
        except TaskModel.DoesNotExist:
            return None

    def save(self, task: TaskEntity, user_id: int = None) -> TaskEntity:
        data = {
            'title': task.title,
            'description': task.description,
            'status': task.status.value,
            'duration_min': task.duration_min,
            'duration_max': task.duration_max,
            'due_date': task.due_date,
            'is_fixed_time': task.is_fixed_time,
            'priority': task.priority,
            'energy_required': task.energy_required,
            'complexity': task.complexity,
            'is_private': task.is_private,
            'percent_complete': task.percent_complete,
            'is_critical_path': task.is_critical_path,
            'project_id': task.project_id,
            'context_id': task.context_id,
            'area_id': task.area_id
        }

        if task.id:
            # Aktualizacja istniejącego
            TaskModel.objects.filter(id=task.id).update(**data)
            obj = TaskModel.objects.get(id=task.id)
        else:
            # Tworzenie nowego (wymaga user_id)
            if user_id is None:
                raise ValueError("user_id is required for creating a new task")
            obj = TaskModel.objects.create(user_id=user_id, **data)

        return self.to_entity(obj)

    def filter_by_status(self, status: TaskStatus) -> List[TaskEntity]:
        qs = TaskModel.objects.filter(status=status.value)
        return [self.to_entity(t) for t in qs]

    def get_active_tasks(self) -> List[TaskEntity]:
        # Active = To Do lub Scheduled
        # Dodajemy select_related('area'), żeby Django pobrało dane obszaru w jednym zapytaniu JOIN
        qs = TaskModel.objects.filter(
            status__in=[TaskStatus.TODO.value, TaskStatus.SCHEDULED.value]
        ).select_related('area')

        return [self.to_entity(t) for t in qs]

    def get_dependent_tasks(self, blocker_id: int) -> List[TaskEntity]:
        # Szukamy zadań, które mają w polu 'blocked_by' nasze zadanie (blocker_id)
        qs = TaskModel.objects.filter(blocked_by__id=blocker_id)
        return [self.to_entity(t) for t in qs]

    def has_active_blockers(self, task_id: int) -> bool:
        """
        Sprawdza, czy zadanie o podanym ID ma aktywne blokery.
        Aktywny bloker to zadanie, które NIE ma statusu DONE ani CANCELLED.
        """
        try:
            task = TaskModel.objects.get(id=task_id)

            # Pobierz liczbę blokerów, które nie są "zamknięte"
            active_blockers_count = task.blocked_by.exclude(
                status__in=[
                    TaskStatus.DONE.value,
                    'cancelled'
                ]
            ).count()

            return active_blockers_count > 0

        except TaskModel.DoesNotExist:
            # Jeśli zadanie nie istnieje, technicznie nie ma blokerów (albo rzucamy błąd)
            return False