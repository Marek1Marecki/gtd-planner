from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.habits.models import Habit, HabitLog

User = get_user_model()


@pytest.mark.integration
class HabitModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_habit_creation(self) -> None:
        """Test creating a basic habit"""
        habit = Habit.objects.create(title="Exercise", user=self.user)
        self.assertEqual(habit.title, "Exercise")
        self.assertEqual(habit.user, self.user)
        self.assertTrue(habit.is_active)
        self.assertEqual(habit.current_streak, 0)
        self.assertEqual(habit.longest_streak, 0)
        self.assertIsNone(habit.last_completed_date)
        self.assertIsNone(habit.area)

    def test_habit_str_method(self) -> None:
        """Test habit string representation"""
        habit = Habit.objects.create(title="Exercise", user=self.user)
        self.assertEqual(str(habit), "Exercise")

    def test_habit_with_area(self) -> None:
        """Test creating habit with area"""
        from apps.areas.models import Area

        area = Area.objects.create(name="Health", color="#ff0000", user=self.user)

        habit = Habit.objects.create(title="Exercise", user=self.user, area=area)
        self.assertEqual(habit.area, area)

    def test_habit_streak_tracking(self) -> None:
        """Test habit streak tracking"""
        habit = Habit.objects.create(title="Exercise", user=self.user)

        # Complete habit for 3 consecutive days
        today = date.today()
        for i in range(3):
            completion_date = today - timedelta(days=2 - i)
            HabitLog.objects.create(habit=habit, date=completion_date)

        # Update habit's streak (this would normally be done by a service)
        habit.current_streak = 3
        habit.longest_streak = 3
        habit.last_completed_date = today
        habit.save()

        updated_habit = Habit.objects.get(pk=habit.pk)
        self.assertEqual(updated_habit.current_streak, 3)
        self.assertEqual(updated_habit.longest_streak, 3)
        self.assertEqual(updated_habit.last_completed_date, today)

    def test_habit_deactivation(self) -> None:
        """Test deactivating a habit"""
        habit = Habit.objects.create(title="Exercise", user=self.user)

        habit.is_active = False
        habit.save()

        updated_habit = Habit.objects.get(pk=habit.pk)
        self.assertFalse(updated_habit.is_active)

    def test_habit_ordering_by_title(self) -> None:
        """Test habits are ordered by title"""
        habit_b = Habit.objects.create(title="B Habit", user=self.user)
        habit_a = Habit.objects.create(title="A Habit", user=self.user)
        habit_c = Habit.objects.create(title="C Habit", user=self.user)

        habits = Habit.objects.filter(user=self.user).order_by("title")
        self.assertEqual(habits[0], habit_a)
        self.assertEqual(habits[1], habit_b)
        self.assertEqual(habits[2], habit_c)

    def test_habit_user_filtering(self) -> None:
        """Test habits are filtered by user"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")

        user_habit = Habit.objects.create(title="User Habit", user=self.user)
        other_habit = Habit.objects.create(title="Other Habit", user=other_user)

        user_habits = Habit.objects.filter(user=self.user)
        self.assertEqual(user_habits.count(), 1)
        self.assertEqual(user_habits[0], user_habit)

        other_habits = Habit.objects.filter(user=other_user)
        self.assertEqual(other_habits.count(), 1)
        self.assertEqual(other_habits[0], other_habit)


@pytest.mark.integration
class HabitLogModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.habit = Habit.objects.create(title="Exercise", user=self.user)

    def test_habit_log_creation(self) -> None:
        """Test creating a habit log"""
        today = date.today()
        log = HabitLog.objects.create(habit=self.habit, date=today)
        self.assertEqual(log.habit, self.habit)
        self.assertEqual(log.date, today)

    def test_habit_log_str_method(self) -> None:
        """Test habit log string representation"""
        today = date.today()
        log = HabitLog.objects.create(habit=self.habit, date=today)
        expected_str = f"Exercise - {today}"
        self.assertEqual(str(log), expected_str)

    def test_habit_log_unique_constraint(self) -> None:
        """Test that habit log is unique per habit per date"""
        today = date.today()

        # Create first log
        HabitLog.objects.create(habit=self.habit, date=today)

        # Try to create duplicate log
        with self.assertRaises(IntegrityError):  # Should raise IntegrityError
            HabitLog.objects.create(habit=self.habit, date=today)

    def test_habit_log_ordering(self) -> None:
        """Test habit logs are ordered by date descending"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        log_old = HabitLog.objects.create(habit=self.habit, date=two_days_ago)
        log_new = HabitLog.objects.create(habit=self.habit, date=today)
        log_middle = HabitLog.objects.create(habit=self.habit, date=yesterday)

        logs = HabitLog.objects.filter(habit=self.habit)
        self.assertEqual(logs[0], log_new)  # Most recent
        self.assertEqual(logs[1], log_middle)
        self.assertEqual(logs[2], log_old)  # Oldest

    def test_habit_log_cascade_delete(self) -> None:
        """Test that habit logs are deleted when habit is deleted"""
        HabitLog.objects.create(habit=self.habit, date=date.today())

        self.assertEqual(HabitLog.objects.count(), 1)

        self.habit.delete()

        self.assertEqual(HabitLog.objects.count(), 0)

    def test_habit_log_different_habits_same_date(self) -> None:
        """Test that different habits can have logs on the same date"""
        other_habit = Habit.objects.create(title="Meditation", user=self.user)

        today = date.today()
        log1 = HabitLog.objects.create(habit=self.habit, date=today)
        log2 = HabitLog.objects.create(habit=other_habit, date=today)

        self.assertEqual(HabitLog.objects.count(), 2)
        self.assertEqual(log1.habit, self.habit)
        self.assertEqual(log2.habit, other_habit)
        self.assertEqual(log1.date, log2.date)

    def test_habit_log_user_filtering(self) -> None:
        """Test habit logs are filtered by habit's user"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")
        other_habit = Habit.objects.create(title="Other Habit", user=other_user)

        user_log = HabitLog.objects.create(habit=self.habit, date=date.today())
        other_log = HabitLog.objects.create(habit=other_habit, date=date.today())

        user_logs = HabitLog.objects.filter(habit__user=self.user)
        self.assertEqual(user_logs.count(), 1)
        self.assertEqual(user_logs[0], user_log)

        other_logs = HabitLog.objects.filter(habit__user=other_user)
        self.assertEqual(other_logs.count(), 1)
        self.assertEqual(other_logs[0], other_log)
