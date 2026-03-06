from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.habits.models import Habit, HabitLog
from apps.habits.services import HabitService

User = get_user_model()


@pytest.mark.integration
class HabitServiceTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.habit_service = HabitService()

        self.habit = Habit.objects.create(title="Exercise", user=self.user)

    def test_complete_habit_new_completion(self) -> None:
        """Test completing a habit for the first time today"""
        today = date.today()

        # Ensure no completion exists for today
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 0)

        # Complete the habit
        self.habit_service.complete_habit(self.habit, today)

        # Check log was created
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)

        # Check habit was updated
        updated_habit = Habit.objects.get(pk=self.habit.pk)
        self.assertEqual(updated_habit.last_completed_date, today)
        self.assertEqual(updated_habit.current_streak, 1)
        self.assertEqual(updated_habit.longest_streak, 1)

    def test_complete_habit_already_completed_today(self) -> None:
        """Test completing a habit that's already completed today"""
        today = date.today()

        # Mark as already completed
        HabitLog.objects.create(habit=self.habit, date=today)
        self.habit.current_streak = 3
        self.habit.longest_streak = 5
        self.habit.save()

        # Try to complete again
        self.habit_service.complete_habit(self.habit, today)

        # Should still only have one log
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)

        # Streak should not change
        updated_habit = Habit.objects.get(pk=self.habit.pk)
        self.assertEqual(updated_habit.current_streak, 3)
        self.assertEqual(updated_habit.longest_streak, 5)

    def test_complete_habit_continues_streak(self) -> None:
        """Test completing habit continues existing streak"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Set up existing streak
        HabitLog.objects.create(habit=self.habit, date=yesterday)
        self.habit.current_streak = 5
        self.habit.longest_streak = 5
        self.habit.last_completed_date = yesterday
        self.habit.save()

        # Complete today
        self.habit_service.complete_habit(self.habit, today)

        # Streak should increase
        updated_habit = Habit.objects.get(pk=self.habit.pk)
        self.assertEqual(updated_habit.current_streak, 6)
        self.assertEqual(updated_habit.longest_streak, 6)
        self.assertEqual(updated_habit.last_completed_date, today)

    def test_complete_habit_breaks_and_starts_new_streak(self) -> None:
        """Test completing habit after breaking streak starts new streak"""
        today = date.today()
        two_days_ago = today - timedelta(days=2)

        # Set up broken streak (completed 2 days ago, not yesterday)
        HabitLog.objects.create(habit=self.habit, date=two_days_ago)
        self.habit.current_streak = 10
        self.habit.longest_streak = 10
        self.habit.last_completed_date = two_days_ago
        self.habit.save()

        # Complete today (streak was broken)
        self.habit_service.complete_habit(self.habit, today)

        # Should start new streak of 1
        updated_habit = Habit.objects.get(pk=self.habit.pk)
        self.assertEqual(updated_habit.current_streak, 1)
        self.assertEqual(updated_habit.longest_streak, 10)  # Longest should remain
        self.assertEqual(updated_habit.last_completed_date, today)

    def test_complete_habit_updates_longest_streak(self) -> None:
        """Test completing habit updates longest streak when current exceeds it"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Set up streak that will exceed longest
        HabitLog.objects.create(habit=self.habit, date=yesterday)
        self.habit.current_streak = 4
        self.habit.longest_streak = 4
        self.habit.last_completed_date = yesterday
        self.habit.save()

        # Complete today (makes streak 5, which equals longest)
        self.habit_service.complete_habit(self.habit, today)

        updated_habit = Habit.objects.get(pk=self.habit.pk)
        self.assertEqual(updated_habit.current_streak, 5)
        self.assertEqual(updated_habit.longest_streak, 5)
        self.assertEqual(updated_habit.last_completed_date, today)

    def test_complete_habit_multiple_habits(self) -> None:
        """Test completing multiple habits independently"""
        habit2 = Habit.objects.create(title="Meditation", user=self.user)
        today = date.today()

        # Complete both habits
        self.habit_service.complete_habit(self.habit, today)
        self.habit_service.complete_habit(habit2, today)

        # Both should have logs
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)
        self.assertEqual(HabitLog.objects.filter(habit=habit2, date=today).count(), 1)

        # Both should have streaks of 1
        updated_habit1 = Habit.objects.get(pk=self.habit.pk)
        updated_habit2 = Habit.objects.get(pk=habit2.pk)
        self.assertEqual(updated_habit1.current_streak, 1)
        self.assertEqual(updated_habit2.current_streak, 1)

    def test_complete_habit_different_users(self) -> None:
        """Test completing habits doesn't affect other users' habits"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")
        other_habit = Habit.objects.create(title="Exercise", user=other_user)
        today = date.today()

        # Complete user's habit
        self.habit_service.complete_habit(self.habit, today)

        # User's habit should be completed
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)

        # Other user's habit should not be affected
        self.assertEqual(HabitLog.objects.filter(habit=other_habit, date=today).count(), 0)

    def test_complete_habit_backdating(self) -> None:
        """Test completing habit for a past date"""
        today = date.today()
        past_date = today - timedelta(days=5)

        # Complete for past date
        self.habit_service.complete_habit(self.habit, past_date)

        # Should create log for past date
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=past_date).count(), 1)

        # Should not create log for today
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 0)

    def test_complete_habit_future_date(self) -> None:
        """Test completing habit for a future date"""
        today = date.today()
        future_date = today + timedelta(days=5)

        # Complete for future date
        self.habit_service.complete_habit(self.habit, future_date)

        # Should create log for future date
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=future_date).count(), 1)

        # Should not create log for today
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 0)

    def test_service_with_inactive_habit(self) -> None:
        """Test service behavior with inactive habit"""
        self.habit.is_active = False
        self.habit.save()

        today = date.today()

        # Should still be able to complete inactive habit
        self.habit_service.complete_habit(self.habit, today)

        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)
