# apps/calendar_app/tests/test_views.py
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase

from apps.tasks.models import Task


@pytest.mark.integration
class CalendarViewsTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.client.login(username=self.user.username, password="testpass123")

    def test_daily_view_unauthenticated(self) -> None:
        """Test daily view requires authentication"""
        self.client.logout()
        response = self.client.get("/calendar/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_daily_view_basic(self) -> None:
        """Test daily view loads correctly"""
        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            response = self.client.get("/calendar/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "timeline")

    def test_daily_view_with_overdue_tasks(self) -> None:
        """Test daily view handles overdue tasks correctly"""
        yesterday = date.today() - timedelta(days=1)

        # Create overdue task
        overdue_task = Task.objects.create(user=self.user, title="Overdue Task", status="todo", due_date=yesterday)

        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            response = self.client.get("/calendar/")
            self.assertEqual(response.status_code, 200)

            # Task should be marked as overdue
            overdue_task.refresh_from_db()
            self.assertEqual(overdue_task.status, "overdue")

    def test_daily_view_with_tasks(self) -> None:
        """Test daily view with active tasks"""
        today = date.today()

        # Create work and personal tasks
        Task.objects.create(user=self.user, title="Work Task", status="todo", is_private=False, due_date=today)

        Task.objects.create(user=self.user, title="Personal Task", status="scheduled", is_private=True, due_date=today)

        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
                mock_scheduler.return_value.calculate_free_windows.return_value = []
                mock_scheduler.return_value.schedule_tasks.return_value = []

                response = self.client.get("/calendar/")
                self.assertEqual(response.status_code, 200)

                # Should have timeline items context
                self.assertIn("timeline_items", response.context)
                self.assertIn("backlog_tasks", response.context)

    def test_daily_view_with_fixed_events(self) -> None:
        """Test daily view with fixed calendar events"""

        # Mock fixed events
        mock_event = Mock()
        mock_event.title = "Meeting"
        mock_event.start_time = datetime.now(timezone.utc)
        mock_event.end_time = mock_event.start_time + timedelta(hours=1)

        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = [mock_event]

            with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
                mock_scheduler.return_value.calculate_free_windows.return_value = []
                mock_scheduler.return_value.schedule_tasks.return_value = []

                response = self.client.get("/calendar/")
                self.assertEqual(response.status_code, 200)

                # Should include fixed event in timeline
                timeline_items = response.context["timeline_items"]
                fixed_events = [item for item in timeline_items if item["type"] == "fixed"]
                self.assertEqual(len(fixed_events), 1)
                self.assertEqual(fixed_events[0]["title"], "Meeting")

    def test_daily_view_htmx_request(self) -> None:
        """Test daily view with HTMX request header"""
        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            response = self.client.get("/calendar/", HTTP_HX_Request="true")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["base_template"], "base_htmx.html")

    def test_daily_view_normal_request(self) -> None:
        """Test daily view with normal request"""
        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            response = self.client.get("/calendar/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["base_template"], "base.html")

    def test_daily_view_user_profile_creation(self) -> None:
        """Test daily view creates user profile if missing"""
        # Delete existing profile
        from apps.core.models import UserProfile

        try:
            UserProfile.objects.get(user=self.user).delete()
        except UserProfile.DoesNotExist:
            pass

        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            response = self.client.get("/calendar/")
            self.assertEqual(response.status_code, 200)

            # Profile should be created
            self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_weekly_view_unauthenticated(self) -> None:
        """Test weekly view requires authentication"""
        self.client.logout()
        response = self.client.get("/calendar/week/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_weekly_view_default_date(self) -> None:
        """Test weekly view with default date (today)"""
        with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
            mock_scheduler.return_value.get_weekly_plan.return_value = {}

            response = self.client.get("/calendar/week/")
            self.assertEqual(response.status_code, 200)

            # Should use current week
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            self.assertEqual(response.context["start_date"], start_of_week)

    def test_weekly_view_custom_date(self) -> None:
        """Test weekly view with custom date parameters"""

        with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
            mock_scheduler.return_value.get_weekly_plan.return_value = {}

            response = self.client.get("/calendar/week/?year=2024&month=1&day=15")
            self.assertEqual(response.status_code, 200)

            # Should use specified week
            expected_start = date(2024, 1, 15) - timedelta(days=date(2024, 1, 15).weekday())
            self.assertEqual(response.context["start_date"], expected_start)

    def test_weekly_view_invalid_date(self) -> None:
        """Test weekly view with invalid date parameters"""
        with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
            mock_scheduler.return_value.get_weekly_plan.return_value = {}

            response = self.client.get("/calendar/week/?year=invalid&month=1&day=15")
            self.assertEqual(response.status_code, 200)

            # Should fall back to current week
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            self.assertEqual(response.context["start_date"], start_of_week)

    def test_weekly_view_navigation_links(self) -> None:
        """Test weekly view generates correct navigation links"""
        with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
            mock_scheduler.return_value.get_weekly_plan.return_value = {}

            response = self.client.get("/calendar/week/")
            self.assertEqual(response.status_code, 200)

            # Should have navigation parameters
            self.assertIn("prev_week_params", response.context)
            self.assertIn("next_week_params", response.context)

    def test_weekly_view_with_strategic_items(self) -> None:
        """Test weekly view includes goals, projects, and milestones"""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        # Create strategic items
        from apps.goals.models import Goal
        from apps.projects.models import Project

        Goal.objects.create(user=self.user, title="Weekly Goal", deadline=start_of_week + timedelta(days=2))

        Project.objects.create(user=self.user, title="Weekly Project", deadline=start_of_week + timedelta(days=3))

        Task.objects.create(
            user=self.user, title="Milestone Task", is_milestone=True, due_date=start_of_week + timedelta(days=1)
        )

        with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
            mock_scheduler.return_value.get_weekly_plan.return_value = {}

            response = self.client.get("/calendar/week/")
            self.assertEqual(response.status_code, 200)

            strategic_items = response.context["strategic_items"]
            self.assertEqual(len(strategic_items), 3)

            # Check types
            types = [item["type"] for item in strategic_items]
            self.assertIn("Cel", types)
            self.assertIn("Projekt", types)
            self.assertIn("Milestone", types)

    def test_weekly_view_htmx_request(self) -> None:
        """Test weekly view with HTMX request header"""
        with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
            mock_scheduler.return_value.get_weekly_plan.return_value = {}

            response = self.client.get("/calendar/week/", HTTP_HX_Request="true")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["base_template"], "base_htmx.html")

    def test_monthly_view_unauthenticated(self) -> None:
        """Test monthly view requires authentication"""
        self.client.logout()
        response = self.client.get("/calendar/month/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_monthly_view_basic(self) -> None:
        """Test monthly view loads correctly"""
        response = self.client.get("/calendar/month/")
        self.assertEqual(response.status_code, 200)

    def test_monthly_view_custom_date(self) -> None:
        """Test monthly view with custom date parameters"""
        response = self.client.get("/calendar/month/?year=2024&month=3")
        self.assertEqual(response.status_code, 200)

    def test_monthly_view_invalid_date(self) -> None:
        """Test monthly view with invalid date parameters"""
        response = self.client.get("/calendar/month/?year=invalid&month=3")
        self.assertEqual(response.status_code, 200)  # Should fall back to current month

    def test_daily_view_task_color_assignment(self) -> None:
        """Test daily view assigns correct colors to tasks"""

        # Create task with area
        from apps.areas.models import Area

        area = Area.objects.create(user=self.user, name="Work", color="#FF0000")

        task_with_area = Task.objects.create(
            user=self.user, title="Task with Area", status="todo", area=area, is_private=False
        )

        task_without_area = Task.objects.create(
            user=self.user, title="Task without Area", status="todo", is_private=True
        )

        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
                # Mock scheduled items
                mock_scheduled_item = Mock()
                mock_scheduled_item.task = task_with_area
                mock_scheduled_item.start = datetime.now(timezone.utc)
                mock_scheduled_item.end = datetime.now(timezone.utc) + timedelta(hours=1)

                mock_scheduled_item2 = Mock()
                mock_scheduled_item2.task = task_without_area
                mock_scheduled_item2.start = datetime.now(timezone.utc) + timedelta(hours=2)
                mock_scheduled_item2.end = datetime.now(timezone.utc) + timedelta(hours=3)

                mock_scheduler.return_value.calculate_free_windows.return_value = []
                mock_scheduler.return_value.schedule_tasks.return_value = [mock_scheduled_item, mock_scheduled_item2]

                response = self.client.get("/calendar/")
                self.assertEqual(response.status_code, 200)

                timeline_items = response.context["timeline_items"]
                self.assertIsNotNone(timeline_items)
                dynamic_items = [item for item in timeline_items if item["type"] == "dynamic"]

                # Task with area should have area color
                area_task_item = next((item for item in dynamic_items if item["task_id"] == task_with_area.id), None)
                self.assertIsNotNone(area_task_item)
                if area_task_item:
                    self.assertEqual(area_task_item["color"], "#FF0000")

                # Private task without area should have default green color
                private_task_item = next(
                    (item for item in dynamic_items if item["task_id"] == task_without_area.id), None
                )
                self.assertIsNotNone(private_task_item)
                if private_task_item:
                    self.assertEqual(private_task_item["color"], "#198754")

    def test_daily_view_backlog_tasks(self) -> None:
        """Test daily view correctly identifies backlog tasks"""

        # Create tasks that won't be scheduled
        task1 = Task.objects.create(user=self.user, title="Backlog 1", status="todo")
        Task.objects.create(user=self.user, title="Backlog 2", status="todo")

        with patch("apps.calendar_app.views.GoogleCalendarAdapter") as mock_adapter:
            mock_adapter.return_value.get_events.return_value = []

            with patch("apps.calendar_app.views.SchedulerService") as mock_scheduler:
                # Schedule only one task
                mock_scheduled_item = Mock()
                mock_scheduled_item.task = task1
                mock_scheduled_item.start = datetime.now(timezone.utc)
                mock_scheduled_item.end = datetime.now(timezone.utc) + timedelta(hours=1)

                mock_scheduler.return_value.calculate_free_windows.return_value = []
                mock_scheduler.return_value.schedule_tasks.return_value = [mock_scheduled_item]

                response = self.client.get("/calendar/")
                self.assertEqual(response.status_code, 200)

                backlog_tasks = response.context["backlog_tasks"]
                self.assertEqual(len(backlog_tasks), 1)
                self.assertEqual(backlog_tasks[0].title, "Backlog 2")
