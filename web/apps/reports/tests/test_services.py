# apps/reports/tests/test_services.py
import uuid
from datetime import timedelta

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.reports.domain.services import ReportService
from apps.reports.models import ActivityLog
from apps.tasks.models import Task


@pytest.mark.integration
class ReportServiceTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.service = ReportService()

    def test_get_weekly_stats_empty(self) -> None:
        """Test weekly stats with no activity"""
        stats = self.service.get_weekly_stats(self.user)

        expected = {
            "period": "Last 7 Days",
            "completed": 0,
            "created": 0,
            "velocity": 0.0,
            "breakdown": {},
        }

        self.assertEqual(stats, expected)

    def test_get_weekly_stats_with_activity(self) -> None:
        """Test weekly stats with recent activity"""
        now = timezone.now()

        # Create some tasks
        task1 = Task.objects.create(user=self.user, title="Task 1", status="done")
        task2 = Task.objects.create(user=self.user, title="Task 2", status="todo")
        task3 = Task.objects.create(user=self.user, title="Task 3", status="scheduled")

        # Create activity logs
        ActivityLog.objects.create(
            user=self.user,
            action_type=ActivityLog.ActionType.CREATED,
            content_object=task1,
            timestamp=now - timedelta(days=2),
        )
        ActivityLog.objects.create(
            user=self.user,
            action_type=ActivityLog.ActionType.CREATED,
            content_object=task2,
            timestamp=now - timedelta(days=3),
        )
        ActivityLog.objects.create(
            user=self.user,
            action_type=ActivityLog.ActionType.COMPLETED,
            content_object=task1,
            timestamp=now - timedelta(days=1),
        )

        # Create an old activity (should not be counted)
        ActivityLog.objects.create(
            user=self.user,
            action_type=ActivityLog.ActionType.CREATED,
            content_object=task3,
            timestamp=now - timedelta(days=10),  # Too old
        )

        stats = self.service.get_weekly_stats(self.user)

        self.assertEqual(stats["period"], "Last 7 Days")
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["created"], 3)
        self.assertEqual(stats["velocity"], 1.0 / 7.0)
        self.assertEqual(stats["breakdown"], {"done": 1, "todo": 1, "scheduled": 1})

    def test_get_weekly_stats_velocity_calculation(self) -> None:
        """Test velocity calculation"""
        now = timezone.now()

        # Create tasks and complete them
        for i in range(7):
            task = Task.objects.create(user=self.user, title=f"Task {i}", status="done")
            ActivityLog.objects.create(
                user=self.user,
                action_type=ActivityLog.ActionType.COMPLETED,
                content_object=task,
                timestamp=now - timedelta(days=i),
            )

        stats = self.service.get_weekly_stats(self.user)

        self.assertEqual(stats["completed"], 7)
        self.assertEqual(stats["velocity"], 1.0)  # 7 tasks / 7 days

    def test_get_area_distribution_empty(self) -> None:
        """Test area distribution with no tasks"""
        distribution = self.service.get_area_distribution(self.user)

        self.assertEqual(distribution, {"labels": [], "data": [], "colors": []})

    def test_get_area_distribution_with_tasks(self) -> None:
        """Test area distribution with tasks in different areas"""
        from apps.areas.models import Area

        # Create areas
        area1 = Area.objects.create(user=self.user, name="Work", color="#FF0000")
        area2 = Area.objects.create(user=self.user, name="Personal", color="#00FF00")

        # Create tasks in different areas
        Task.objects.create(user=self.user, title="Work Task 1", area=area1, status="todo")
        Task.objects.create(user=self.user, title="Work Task 2", area=area1, status="done")
        Task.objects.create(user=self.user, title="Personal Task", area=area2, status="scheduled")
        Task.objects.create(user=self.user, title="No Area Task", status="todo")  # No area

        distribution = self.service.get_area_distribution(self.user)

        # Should return 2 areas (tasks without area are excluded)
        self.assertEqual(len(distribution["labels"]), 2)

        # Check area1 (Work) - should have 2 tasks
        work_index = distribution["labels"].index("Work")
        self.assertEqual(distribution["data"][work_index], 2)
        self.assertEqual(distribution["colors"][work_index], "#FF0000")

        # Check area2 (Personal) - should have 1 task
        personal_index = distribution["labels"].index("Personal")
        self.assertEqual(distribution["data"][personal_index], 1)
        self.assertEqual(distribution["colors"][personal_index], "#00FF00")

    def test_get_area_distribution_excludes_inactive_tasks(self) -> None:
        """Test area distribution excludes inactive tasks"""
        from apps.areas.models import Area

        area = Area.objects.create(user=self.user, name="Work", color="#FF0000")

        # Create tasks with different statuses
        Task.objects.create(user=self.user, title="Active 1", area=area, status="todo")
        Task.objects.create(user=self.user, title="Active 2", area=area, status="scheduled")
        Task.objects.create(user=self.user, title="Active 3", area=area, status="done")
        Task.objects.create(user=self.user, title="Inactive 1", area=area, status="inbox")
        Task.objects.create(user=self.user, title="Inactive 2", area=area, status="waiting")

        distribution = self.service.get_area_distribution(self.user)

        # Should only include active tasks (todo, scheduled, done)
        # The service returns a dict with labels, data, and colors
        self.assertEqual(distribution["labels"][0], "Work")
        self.assertEqual(distribution["data"][0], 3)

    def test_get_area_distribution_user_isolation(self) -> None:
        """Test area distribution is isolated per user"""
        from django.contrib.auth import get_user_model

        from apps.areas.models import Area

        User = get_user_model()
        user2 = User.objects.create_user(
            username=f"testuser2_{uuid.uuid4().hex[:8]}", email="test2@example.com", password="testpass123"
        )

        # Create areas for both users
        area1 = Area.objects.create(user=self.user, name="Work", color="#FF0000")
        area2 = Area.objects.create(user=user2, name="Work", color="#0000FF")

        # Create tasks for both users
        Task.objects.create(user=self.user, title="User1 Task", area=area1, status="todo")
        Task.objects.create(user=user2, title="User2 Task", area=area2, status="todo")

        # Check distribution for user1
        distribution1 = self.service.get_area_distribution(self.user)
        self.assertEqual(len(distribution1["labels"]), 1)
        self.assertEqual(distribution1["labels"][0], "Work")
        self.assertEqual(distribution1["data"][0], 1)

        # Check distribution for user2
        service2 = ReportService()
        distribution2 = service2.get_area_distribution(user2)
        self.assertEqual(len(distribution2["labels"]), 1)
        self.assertEqual(distribution2["labels"][0], "Work")
        self.assertEqual(distribution2["data"][0], 1)

    def test_get_weekly_stats_status_breakdown(self) -> None:
        """Test status breakdown in weekly stats"""
        # Create tasks with different statuses
        Task.objects.create(user=self.user, title="Todo Task", status="todo")
        Task.objects.create(user=self.user, title="Done Task", status="done")
        Task.objects.create(user=self.user, title="Scheduled Task", status="scheduled")
        Task.objects.create(user=self.user, title="Another Todo", status="todo")

        stats = self.service.get_weekly_stats(self.user)

        breakdown = stats["breakdown"]
        self.assertEqual(breakdown.get("todo", 0), 2)
