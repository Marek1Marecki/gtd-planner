# apps/reports/tests/test_views.py
import uuid
from datetime import timedelta

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.reports.models import ActivityLog, ReviewSession
from apps.tasks.models import Task


@pytest.mark.integration
class ReportsViewsTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.client.login(username=self.user.username, password="testpass123")

    def test_stats_api_view_unauthenticated(self) -> None:
        """Test stats API view requires authentication"""
        self.client.logout()
        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_stats_api_view_basic(self) -> None:
        """Test stats API view returns basic structure"""
        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("weekly_stats", data)
        self.assertIn("area_distribution", data)
        self.assertIn("habit_completion", data)

    def test_stats_api_view_with_data(self) -> None:
        """Test stats API view with actual data"""
        # Create some tasks
        task1 = Task.objects.create(user=self.user, title="Task 1", status="done")
        task2 = Task.objects.create(user=self.user, title="Task 2", status="todo")

        # Create activity logs
        ActivityLog.objects.create(
            user=self.user,
            action_type=ActivityLog.ActionType.COMPLETED,
            content_object=task1,
            timestamp=timezone.now() - timedelta(days=1),
        )
        ActivityLog.objects.create(
            user=self.user,
            action_type=ActivityLog.ActionType.CREATED,
            content_object=task2,
            timestamp=timezone.now() - timedelta(days=2),
        )

        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        weekly_stats = data["weekly_stats"]

        self.assertEqual(weekly_stats["completed"], 1)
        self.assertEqual(weekly_stats["created"], 1)
        self.assertIn("breakdown", weekly_stats)

    def test_review_dashboard_view_unauthenticated(self) -> None:
        """Test review dashboard view requires authentication"""
        self.client.logout()
        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_review_dashboard_view_basic(self) -> None:
        """Test review dashboard view loads correctly"""
        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekly Review")

    def test_review_dashboard_view_with_data(self) -> None:
        """Test review dashboard view with existing data"""
        # Create some tasks and review sessions
        Task.objects.create(user=self.user, title="Task 1", status="done")
        Task.objects.create(user=self.user, title="Task 2", status="todo")

        ReviewSession.objects.create(user=self.user, reflection="Good week", next_week_priorities="Complete more tasks")

        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 200)

        # Should contain task statistics
        self.assertContains(response, "Task Statistics")
        # Should contain review form
        self.assertContains(response, "Review Form")

    def test_review_form_post_valid(self) -> None:
        """Test review form POST with valid data"""
        data = {"reflection": "Great progress this week", "next_week_priorities": "Finish project X"}

        response = self.client.post("/reports/review/", data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful POST

        # Check that review session was created
        session = ReviewSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.reflection, "Great progress this week")
            self.assertEqual(session.next_week_priorities, "Finish project X")

    def test_review_form_post_empty(self) -> None:
        """Test review form POST with empty data"""
        data = {"reflection": "", "next_week_priorities": ""}

        response = self.client.post("/reports/review/", data)
        self.assertEqual(response.status_code, 302)  # Should still redirect

        # Check that review session was created with empty values
        session = ReviewSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.reflection, "")
            self.assertEqual(session.next_week_priorities, "")

    def test_review_form_post_partial_data(self) -> None:
        """Test review form POST with partial data"""
        data = {
            "reflection": "Only reflection filled",
            # next_week_priorities missing
        }

        response = self.client.post("/reports/review/", data)
        self.assertEqual(response.status_code, 302)

        session = ReviewSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        if session:
            self.assertEqual(session.reflection, "Only reflection filled")
            self.assertEqual(session.next_week_priorities, "")

    def test_review_dashboard_context_data(self) -> None:
        """Test review dashboard context contains expected data"""
        # Create test data
        Task.objects.create(user=self.user, title="Task 1", status="done")
        Task.objects.create(user=self.user, title="Task 2", status="todo")
        Task.objects.create(user=self.user, title="Task 3", status="scheduled")

        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 200)

        # Check context variables
        self.assertIn("tasks", response.context)
        self.assertIn("review_form", response.context)
        self.assertIn("recent_reviews", response.context)

        tasks = response.context["tasks"]
        self.assertEqual(len(tasks), 3)

    def test_review_dashboard_recent_reviews(self) -> None:
        """Test review dashboard shows recent reviews"""
        # Create multiple review sessions
        session1 = ReviewSession.objects.create(user=self.user, reflection="Week 1", next_week_priorities="Priority 1")

        # Small delay to ensure different timestamps
        import time

        time.sleep(0.01)

        session2 = ReviewSession.objects.create(user=self.user, reflection="Week 2", next_week_priorities="Priority 2")

        response = self.client.get("/reports/review/")
        self.assertEqual(response.status_code, 200)

        recent_reviews = response.context["recent_reviews"]
        self.assertEqual(len(recent_reviews), 2)
        self.assertEqual(recent_reviews[0], session2)  # Most recent first
        self.assertEqual(recent_reviews[1], session1)

    def test_stats_api_habit_completion_data(self) -> None:
        """Test stats API includes habit completion data"""
        from apps.habits.models import Habit, HabitLog

        # Create a habit and log
        habit = Habit.objects.create(user=self.user, title="Exercise")
        HabitLog.objects.create(habit=habit, date=timezone.now().date())

        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("habit_completion", data)

        habit_data = data["habit_completion"]
        self.assertIn("total", habit_data)
        self.assertIn("completed", habit_data)
        self.assertIn("rate", habit_data)

    def test_stats_api_goal_progress_data(self) -> None:
        """Test stats API includes goal progress data"""
        from apps.goals.models import Goal

        # Create goals
        Goal.objects.create(user=self.user, title="Goal 1", progress=50)
        Goal.objects.create(user=self.user, title="Goal 2", progress=75)

        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("goal_progress", data)

        goal_data = data["goal_progress"]
        self.assertIn("total", goal_data)
        self.assertIn("average_progress", goal_data)
        self.assertEqual(goal_data["total"], 2)

    def test_stats_api_project_status_data(self) -> None:
        """Test stats API includes project status data"""
        from apps.projects.models import Project

        # Create projects
        Project.objects.create(user=self.user, title="Project 1", status="active")
        Project.objects.create(user=self.user, title="Project 2", status="completed")

        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("project_status", data)

        project_data = data["project_status"]
        self.assertIn("total", project_data)
        self.assertIn("active", project_data)
        self.assertIn("completed", project_data)
        self.assertEqual(project_data["total"], 2)

    def test_stats_api_note_count_data(self) -> None:
        """Test stats API includes note count data"""
        from apps.notes.models import Note

        # Create notes
        Note.objects.create(user=self.user, title="Note 1", content="Content 1")
        Note.objects.create(user=self.user, title="Note 2", content="Content 2")

        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("note_count", data)

        note_data = data["note_count"]
        self.assertIn("total", note_data)
        self.assertEqual(note_data["total"], 2)

    def test_stats_api_recurring_tasks_data(self) -> None:
        """Test stats API includes recurring tasks data"""
        from apps.tasks.models import RecurringPattern

        # Create recurring patterns
        RecurringPattern.objects.create(user=self.user, title="Daily Task")
        RecurringPattern.objects.create(user=self.user, title="Weekly Task")

        response = self.client.get("/reports/api/stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("recurring_tasks", data)

        recurring_data = data["recurring_tasks"]
        self.assertIn("total", recurring_data)
        self.assertEqual(recurring_data["total"], 2)
