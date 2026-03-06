# apps/tasks/tests/test_domain_services.py
"""Integration tests for domain services that require Django infrastructure."""

import uuid
from unittest.mock import Mock

import pytest
from django.test import TestCase

from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.domain.services.task_service import TaskService
from apps.tasks.models import Task


@pytest.mark.integration
class TaskServiceTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Mock repository to isolate domain logic
        self.mock_repository = Mock()
        self.service = TaskService(repository=self.mock_repository)

    def test_create_task_basic(self) -> None:
        """Test basic task creation through service"""
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": 3,
            "duration_min": 60,
        }

        # Configure mock to return proper TaskEntity
        expected_task = TaskEntity(
            id=1, title="New Task", description="Task description", priority=3, duration_min=60, user_id=self.user.id
        )
        self.mock_repository.create.return_value = expected_task

        task = self.service.create_task(self.user.id, task_data)

        self.assertIsInstance(task, TaskEntity)
        self.assertEqual(task.title, "New Task")
        self.assertEqual(task.description, "Task description")
        self.assertEqual(task.priority, 3)
        self.assertEqual(task.duration_min, 60)
        self.assertEqual(task.user_id, self.user.id)

    def test_create_task_with_defaults(self) -> None:
        """Test task creation with default values"""
        task_data = {
            "title": "Minimal Task",
        }

        expected_task = TaskEntity(
            id=1,
            title="Minimal Task",
            status=TaskStatus.INBOX,  # Default status
            priority=3,  # Default priority
            user_id=self.user.id,
        )
        self.mock_repository.create.return_value = expected_task

        task = self.service.create_task(self.user.id, task_data)

        self.assertEqual(task.title, "Minimal Task")
        self.assertEqual(task.status, "inbox")  # Default status
        self.assertEqual(task.priority, 3)  # Default priority

    def test_update_task_basic(self) -> None:
        """Test basic task update"""
        # Create initial task entity
        original_task = TaskEntity(id=1, title="Original Title", priority=3, user_id=self.user.id)

        # Configure mock repository
        self.mock_repository.get_by_id.return_value = original_task

        updated_task_entity = TaskEntity(id=1, title="Updated Title", priority=1, user_id=self.user.id)
        self.mock_repository.update.return_value = updated_task_entity

        update_data = {
            "title": "Updated Title",
            "priority": 1,
        }

        updated_task = self.service.update_task(1, self.user.id, update_data)

        self.assertEqual(updated_task.title, "Updated Title")
        self.assertEqual(updated_task.priority, 1)

    def test_update_task_not_found(self) -> None:
        """Test updating non-existent task"""
        update_data = {"title": "Updated"}

        # Configure mock to return None (task not found)
        self.mock_repository.get_by_id.return_value = None

        with self.assertRaises(ValueError):  # Should raise appropriate exception
            self.service.update_task(999, self.user.id, update_data)

    def test_update_task_wrong_user(self) -> None:
        """Test updating task belonging to another user"""
        other_user_id = 999
        task = TaskEntity(id=1, title="Other User Task", priority=3, user_id=other_user_id)

        # Configure mock repository
        self.mock_repository.get_by_id.return_value = task

        update_data = {"title": "Updated"}

        with self.assertRaises(ValueError):  # Should raise appropriate exception
            self.service.update_task(1, self.user.id, update_data)

    def test_complete_task(self) -> None:
        """Test completing a task"""
        # Create task entity
        task_entity = TaskEntity(id=1, title="To Complete", status=TaskStatus.TODO, user_id=self.user.id)

        # Configure mock repository
        self.mock_repository.get_by_id.return_value = task_entity

        completed_task_entity = TaskEntity(id=1, title="To Complete", status=TaskStatus.DONE, user_id=self.user.id)
        self.mock_repository.update.return_value = completed_task_entity

        completed_task = self.service.complete_task(1)

        self.assertEqual(completed_task.status, "done")

    def test_delete_task(self) -> None:
        """Test task deletion"""
        # Create actual task in database for this test
        task = Task.objects.create(user=self.user, title="To Delete")

        # Configure mock repository
        task_entity = TaskEntity(id=task.id, title=task.title, user_id=self.user.id)
        self.mock_repository.get_by_id.return_value = task_entity
        self.mock_repository.delete.return_value = None

        task_id = task.id
        self.service.delete_task(task.id, self.user.id)

        # Verify that mock.delete was called
        self.mock_repository.delete.assert_called_once_with(task_id)

    def test_get_user_tasks(self) -> None:
        """Test getting user tasks"""
        # Create task entities for user
        task1_entity = TaskEntity(id=1, title="Task 1", user_id=self.user.id)
        task2_entity = TaskEntity(id=2, title="Task 2", user_id=self.user.id)

        # Configure mock repository
        self.mock_repository.get_by_user.return_value = [task1_entity, task2_entity]

        user_tasks = self.service.get_user_tasks(self.user.id)

        self.assertEqual(len(user_tasks), 2)
        self.assertIn(task1_entity, user_tasks)
        self.assertIn(task2_entity, user_tasks)

    def test_get_tasks_by_status(self) -> None:
        """Test getting tasks by status"""
        # Create task entities with different statuses
        todo_task_entity = TaskEntity(id=1, title="Todo", status=TaskStatus.TODO, user_id=self.user.id)

        # Configure mock repository
        self.mock_repository.filter_by_user_and_status.return_value = [todo_task_entity]

        todo_tasks = self.service.get_tasks_by_status(self.user.id, "todo")

        self.assertEqual(len(todo_tasks), 1)
        self.assertIn(todo_task_entity, todo_tasks)

    def test_simple_task_creation(self) -> None:
        """Test simple task creation"""
        task_entity = TaskEntity(id=1, title="Test Task", user_id=self.user.id, status=TaskStatus.TODO)
        self.assertEqual(task_entity.title, "Test Task")
        self.assertEqual(task_entity.status, "todo")

    def test_task_service_edge_cases(self) -> None:
        """Test edge cases in task service operations"""
        # Test with minimal task data
        task_data = {
            "title": "Minimal Task",
        }

        # Configure mock repository
        task_entity = TaskEntity(id=1, title="Minimal Task", user_id=self.user.id, status=TaskStatus.TODO)
        self.mock_repository.create.return_value = task_entity

        # Call service
        result = self.service.create_task(self.user.id, task_data)

        # Verify
        self.assertEqual(result.title, "Minimal Task")

    def test_task_service_update_operations(self) -> None:
        """Test various update operations"""
        update_data = {"title": "Updated Task"}

        # Configure mock repository
        task_entity = TaskEntity(id=1, title="Original", user_id=self.user.id, status=TaskStatus.TODO)
        updated_entity = TaskEntity(id=1, title="Updated Task", user_id=self.user.id, status=TaskStatus.TODO)

        self.mock_repository.get_by_id.return_value = task_entity
        self.mock_repository.update.return_value = updated_entity

        # Call service
        result = self.service.update_task(1, self.user.id, update_data)

        # Verify
        self.assertEqual(result.title, "Updated Task")

    def test_task_service_get_by_user_final(self) -> None:
        """Test getting tasks by user - final version"""
        # Configure mock repository
        task1 = TaskEntity(id=1, title="Task 1", user_id=self.user.id, status=TaskStatus.TODO)
        task2 = TaskEntity(id=2, title="Task 2", user_id=self.user.id, status=TaskStatus.DONE)

        self.mock_repository.get_by_user.return_value = [task1, task2]

        # Call service
        result = self.service.get_user_tasks(self.user.id)

        # Verify
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "Task 1")
        self.assertEqual(result[1].title, "Task 2")
        self.mock_repository.get_by_user.assert_called_once_with(self.user.id)

    def test_task_service_delete_by_id_final(self) -> None:
        """Test deleting task by ID - final version"""
        # Configure mock repository
        task_entity = TaskEntity(id=1, title="To Delete", user_id=self.user.id, status=TaskStatus.TODO)
        self.mock_repository.get_by_id.return_value = task_entity
        self.mock_repository.delete.return_value = None

        # Call service
        self.service.delete_task(1, self.user.id)

        # Verify
        self.mock_repository.get_by_id.assert_called_once_with(1)
        self.mock_repository.delete.assert_called_once_with(1)

    def test_task_service_complete_task_flow_final(self) -> None:
        """Test complete task flow - final version"""
        # Configure mock repository
        task_entity = TaskEntity(id=1, title="To Complete", user_id=self.user.id, status=TaskStatus.TODO)
        completed_entity = TaskEntity(id=1, title="To Complete", user_id=self.user.id, status=TaskStatus.DONE)

        self.mock_repository.get_by_id.return_value = task_entity
        self.mock_repository.update.return_value = completed_entity

        # Call service
        result = self.service.complete_task(1)

        # Verify
        self.assertEqual(result.status, "done")
        self.mock_repository.update.assert_called_once()
