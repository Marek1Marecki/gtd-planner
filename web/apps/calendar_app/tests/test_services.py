# apps/calendar_app/tests/test_services.py
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from django.test import TestCase

from apps.calendar_app.domain.services import FreeWindow, SchedulerService
from apps.calendar_app.ports.calendar_provider import FixedEvent
from apps.tasks.domain.entities import TaskEntity, TaskStatus
from apps.tasks.models import Task


@pytest.mark.integration
class SchedulerServiceTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.service = SchedulerService()

    def test_calculate_free_windows_basic(self) -> None:
        """Test basic free window calculation"""
        today = date.today()
        work_start = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0, tzinfo=UTC)
        work_end = datetime.combine(today, datetime.min.time()).replace(hour=17, minute=0, tzinfo=UTC)

        # No fixed events
        fixed_events: Sequence[FixedEvent] = []

        windows = self.service.calculate_free_windows(today, fixed_events, work_start.time(), work_end.time())

        # Should have one window covering the entire work period
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].start, work_start)
        self.assertEqual(windows[0].end, work_end)

    def test_calculate_free_windows_with_events(self) -> None:
        """Test free window calculation with fixed events"""
        today = date.today()
        work_start = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0, tzinfo=UTC)
        work_end = datetime.combine(today, datetime.min.time()).replace(hour=17, minute=0, tzinfo=UTC)

        # Create a fixed event from 10:00 to 12:00
        mock_event = Mock()
        mock_event.start_time = datetime.combine(today, datetime.min.time()).replace(hour=10, minute=0, tzinfo=UTC)
        mock_event.end_time = datetime.combine(today, datetime.min.time()).replace(hour=12, minute=0, tzinfo=UTC)

        fixed_events = [mock_event]

        windows = self.service.calculate_free_windows(today, fixed_events, work_start.time(), work_end.time())

        # Should have two windows: 9:00-10:00 and 12:00-17:00
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0].start, work_start)
        self.assertEqual(windows[0].end, mock_event.start_time)
        self.assertEqual(windows[1].start, mock_event.end_time)
        self.assertEqual(windows[1].end, work_end)

    def test_calculate_free_windows_multiple_events(self) -> None:
        """Test free window calculation with multiple events"""
        today = date.today()
        work_start = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0, tzinfo=UTC)
        work_end = datetime.combine(today, datetime.min.time()).replace(hour=17, minute=0, tzinfo=UTC)

        # Create multiple fixed events
        event1 = Mock()
        event1.start_time = datetime.combine(today, datetime.min.time()).replace(hour=10, minute=0, tzinfo=UTC)
        event1.end_time = datetime.combine(today, datetime.min.time()).replace(hour=11, minute=0, tzinfo=UTC)

        event2 = Mock()
        event2.start_time = datetime.combine(today, datetime.min.time()).replace(hour=14, minute=0, tzinfo=UTC)
        event2.end_time = datetime.combine(today, datetime.min.time()).replace(hour=15, minute=0, tzinfo=UTC)

        fixed_events = [event1, event2]

        windows = self.service.calculate_free_windows(today, fixed_events, work_start.time(), work_end.time())

        # Should have three windows: 9:00-10:00, 11:00-14:00, 15:00-17:00
        self.assertEqual(len(windows), 3)
        self.assertEqual(windows[0].start, work_start)
        self.assertEqual(windows[0].end, event1.start_time)
        self.assertEqual(windows[1].start, event1.end_time)
        self.assertEqual(windows[1].end, event2.start_time)
        self.assertEqual(windows[2].start, event2.end_time)
        self.assertEqual(windows[2].end, work_end)

    def test_schedule_tasks_empty(self) -> None:
        """Test scheduling with no tasks"""
        now = datetime.now(UTC)

        # Create empty windows
        window = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=3), is_work=True)

        # Create a mock user profile
        user_profile = Mock()
        user_profile.energy_profile = {9: 3, 14: 1, 20: 2}

        schedule = self.service.schedule_tasks([], [window], now, user_profile)

        self.assertEqual(len(schedule), 0)

    def test_schedule_tasks_basic(self) -> None:
        """Test basic task scheduling"""
        now = datetime.now(UTC)

        # Create a task and task entity
        task = Task.objects.create(user=self.user, title="Test Task", duration_min=60, priority=3, status="todo")

        task_entity = TaskEntity(
            id=task.id,
            title=task.title,
            duration_min=task.duration_min,
            priority=task.priority,
            status=TaskStatus(task.status),
            user_id=task.user.id,
        )

        # Create a window
        window = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=3), is_work=True)

        # Create a mock user profile
        user_profile = Mock()
        user_profile.energy_profile = {9: 3, 14: 1, 20: 2}

        schedule = self.service.schedule_tasks([task_entity], [window], now, user_profile)

        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0].task, task_entity)
        self.assertEqual(schedule[0].start, window.start)
        self.assertEqual(schedule[0].end, window.start + timedelta(minutes=60))

    def test_schedule_tasks_priority_ordering(self) -> None:
        """Test tasks are scheduled by priority"""
        now = datetime.now(UTC)

        # Create tasks with different priorities
        low_priority_task = Task.objects.create(
            user=self.user,
            title="Low Priority",
            duration_min=60,
            priority=5,  # Lower priority number = higher priority
            status="todo",
        )

        high_priority_task = Task.objects.create(
            user=self.user, title="High Priority", duration_min=60, priority=1, status="todo"
        )

        # Create a window
        window = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=4), is_work=True)

        # Konwertuj Task na TaskEntity
        low_entity = TaskEntity(
            id=low_priority_task.id,
            title=low_priority_task.title,
            duration_min=low_priority_task.duration_min,
            priority=low_priority_task.priority,
            status=TaskStatus(low_priority_task.status),
            user_id=low_priority_task.user.id,
        )
        high_entity = TaskEntity(
            id=high_priority_task.id,
            title=high_priority_task.title,
            duration_min=high_priority_task.duration_min,
            priority=high_priority_task.priority,
            status=TaskStatus(high_priority_task.status),
            user_id=high_priority_task.user.id,
        )

        # Create a window
        window = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=4), is_work=True)

        # Create a mock user profile
        user_profile = Mock()
        user_profile.energy_profile = {9: 3, 14: 1, 20: 2}

        schedule = self.service.schedule_tasks([low_entity, high_entity], [window], now, user_profile)

        # High priority task should be scheduled first
        self.assertEqual(len(schedule), 2)
        self.assertEqual(schedule[0].task, high_entity)
        self.assertEqual(schedule[1].task, low_entity)

    def test_schedule_tasks_insufficient_time(self) -> None:
        """Test tasks that don't fit in available windows"""
        now = datetime.now(UTC)

        # Create a task longer than available window
        task = Task.objects.create(
            user=self.user,
            title="Long Task",
            duration_min=180,  # 3 hours
            priority=1,
            status="todo",
        )

        # Create a 2-hour window
        window = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=3), is_work=True)

        # Konwertuj task na TaskEntity
        task_entity = TaskEntity(
            id=task.id,
            title=task.title,
            duration_min=task.duration_min,
            priority=task.priority,
            status=TaskStatus(task.status),
            user_id=task.user.id,
        )

        # Create a mock user profile
        user_profile = Mock()
        user_profile.energy_profile = {9: 3, 14: 1, 20: 2}

        schedule = self.service.schedule_tasks([task_entity], [window], now, user_profile)

        # Task should not be scheduled
        self.assertEqual(len(schedule), 0)

    def test_schedule_tasks_multiple_windows(self) -> None:
        """Test scheduling across multiple windows"""
        now = datetime.now(UTC)

        # Create tasks
        task1 = Task.objects.create(user=self.user, title="Task 1", duration_min=60, priority=1, status="todo")

        task2 = Task.objects.create(user=self.user, title="Task 2", duration_min=60, priority=2, status="todo")

        # Create two windows
        window1 = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=2), is_work=True)

        window2 = FreeWindow(start=now + timedelta(hours=3), end=now + timedelta(hours=5), is_work=True)

        # Konwertuj task1 i task2 na TaskEntity
        entity1 = TaskEntity(
            id=task1.id,
            title=task1.title,
            duration_min=task1.duration_min,
            priority=task1.priority,
            status=TaskStatus(task1.status),
            user_id=task1.user.id,
        )
        entity2 = TaskEntity(
            id=task2.id,
            title=task2.title,
            duration_min=task2.duration_min,
            priority=task2.priority,
            status=TaskStatus(task2.status),
            user_id=task2.user.id,
        )

        # Create a mock user profile
        user_profile = Mock()
        user_profile.energy_profile = {9: 3, 14: 1, 20: 2}

        schedule = self.service.schedule_tasks([entity1, entity2], [window1, window2], now, user_profile)

        # Both tasks should be scheduled
        self.assertEqual(len(schedule), 2)
        self.assertEqual(schedule[0].task, entity1)
        self.assertEqual(schedule[1].task, entity2)

    def test_get_weekly_plan_basic(self) -> None:
        """Test basic weekly plan generation"""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        # Create a real user profile
        from apps.core.models import UserProfile

        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "work_start_hour": "09:00",
                "work_end_hour": "17:00",
                "personal_start_hour": "18:00",
                "personal_end_hour": "22:00",
            },
        )

        plan = self.service.get_weekly_plan(self.user, start_of_week, datetime.now(UTC))

        # Should return a list with 7 days
        self.assertIsInstance(plan, list)
        self.assertEqual(len(plan), 7)  # 7 days in a week

    def test_get_weekly_plan_with_tasks(self) -> None:
        """Test weekly plan with tasks"""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        # Create a real user profile
        from apps.core.models import UserProfile

        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "work_start_hour": "09:00",
                "work_end_hour": "17:00",
                "personal_start_hour": "18:00",
                "personal_end_hour": "22:00",
            },
        )

        # Create tasks for different days
        Task.objects.create(user=self.user, title="Monday Task", status="todo", due_date=start_of_week)
        Task.objects.create(
            user=self.user, title="Tuesday Task", status="todo", due_date=start_of_week + timedelta(days=1)
        )

        from unittest.mock import patch

        with patch("apps.calendar_app.domain.services.SchedulerService.calculate_free_windows") as mock_windows:
            with patch("apps.calendar_app.domain.services.SchedulerService.schedule_tasks") as mock_schedule:
                mock_windows.return_value = []
                mock_schedule.return_value = []

                self.service.get_weekly_plan(self.user, start_of_week, datetime.now(UTC))

                # Should have called scheduling for each day (2x per day: work + personal)
                self.assertEqual(mock_windows.call_count, 14)  # 7 days × 2 timelines
                self.assertEqual(mock_schedule.call_count, 14)  # 7 days × 2 timelines

    def test_schedule_tasks_with_energy_profile(self) -> None:
        """Test scheduling considers energy profile"""
        now = datetime.now(UTC)

        # Create user profile with energy profile
        from apps.core.models import UserProfile

        profile, created = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "energy_profile": {"9": 3, "14": 1, "20": 2},  # High energy at 9am, low at 2pm
            },
        )

        # Create tasks
        high_energy_task = Task.objects.create(
            user=self.user,
            title="High Energy Task",
            duration_min=60,
            priority=1,
            status="todo",
            energy_required=3,  # Requires high energy
        )

        low_energy_task = Task.objects.create(
            user=self.user,
            title="Low Energy Task",
            duration_min=60,
            priority=2,
            status="todo",
            energy_required=1,  # Requires low energy
        )

        # Create windows at different times
        morning_window = FreeWindow(
            start=now.replace(hour=9, minute=0), end=now.replace(hour=11, minute=0), is_work=True
        )
        afternoon_window = FreeWindow(
            start=now.replace(hour=14, minute=0), end=now.replace(hour=16, minute=0), is_work=True
        )

        # Konwertuj taski na TaskEntity
        high_energy_entity = TaskEntity(
            id=high_energy_task.id,
            title=high_energy_task.title,
            duration_min=high_energy_task.duration_min,
            priority=high_energy_task.priority,
            status=TaskStatus(high_energy_task.status),
            user_id=high_energy_task.user.id,
            energy_required=high_energy_task.energy_required,
        )
        low_energy_entity = TaskEntity(
            id=low_energy_task.id,
            title=low_energy_task.title,
            duration_min=low_energy_task.duration_min,
            priority=low_energy_task.priority,
            status=TaskStatus(low_energy_task.status),
            user_id=low_energy_task.user.id,
            energy_required=low_energy_task.energy_required,
        )

        schedule = self.service.schedule_tasks(
            [high_energy_entity, low_energy_entity], [morning_window, afternoon_window], now, user_profile=profile
        )

        # Should schedule tasks considering energy requirements
        self.assertEqual(len(schedule), 2)

    def test_schedule_tasks_with_deadlines(self) -> None:
        """Test scheduling respects task deadlines"""
        today = date.today()
        now = datetime.now(UTC)

        # Create tasks with different deadlines
        urgent_task = Task.objects.create(
            user=self.user,
            title="Urgent Task",
            duration_min=60,
            priority=3,
            status="todo",
            due_date=today,  # Due today
        )

        future_task = Task.objects.create(
            user=self.user,
            title="Future Task",
            duration_min=60,
            priority=1,
            status="todo",
            due_date=today + timedelta(days=7),  # Due next week
        )

        # Create windows
        window = FreeWindow(start=now + timedelta(hours=1), end=now + timedelta(hours=4), is_work=True)

        # Konwertuj urgent_task i future_task na TaskEntity
        urgent_entity = TaskEntity(
            id=urgent_task.id,
            title=urgent_task.title,
            duration_min=urgent_task.duration_min,
            priority=urgent_task.priority,
            status=TaskStatus(urgent_task.status),
            user_id=urgent_task.user.id,
            due_date=urgent_task.due_date,
        )
        future_entity = TaskEntity(
            id=future_task.id,
            title=future_task.title,
            duration_min=future_task.duration_min,
            priority=future_task.priority,
            status=TaskStatus(future_task.status),
            user_id=future_task.user.id,
            due_date=future_task.due_date,
        )

        # Create a mock user profile
        user_profile = Mock()
        user_profile.energy_profile = {9: 3, 14: 1, 20: 2}

        schedule = self.service.schedule_tasks([urgent_entity, future_entity], [window], now, user_profile)

        # Urgent task should be prioritized despite lower priority number
        self.assertEqual(len(schedule), 2)
        self.assertEqual(schedule[0].task, urgent_entity)

    def test_calculate_free_windows_edge_cases(self) -> None:
        """Test edge cases in free window calculation"""
        today = date.today()
        work_start = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0, tzinfo=UTC)
        work_end = datetime.combine(today, datetime.min.time()).replace(hour=17, minute=0, tzinfo=UTC)

        # Event exactly at work start
        event_at_start = Mock()
        event_at_start.start_time = work_start
        event_at_start.end_time = work_start + timedelta(hours=1)

        # Event exactly at work end
        event_at_end = Mock()
        event_at_end.start_time = work_end - timedelta(hours=1)
        event_at_end.end_time = work_end

        fixed_events = [event_at_start, event_at_end]

        windows = self.service.calculate_free_windows(today, fixed_events, work_start.time(), work_end.time())

        # Should have one window between the events
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].start, event_at_start.end_time)
        self.assertEqual(windows[0].end, event_at_end.start_time)
