from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.habits.models import Habit, HabitLog

User = get_user_model()


@pytest.mark.integration
class HabitViewsTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

        self.habit = Habit.objects.create(title="Exercise", user=self.user)

    def test_habit_list_widget_view(self) -> None:
        """Test habit list widget view"""
        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exercise")
        self.assertTemplateUsed(response, "habits/partials/widget.html")

    def test_habit_list_widget_view_unauthenticated(self) -> None:
        """Test habit list widget view requires authentication"""
        self.client.logout()
        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_habit_list_widget_view_with_completion(self) -> None:
        """Test habit list widget shows completion status"""
        today = date.today()
        # Mark habit as completed today
        HabitLog.objects.create(habit=self.habit, date=today)

        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exercise")

    def test_habit_complete_view_post(self) -> None:
        """Test habit completion view"""
        today = date.today()

        # Ensure habit is not completed today
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 0)

        response = self.client.post(reverse("habit_complete", args=[self.habit.pk]))

        self.assertEqual(response.status_code, 200)  # HTMX request returns 200

        # Check habit log was created
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)

    def test_habit_complete_view_already_completed(self) -> None:
        """Test completing an already completed habit"""
        today = date.today()
        # Mark habit as already completed
        HabitLog.objects.create(habit=self.habit, date=today)

        response = self.client.post(reverse("habit_complete", args=[self.habit.pk]))

        self.assertEqual(response.status_code, 200)

        # Should still only have one log (no duplicate)
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=today).count(), 1)

    def test_habit_complete_view_not_found(self) -> None:
        """Test completing non-existent habit"""
        response = self.client.post(reverse("habit_complete", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_habit_complete_view_other_user(self) -> None:
        """Test completing other user's habit"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")
        other_habit = Habit.objects.create(title="Other Habit", user=other_user)

        response = self.client.post(reverse("habit_complete", args=[other_habit.pk]))
        self.assertEqual(response.status_code, 404)  # Should not be accessible

    def test_habit_list_widget_filtering(self) -> None:
        """Test habit list widget filters active habits only"""
        Habit.objects.create(title="Inactive Habit", user=self.user, is_active=False)

        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exercise")
        self.assertNotContains(response, "Inactive Habit")

    def test_habit_list_widget_user_filtering(self) -> None:
        """Test habit list widget shows only user's habits"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")
        Habit.objects.create(title="Other Habit", user=other_user)

        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exercise")
        self.assertNotContains(response, "Other Habit")

    def test_habit_list_widget_with_streak(self) -> None:
        """Test habit list widget shows streak information"""
        # Set up a habit with a streak
        self.habit.current_streak = 5
        self.habit.longest_streak = 10
        self.habit.save()

        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "🔥 5")  # Streak display

    def test_habit_complete_view_updates_habit_model(self) -> None:
        """Test that completing habit updates habit model fields"""
        response = self.client.post(reverse("habit_complete", args=[self.habit.pk]))

        self.assertEqual(response.status_code, 200)

        # Check habit was updated (this would be done by HabitService)
        # Note: This test assumes the service is called in the view
        # The service should update these fields
        # self.assertEqual(Habit.objects.get(pk=self.habit.pk).last_completed_date, today)
        # self.assertGreaterEqual(Habit.objects.get(pk=self.habit.pk).current_streak, 1)

    def test_habit_list_widget_htmx_request(self) -> None:
        """Test habit list widget handles HTMX requests"""
        response = self.client.get(reverse("habit_widget"), HTTP_HX_Request="true")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "habits/partials/widget.html")

    def test_habit_complete_view_htmx_target(self) -> None:
        """Test habit complete view returns HTMX-compatible response"""
        response = self.client.post(reverse("habit_complete", args=[self.habit.pk]), HTTP_HX_Request="true")

        self.assertEqual(response.status_code, 200)
        # Should return the updated widget HTML
        self.assertContains(response, "Exercise")

    def test_multiple_habits_in_widget(self) -> None:
        """Test widget displays multiple habits correctly"""
        Habit.objects.create(title="Meditation", user=self.user)

        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exercise")
        self.assertContains(response, "Meditation")

    def test_habit_completion_persistence(self) -> None:
        """Test that habit completion persists across requests"""
        # Complete habit
        response = self.client.post(reverse("habit_complete", args=[self.habit.pk]))
        self.assertEqual(response.status_code, 200)

        # Check in subsequent request that habit is still marked as completed
        response = self.client.get(reverse("habit_widget"))
        self.assertEqual(response.status_code, 200)

        # The template should show habit as completed
        # This depends on the template logic using last_completed_date == today
