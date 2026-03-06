# apps/projects/tests/test_views.py
import uuid
from datetime import date, timedelta

import pytest
from django.test import TestCase

from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.integration
class ProjectsViewsTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.client.login(username=self.user.username, password="testpass123")

    def test_project_list_view_unauthenticated(self) -> None:
        """Test project list view requires authentication"""
        self.client.logout()
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_project_list_view_empty(self) -> None:
        """Test project list view with no projects"""
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "projects")
        self.assertEqual(len(response.context["projects"]), 0)

    def test_project_list_view_with_projects(self) -> None:
        """Test project list view with projects"""
        # Create root projects
        project1 = Project.objects.create(user=self.user, title="Project 1")
        project2 = Project.objects.create(user=self.user, title="Project 2")

        # Create subproject (should not appear in root list)
        subproject = Project.objects.create(user=self.user, title="Subproject", parent_project=project1)

        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)

        projects = response.context["projects"]
        self.assertEqual(len(projects), 2)
        self.assertIn(project1, projects)
        self.assertIn(project2, projects)
        self.assertNotIn(subproject, projects)

    def test_project_list_view_prefetch_related(self) -> None:
        """Test project list view uses prefetch_related for optimization"""
        project = Project.objects.create(user=self.user, title="Project with subprojects")
        Project.objects.create(user=self.user, title="Subproject", parent_project=project)

        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)

        # Should have subprojects prefetched
        project = response.context["projects"][0]
        self.assertTrue(hasattr(project, "_prefetched_objects_cache"))

    def test_project_detail_view_unauthenticated(self) -> None:
        """Test project detail view requires authentication"""
        self.client.logout()
        project = Project.objects.create(user=self.user, title="Test Project")
        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_project_detail_view_not_found(self) -> None:
        """Test project detail view with non-existent project"""
        response = self.client.get("/projects/999/")
        self.assertEqual(response.status_code, 404)

    def test_project_detail_view_other_user(self) -> None:
        """Test project detail view with other user's project"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        other_user = User.objects.create_user(
            username=f"otheruser_{uuid.uuid4().hex[:8]}", email="other@example.com", password="testpass123"
        )

        other_project = Project.objects.create(user=other_user, title="Other Project")
        response = self.client.get(f"/projects/{other_project.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_project_detail_view_basic(self) -> None:
        """Test project detail view basic functionality"""
        project = Project.objects.create(user=self.user, title="Test Project")

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"], project)

    def test_project_detail_view_with_tasks(self) -> None:
        """Test project detail view with tasks"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Create tasks with different statuses and priorities
        task1 = Task.objects.create(user=self.user, title="Task 1", project=project, status="todo", priority=1)
        task2 = Task.objects.create(user=self.user, title="Task 2", project=project, status="done", priority=3)
        task3 = Task.objects.create(
            user=self.user, title="Task 3", project=project, status="scheduled", priority=2, is_critical_path=True
        )

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        tasks = response.context["tasks"]
        self.assertEqual(len(tasks), 3)

        # Should be ordered by is_critical_path first, then priority
        self.assertEqual(tasks[0], task3)  # Critical path first
        self.assertEqual(tasks[1], task1)  # Priority 1
        self.assertEqual(tasks[2], task2)  # Priority 3

    def test_project_detail_view_progress_calculation(self) -> None:
        """Test project detail view progress calculation"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Create tasks
        Task.objects.create(user=self.user, title="Done Task", project=project, status="done")
        Task.objects.create(user=self.user, title="Todo Task", project=project, status="todo")
        Task.objects.create(user=self.user, title="Scheduled Task", project=project, status="scheduled")

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Progress should be 33% (1 done out of 3 total)
        self.assertEqual(response.context["progress"], 33)

    def test_project_detail_view_no_tasks_progress(self) -> None:
        """Test project detail view progress with no tasks"""
        project = Project.objects.create(user=self.user, title="Empty Project")

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Progress should be 0 when no tasks
        self.assertEqual(response.context["progress"], 0)

    def test_project_detail_view_with_notes(self) -> None:
        """Test project detail view includes notes"""
        from apps.notes.models import Note

        project = Project.objects.create(user=self.user, title="Test Project")

        # Create notes
        note1 = Note.objects.create(user=self.user, title="Note 1", content="Content 1", project=project)
        note2 = Note.objects.create(user=self.user, title="Note 2", content="Content 2", project=project)

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        notes = response.context["notes"]
        self.assertEqual(len(notes), 2)
        # Should be ordered by updated_at descending
        self.assertEqual(notes[0], note2)
        self.assertEqual(notes[1], note1)

    def test_project_detail_view_prediction(self) -> None:
        """Test project detail view includes completion prediction"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Create active tasks
        Task.objects.create(user=self.user, title="Active Task 1", project=project, status="todo", duration_min=60)
        Task.objects.create(
            user=self.user, title="Active Task 2", project=project, status="scheduled", duration_min=120
        )

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should include projected completion date
        self.assertIn("projected_date", response.context)
        self.assertIsInstance(response.context["projected_date"], date)

    def test_project_detail_view_prediction_no_active_tasks(self) -> None:
        """Test project detail view prediction with no active tasks"""
        project = Project.objects.create(user=self.user, title="Completed Project")

        # Create only completed tasks
        Task.objects.create(user=self.user, title="Done Task", project=project, status="done")

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should still include projected date (should be today)
        self.assertIn("projected_date", response.context)

    def test_project_detail_view_active_tasks_filter(self) -> None:
        """Test project detail view filters active tasks for prediction"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Create tasks with different statuses
        Task.objects.create(user=self.user, title="Active Task", project=project, status="todo", duration_min=60)
        Task.objects.create(user=self.user, title="Blocked Task", project=project, status="blocked", duration_min=30)
        Task.objects.create(user=self.user, title="Done Task", project=project, status="done", duration_min=45)
        Task.objects.create(user=self.user, title="Waiting Task", project=project, status="waiting", duration_min=20)

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Prediction should only consider active tasks (todo, scheduled, blocked)
        # Total duration should be 60 + 30 = 90 minutes
        projected_date = response.context["projected_date"]
        self.assertIsInstance(projected_date, date)

    def test_project_detail_view_subprojects(self) -> None:
        """Test project detail view with subprojects"""
        parent_project = Project.objects.create(user=self.user, title="Parent Project")
        subproject = Project.objects.create(user=self.user, title="Subproject", parent_project=parent_project)

        # Create tasks for both projects
        Task.objects.create(user=self.user, title="Parent Task", project=parent_project, status="todo")
        Task.objects.create(user=self.user, title="Subproject Task", project=subproject, status="todo")

        response = self.client.get(f"/projects/{parent_project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Should only show tasks for this project, not subprojects
        tasks = response.context["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].project, parent_project)

    def test_project_detail_view_with_areas_and_tags(self) -> None:
        """Test project detail view with areas and tags"""
        from apps.areas.models import Area
        from apps.contexts.models import Tag

        area = Area.objects.create(user=self.user, name="Work Area", color="#FF0000")
        tag = Tag.objects.create(user=self.user, name="Important", color="#00FF00")

        project = Project.objects.create(user=self.user, title="Test Project", area=area)
        project.tags.add(tag)

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        # Project should have area and tags
        self.assertEqual(response.context["project"].area, area)
        self.assertIn(tag, response.context["project"].tags.all())

    def test_project_detail_view_with_deadline(self) -> None:
        """Test project detail view with deadline"""
        deadline = date.today() + timedelta(days=30)
        project = Project.objects.create(user=self.user, title="Test Project", deadline=deadline)

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["project"].deadline, deadline)

    def test_project_detail_view_milestone_tasks(self) -> None:
        """Test project detail view with milestone tasks"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Create milestone and regular tasks
        milestone_task = Task.objects.create(user=self.user, title="Milestone", project=project, is_milestone=True)
        regular_task = Task.objects.create(user=self.user, title="Regular Task", project=project, is_milestone=False)

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        tasks = response.context["tasks"]
        self.assertIn(milestone_task, tasks)
        self.assertIn(regular_task, tasks)

    def test_project_detail_view_with_no_tasks(self) -> None:
        """Test project detail view with no tasks"""
        project = Project.objects.create(user=self.user, title="Empty Project")

        response = self.client.get(f"/projects/{project.pk}/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["project"], project)
        self.assertEqual(list(response.context["tasks"]), [])
