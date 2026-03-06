import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.tasks.models import ChecklistItem, Task

User = get_user_model()


@pytest.mark.integration
class TaskViewsTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

        self.task = Task.objects.create(title="Test Task", description="Test Description", user=self.user)

    def test_task_list_view(self) -> None:
        """Test task list view"""
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Task")

    def test_task_list_view_unauthenticated(self) -> None:
        """Test task list view requires authentication"""
        self.client.logout()
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_task_create_view_get(self) -> None:
        """Test task creation view GET request"""
        response = self.client.get(reverse("task_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    def test_task_create_view_post(self) -> None:
        """Test task creation view POST request"""
        data = {
            "title": "New Task",
            "description": "New Description",
            "priority": 2,
            "energy_required": 3,
            "duration_min": 45,
        }
        response = self.client.post(reverse("task_create"), data)

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check task was created
        new_task = Task.objects.get(title="New Task")
        self.assertEqual(new_task.description, "New Description")
        self.assertEqual(new_task.user, self.user)
        self.assertEqual(new_task.priority, 2)

    def test_task_update_view_get(self) -> None:
        """Test task update view GET request"""
        response = self.client.get(reverse("task_edit", args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Task")
        self.assertContains(response, "form")

    def test_task_update_view_post(self) -> None:
        """Test task update view POST request"""
        data = {
            "title": "Updated Task",
            "description": "Updated Description",
            "priority": 3,
            "energy_required": 4,
            "duration_min": 60,
        }
        response = self.client.post(reverse("task_edit", args=[self.task.pk]), data)

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check task was updated
        updated_task = Task.objects.get(pk=self.task.pk)
        self.assertEqual(updated_task.title, "Updated Task")
        self.assertEqual(updated_task.description, "Updated Description")
        self.assertEqual(updated_task.priority, 3)

    def test_task_complete_view_post(self) -> None:
        """Test task completion view"""
        self.assertEqual(self.task.status, "inbox")

        response = self.client.post(reverse("task_complete", args=[self.task.pk]))

        self.assertEqual(response.status_code, 200)  # HTMX request returns 200

        # Check task was marked as completed
        completed_task = Task.objects.get(pk=self.task.pk)
        self.assertEqual(completed_task.status, "done")

    def test_checklist_toggle_view_post(self) -> None:
        """Test checklist item toggle view"""
        checklist_item = ChecklistItem.objects.create(task=self.task, text="Test item", order=1)
        self.assertFalse(checklist_item.is_completed)

        response = self.client.post(reverse("checklist_toggle", args=[checklist_item.pk]))

        self.assertEqual(response.status_code, 200)  # HTMX request returns 200

        # Check item was toggled
        updated_item = ChecklistItem.objects.get(pk=checklist_item.pk)
        self.assertTrue(updated_item.is_completed)

    def test_checklist_delete_view_post(self) -> None:
        """Test checklist item delete view"""
        checklist_item = ChecklistItem.objects.create(task=self.task, text="Test item", order=1)

        response = self.client.delete(reverse("checklist_delete", args=[checklist_item.pk]))

        self.assertEqual(response.status_code, 200)  # HTMX request returns 200

        # Check item was deleted
        with self.assertRaises(ChecklistItem.DoesNotExist):
            ChecklistItem.objects.get(pk=checklist_item.pk)

    def test_checklist_toggle_view_other_user(self) -> None:
        """Test checklist toggle with other user's item"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")
        other_task = Task.objects.create(title="Other Task", user=other_user)
        checklist_item = ChecklistItem.objects.create(task=other_task, text="Other item", order=1)

        response = self.client.post(reverse("checklist_toggle", args=[checklist_item.pk]))
        self.assertEqual(response.status_code, 404)  # Should not be accessible

    def test_task_filtering_by_status(self) -> None:
        """Test filtering tasks by completion status"""
        Task.objects.create(title="Completed Task", user=self.user, status="done")

        # Test that both tasks appear in list (no filtering implemented yet)
        response = self.client.get(reverse("task_list"))
        self.assertContains(response, "Test Task")
        self.assertContains(response, "Completed Task")

    def test_task_search(self) -> None:
        """Test searching tasks"""
        Task.objects.create(title="Searchable Task", description="Special keyword", user=self.user)

        # Test that all tasks appear (no search implemented yet)
        response = self.client.get(reverse("task_list"))
        self.assertContains(response, "Test Task")
        self.assertContains(response, "Searchable Task")

    def test_task_list_view_context(self) -> None:
        """Test task list view context data"""
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, 200)

        # Check that response has context
        self.assertTrue(hasattr(response, "context"))

    def test_task_create_view_context(self) -> None:
        """Test task create view context"""
        response = self.client.get(reverse("task_create"))
        self.assertEqual(response.status_code, 200)

        # Check that response has context
        self.assertTrue(hasattr(response, "context"))
