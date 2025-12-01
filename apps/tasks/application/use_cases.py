# apps/tasks/application/use_cases.py
from dataclasses import dataclass
from typing import Optional
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.ports.repositories import ITaskRepository

@dataclass
class CreateTaskInput:
    title: str
    user_id: int
    description: str = ""
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None
    project_id: Optional[int] = None
    energy_required: int = 2
    is_private: bool = False
    context_id: Optional[int] = None

class CreateTaskUseCase:
    def __init__(self, repository: ITaskRepository):
        self.repository = repository

    def execute(self, input_dto: CreateTaskInput) -> TaskEntity:
        if not input_dto.title:
            raise ValueError("Task title cannot be empty")

        task = TaskEntity(
            id=None,
            title=input_dto.title,
            description=input_dto.description,
            status=TaskStatus.INBOX,
            duration_min=input_dto.duration_min,
            duration_max=input_dto.duration_max,
            project_id=input_dto.project_id,
            energy_required=input_dto.energy_required,
            is_private=input_dto.is_private,
            context_id=input_dto.context_id
        )

        return self.repository.save(task, user_id=input_dto.user_id)