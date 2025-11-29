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
            percent_complete=model.percent_complete
        )

    def get_by_id(self, task_id: int) -> Optional[TaskEntity]:
        try:
            task = TaskModel.objects.get(id=task_id)
            return self.to_entity(task)
        except TaskModel.DoesNotExist:
            return None

    def save(self, task: TaskEntity, user_id: int) -> TaskEntity:
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
            'percent_complete': task.percent_complete
        }

        if task.id:
            # Aktualizacja istniejącego zadania
            TaskModel.objects.filter(id=task.id).update(**data)
            obj = TaskModel.objects.get(id=task.id)
        else:
            # Tworzenie nowego zadania (wymaga user_id)
            obj = TaskModel.objects.create(user_id=user_id, **data)

        return self.to_entity(obj)

    def filter_by_status(self, status: TaskStatus) -> List[TaskEntity]:
        qs = TaskModel.objects.filter(status=status.value)
        return [self.to_entity(t) for t in qs]

    def get_active_tasks(self) -> List[TaskEntity]:
        # Active = Todo lub Scheduled
        qs = TaskModel.objects.filter(status__in=[TaskStatus.TODO.value, TaskStatus.SCHEDULED.value])
        return [self.to_entity(t) for t in qs]