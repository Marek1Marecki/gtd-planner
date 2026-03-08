# apps/projects/tests/test_prediction.py
import uuid
from datetime import date, timedelta

import pytest
from django.test import TestCase

from apps.projects.domain.prediction import ProjectPredictor
from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.integration
class ProjectPredictorTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.predictor = ProjectPredictor(daily_capacity_minutes=240, current_date=date(2024, 1, 15))  # 4 hours

    def test_predict_completion_date_no_tasks(self) -> None:
        """Test prediction with no tasks"""
        completion_date = self.predictor.predict_completion_date([])
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_zero_duration_tasks(self) -> None:
        """Test prediction with tasks that have zero duration"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task1 = Task.objects.create(user=self.user, title="Task 1", project=project, duration_min=0)
        task2 = Task.objects.create(user=self.user, title="Task 2", project=project, duration_min=0)

        completion_date = self.predictor.predict_completion_date([task1, task2])
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_single_task_same_day(self) -> None:
        """Test prediction with single task that fits in one day"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task = Task.objects.create(user=self.user, title="Task", project=project, duration_min=120)  # 2 hours

        completion_date = self.predictor.predict_completion_date([task])
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_single_task_multiple_days(self) -> None:
        """Test prediction with single task that spans multiple days"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task = Task.objects.create(user=self.user, title="Long Task", project=project, duration_min=600)  # 10 hours

        completion_date = self.predictor.predict_completion_date([task])

        # Should take 3 days (10 hours / 4 hours per day = 2.5 days, rounded up)
        expected_date = date(2024, 1, 15)
        days_needed = 0
        hours_remaining = 10

        while hours_remaining > 0:
            expected_date += timedelta(days=1)
            if expected_date.weekday() < 5:  # Weekday
                hours_remaining -= 4
                days_needed += 1

        self.assertEqual(completion_date, expected_date)

    def test_predict_completion_date_multiple_tasks(self) -> None:
        """Test prediction with multiple tasks"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task1 = Task.objects.create(user=self.user, title="Task 1", project=project, duration_min=120)  # 2 hours
        task2 = Task.objects.create(user=self.user, title="Task 2", project=project, duration_min=180)  # 3 hours
        task3 = Task.objects.create(user=self.user, title="Task 3", project=project, duration_min=60)  # 1 hour

        completion_date = self.predictor.predict_completion_date([task1, task2, task3])

        # Total: 6 hours = 2 days
        expected_date = date(2024, 1, 15)
        days_needed = 0
        hours_remaining = 6

        while hours_remaining > 0:
            expected_date += timedelta(days=1)
            if expected_date.weekday() < 5:  # Weekday
                hours_remaining -= 4
                days_needed += 1

        self.assertEqual(completion_date, expected_date)

    def test_predict_completion_date_with_weekends(self) -> None:
        """Test prediction correctly skips weekends"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Create task that requires 8 hours (2 weekdays)
        task = Task.objects.create(user=self.user, title="Long Task", project=project, duration_min=480)

        # Start on Friday
        friday_predictor = ProjectPredictor(daily_capacity_minutes=240, current_date=date(2024, 1, 5))  # Friday
        completion_date = friday_predictor.predict_completion_date([task])

        # Should complete on Tuesday (skip weekend)
        expected_tuesday = date(2024, 1, 9)
        self.assertEqual(completion_date, expected_tuesday)

    def test_predict_completion_date_duration_min_max_average(self) -> None:
        """Test prediction uses average of min/max duration"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task = Task.objects.create(user=self.user, title="Task", project=project, duration_min=60, duration_max=180)

        completion_date = self.predictor.predict_completion_date([task])

        # Should use average: (60 + 180) / 2 = 120 minutes = 2 hours
        # Should complete same day
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_duration_min_only(self) -> None:
        """Test prediction with only min duration"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task = Task.objects.create(
            user=self.user,
            title="Task",
            project=project,
            duration_min=90,
            # duration_max is None
        )

        completion_date = self.predictor.predict_completion_date([task])

        # Should use min duration as both min and max: (90 + 90) / 2 = 90 minutes
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_default_duration(self) -> None:
        """Test prediction uses default duration when none specified"""
        project = Project.objects.create(user=self.user, title="Test Project")

        task = Task.objects.create(
            user=self.user,
            title="Task",
            project=project,
            # No duration_min or duration_max
        )

        completion_date = self.predictor.predict_completion_date([task])

        # Should use default 30 minutes
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_custom_capacity(self) -> None:
        """Test prediction with custom daily capacity"""
        custom_predictor = ProjectPredictor(daily_capacity_minutes=120)  # 2 hours per day
        project = Project.objects.create(user=self.user, title="Test Project")

        task = Task.objects.create(user=self.user, title="Task", project=project, duration_min=240)  # 4 hours

        completion_date = custom_predictor.predict_completion_date([task])

        # Should take 2 days with 2-hour capacity
        expected_date = date.today()
        days_needed = 0
        hours_remaining = 4

        while hours_remaining > 0:
            expected_date += timedelta(days=1)
            if expected_date.weekday() < 5:  # Weekday
                hours_remaining -= 2
                days_needed += 1

        self.assertEqual(completion_date, expected_date)

    def test_predict_completion_date_edge_case_friday_start(self) -> None:
        """Test prediction edge case starting on Friday"""
        project = Project.objects.create(user=self.user, title="Test Project")

        # Task that requires 8 hours (2 full weekdays)
        task = Task.objects.create(user=self.user, title="Long Task", project=project, duration_min=480)

        # Mock today to be Friday
        friday_predictor = ProjectPredictor(daily_capacity_minutes=240, current_date=date(2024, 1, 12))  # Friday
        completion_date = friday_predictor.predict_completion_date([task])

        # Friday: 4 hours, Monday: 4 hours = Tuesday completion
        expected_tuesday = date(2024, 1, 16)
        self.assertEqual(completion_date, expected_tuesday)

    def test_predict_completion_date_large_project(self) -> None:
        """Test prediction with large project spanning multiple weeks"""
        project = Project.objects.create(user=self.user, title="Large Project")

        # Create tasks totaling 40 hours (10 weekdays)
        tasks = []
        for i in range(10):
            task = Task.objects.create(
                user=self.user,
                title=f"Task {i}",
                project=project,
                duration_min=240,  # 4 hours each
            )
            tasks.append(task)

        completion_date = self.predictor.predict_completion_date(tasks)

        # Should take 10 weekdays = 2 weeks
        expected_date = date(2024, 1, 15)
        workdays_needed = 10
        workdays_counted = 0

        while workdays_counted < workdays_needed:
            expected_date += timedelta(days=1)
            if expected_date.weekday() < 5:  # Weekday
                workdays_counted += 1

        self.assertEqual(completion_date, expected_date)

    def test_predict_completion_date_mixed_durations(self) -> None:
        """Test prediction with tasks having different duration specifications"""
        project = Project.objects.create(user=self.user, title="Mixed Project")

        # Task with both min and max
        task1 = Task.objects.create(
            user=self.user, title="Task 1", project=project, duration_min=60, duration_max=100
        )  # Average: 80 minutes

        # Task with only min
        task2 = Task.objects.create(
            user=self.user, title="Task 2", project=project, duration_min=120
        )  # Average: 120 minutes

        # Task with no duration (default 30)
        task3 = Task.objects.create(user=self.user, title="Task 3", project=project)  # Average: 30 minutes

        completion_date = self.predictor.predict_completion_date([task1, task2, task3])

        # Total: 80 + 120 + 30 = 230 minutes = ~4 hours
        # Should complete same day
        self.assertEqual(completion_date, date(2024, 1, 15))

    def test_predict_completion_date_very_small_capacity(self) -> None:
        """Test prediction with very small daily capacity"""
        tiny_predictor = ProjectPredictor(daily_capacity_minutes=30)  # 30 minutes per day
        project = Project.objects.create(user=self.user, title="Slow Project")

        task = Task.objects.create(user=self.user, title="Task", project=project, duration_min=150)  # 2.5 hours

        completion_date = tiny_predictor.predict_completion_date([task])

        # Should take 5 days (150 / 30 = 5)
        expected_date = date.today()
        days_needed = 0
        minutes_remaining = 150

        while minutes_remaining > 0:
            expected_date += timedelta(days=1)
            if expected_date.weekday() < 5:  # Weekday
                minutes_remaining -= 30
                days_needed += 1

        self.assertEqual(completion_date, expected_date)
