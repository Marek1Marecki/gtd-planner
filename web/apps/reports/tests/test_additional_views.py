# apps/reports/tests/test_additional_views.py
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.integration
class ReportsAdditionalViewsTest(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.client.login(username=self.user.username, password="testpass123")

    def test_weekly_review_view_basic_context(self) -> None:
        """Test weekly review view has basic context"""
        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 200)

        # Check basic context keys
        self.assertIn("review_form", response.context)
        self.assertIn("total_tasks", response.context)
        self.assertIn("completed_tasks", response.context)
        self.assertIn("todo_tasks", response.context)
        self.assertIn("scheduled_tasks", response.context)

    def test_weekly_review_view_with_project_data(self) -> None:
        """Test weekly review view with project data"""
        # Create project and tasks
        project = Project.objects.create(user=self.user, title="Test Project")
        Task.objects.create(user=self.user, title="Task 1", project=project, status="todo")
        Task.objects.create(user=self.user, title="Task 2", project=project, status="done")

        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 200)

        # Should have task counts
        self.assertGreater(response.context["total_tasks"], 0)
        self.assertGreater(response.context["todo_tasks"], 0)
        self.assertGreater(response.context["completed_tasks"], 0)
