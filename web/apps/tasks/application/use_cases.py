"""Task application use cases."""

# apps/tasks/application/use_cases.py
from dataclasses import dataclass

from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository


@dataclass
class CreateTaskInput:
    """Input data for creating a new task."""

    title: str
    user_id: int
    description: str = ""
    duration_min: int | None = None
    duration_max: int | None = None
    project_id: int | None = None
    energy_required: int = 2
    is_private: bool = False
    context_id: int | None = None
    area_id: int | None = None
    is_milestone: bool = False
    goal_id: int | None = None
    status: str = "inbox"
    priority: int = 3


class CreateTaskUseCase:
    """Use case for creating new tasks."""

    def __init__(self, repository: ITaskRepository):
        """Initialize use case with repository."""
        self.repository = repository

    def execute(self, input_dto: CreateTaskInput) -> TaskEntity:
        """Execute the task creation use case."""
        if not input_dto.title:
            raise ValueError("Task title cannot be empty")

        task = TaskEntity(
            id=None,
            title=input_dto.title,
            description=input_dto.description,
            status=TaskStatus(input_dto.status),
            duration_min=input_dto.duration_min,
            duration_max=input_dto.duration_max,
            project_id=input_dto.project_id,
            energy_required=input_dto.energy_required,
            is_private=input_dto.is_private,
            context_id=input_dto.context_id,
            area_id=input_dto.area_id,
            is_milestone=input_dto.is_milestone,
            goal_id=input_dto.goal_id,
            priority=input_dto.priority,
        )

        return self.repository.save(task, user_id=input_dto.user_id)
