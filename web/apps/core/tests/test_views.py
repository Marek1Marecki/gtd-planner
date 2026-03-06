# apps/core/tests/test_views.py
import uuid
from datetime import date
from unittest.mock import Mock, patch

import pytest
from django.contrib.messages import get_messages
from django.test import RequestFactory, TestCase

from apps.core.models import GoogleCredentials, UserProfile
from apps.tasks.models import Task


@pytest.mark.integration
class CoreViewsTest(TestCase):
    def setUp(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        self.client.login(username=self.user.username, password="testpass123")
        self.factory = RequestFactory()

    def test_google_login_view(self) -> None:
        """Test Google OAuth login view"""
        with patch("apps.core.views.Flow.from_client_secrets_file") as mock_flow:
            mock_flow_instance = Mock()
            mock_flow.return_value = mock_flow_instance
            mock_flow_instance.authorization_url.return_value = ("http://auth.url", "test_state")

            response = self.client.get("/core/google/login/")

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response["Location"], "http://auth.url")
            self.assertEqual(self.client.session["google_auth_state"], "test_state")

    def test_google_login_view_scopes(self) -> None:
        """Test Google login uses correct scopes"""
        with patch("apps.core.views.Flow.from_client_secrets_file") as mock_flow:
            mock_flow_instance = Mock()
            mock_flow.return_value = mock_flow_instance
            mock_flow_instance.authorization_url.return_value = ("http://auth.url", "test_state")

            self.client.get("/core/google/login/")

            # Check that flow was called with correct parameters
            mock_flow.assert_called_once()
            call_args = mock_flow.call_args
            self.assertIn("scopes", call_args[1])
            self.assertEqual(call_args[1]["scopes"], ["https://www.googleapis.com/auth/calendar.events"])

    def test_google_callback_view(self) -> None:
        """Test Google OAuth callback view"""
        # Set session state
        session = self.client.session
        session["google_auth_state"] = "test_state"
        session.save()

        with patch("apps.core.views.Flow.from_client_secrets_file") as mock_flow:
            mock_flow_instance = Mock()
            mock_flow.return_value = mock_flow_instance

            # Mock credentials
            mock_creds = Mock()
            mock_creds.token = "access_token"
            mock_creds.refresh_token = "refresh_token"
            mock_creds.token_uri = "token_uri"
            mock_creds.client_id = "client_id"
            mock_creds.client_secret = "client_secret"
            mock_creds.scopes = ["calendar.events"]

            mock_flow_instance.credentials = mock_creds

            response = self.client.get("/core/google/callback/?code=test_code")

            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, "/core/settings/")

            # Check credentials were saved
            creds = GoogleCredentials.objects.get(user=self.user)
            self.assertEqual(creds.token, "access_token")
            self.assertEqual(creds.refresh_token, "refresh_token")

    def test_google_callback_view_updates_existing_credentials(self) -> None:
        """Test Google callback updates existing credentials"""
        # Create existing credentials
        GoogleCredentials.objects.create(user=self.user, token="old_token", refresh_token="old_refresh")

        session = self.client.session
        session["google_auth_state"] = "test_state"
        session.save()

        with patch("apps.core.views.Flow.from_client_secrets_file") as mock_flow:
            mock_flow_instance = Mock()
            mock_flow.return_value = mock_flow_instance

            mock_creds = Mock()
            mock_creds.token = "new_token"
            mock_creds.refresh_token = "new_refresh"
            mock_creds.token_uri = "token_uri"
            mock_creds.client_id = "client_id"
            mock_creds.client_secret = "client_secret"
            mock_creds.scopes = ["calendar.events"]

            mock_flow_instance.credentials = mock_creds

            response = self.client.get("/core/google/callback/?code=test_code")

            self.assertEqual(response.status_code, 302)

            # Check credentials were updated
            creds = GoogleCredentials.objects.get(user=self.user)
            self.assertEqual(creds.token, "new_token")
            self.assertEqual(creds.refresh_token, "new_refresh")

    def test_settings_view_get(self) -> None:
        """Test settings view GET request"""
        response = self.client.get("/core/settings/")
        self.assertEqual(response.status_code, 200)

        # Check context
        self.assertIn("form", response.context)
        self.assertIn("energy_range", response.context)
        self.assertIn("current_energy", response.context)
        self.assertEqual(list(response.context["energy_range"]), list(range(0, 24)))

    def test_settings_view_creates_profile(self) -> None:
        """Test settings view creates profile if missing"""
        # Delete existing profile
        try:
            self.user.profile.delete()
        except UserProfile.DoesNotExist:
            pass

        response = self.client.get("/core/settings/")
        self.assertEqual(response.status_code, 200)

        # Profile should be created
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_settings_view_post_valid(self) -> None:
        """Test settings view POST with valid data"""
        data = {
            "work_start_hour": "09:00",
            "work_end_hour": "17:00",
            "personal_start_hour": "18:00",
            "personal_end_hour": "22:00",
            "morning_buffer_minutes": "30",
            "evening_buffer_minutes": "30",
            "wip_limit": "5",
            "current_strategy": "balanced",
            # Energy profile data
            "energy_09": "3",
            "energy_14": "1",
            "energy_20": "2",
        }

        response = self.client.post("/core/settings/", data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/core/settings/")

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Ustawienia zapisane pomyślnie!")

        # Check profile was updated
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.work_start_hour.strftime("%H:%M"), "09:00")
        self.assertEqual(profile.work_end_hour.strftime("%H:%M"), "17:00")
        self.assertEqual(profile.wip_limit, 5)
        self.assertEqual(profile.current_strategy, "balanced")
        self.assertEqual(profile.energy_profile, {"09": 3, "14": 1, "20": 2})

    def test_settings_view_post_invalid(self) -> None:
        """Test settings view POST with invalid data"""
        data = {
            "work_start_hour": "invalid_time",
            "work_end_hour": "17:00",
            "personal_start_hour": "18:00",
            "personal_end_hour": "22:00",
            "morning_buffer_minutes": "30",
            "evening_buffer_minutes": "30",
            "wip_limit": "5",
            "current_strategy": "balanced",
        }

        response = self.client.post("/core/settings/", data)
        self.assertEqual(response.status_code, 200)

        # Should show form with errors
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)

    def test_settings_view_post_partial_energy_data(self) -> None:
        """Test settings view POST with partial energy profile data"""
        data = {
            "work_start_hour": "09:00",
            "work_end_hour": "17:00",
            "personal_start_hour": "18:00",
            "personal_end_hour": "22:00",
            "morning_buffer_minutes": "30",
            "evening_buffer_minutes": "30",
            "wip_limit": "5",
            "current_strategy": "balanced",
            "energy_09": "3",
            "energy_14": "1",
            # Missing energy_20
        }

        response = self.client.post("/core/settings/", data)
        self.assertEqual(response.status_code, 302)

        # Should save only provided energy data
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.energy_profile, {"09": 3, "14": 1})

    def test_settings_view_post_no_energy_data(self) -> None:
        """Test settings view POST with no energy profile data"""
        data = {
            "work_start_hour": "09:00",
            "work_end_hour": "17:00",
            "personal_start_hour": "18:00",
            "personal_end_hour": "22:00",
            "morning_buffer_minutes": "30",
            "evening_buffer_minutes": "30",
            "wip_limit": "5",
            "current_strategy": "balanced",
        }

        response = self.client.post("/core/settings/", data)
        self.assertEqual(response.status_code, 302)

        # Energy profile should be empty
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.energy_profile, {})

    def test_dashboard_view(self) -> None:
        """Test dashboard view"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Check context variables
        self.assertIn("tasks_today", response.context)
        self.assertIn("tasks_overdue", response.context)
        self.assertIn("tasks_inbox", response.context)
        self.assertIn("projects", response.context)
        self.assertIn("today", response.context)

    def test_dashboard_view_with_tasks(self) -> None:
        """Test dashboard view with tasks"""
        # Create tasks with different statuses
        Task.objects.create(user=self.user, title="Scheduled Task", status="scheduled")
        Task.objects.create(user=self.user, title="Overdue Task", status="overdue")
        Task.objects.create(user=self.user, title="Inbox Task", status="inbox")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["tasks_today"], 1)
        self.assertEqual(response.context["tasks_overdue"], 1)
        self.assertEqual(response.context["tasks_inbox"], 1)

    def test_dashboard_view_with_projects(self) -> None:
        """Test dashboard view with projects"""
        from apps.projects.models import Project

        # Create projects
        for i in range(7):
            Project.objects.create(user=self.user, title=f"Project {i}", status="active")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Should show only 5 most recent projects
        projects = response.context["projects"]
        self.assertEqual(len(projects), 5)

    def test_set_work_mode_view_focus_mode(self) -> None:
        """Test set work mode view with focus mode"""
        response = self.client.post("/core/set-mode/", {"mode": "focus"})
        self.assertEqual(response.status_code, 200)

        # Check profile was updated - refresh from database
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.morning_buffer_minutes, 15)
        self.assertEqual(profile.between_tasks_buffer_minutes, 0)
        self.assertEqual(profile.current_strategy, "deep_work")

        # Check response content
        self.assertIn("Tryb: Focus", response.content.decode())
        self.assertIn("Głęboka Praca", response.content.decode())

    def test_set_work_mode_view_light_mode(self) -> None:
        """Test set work mode view with light mode"""
        response = self.client.post("/core/set-mode/", {"mode": "light"})
        self.assertEqual(response.status_code, 200)

        # Check profile was updated - refresh from database
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.morning_buffer_minutes, 45)
        self.assertEqual(profile.between_tasks_buffer_minutes, 15)
        self.assertEqual(profile.current_strategy, "warmup")

        # Check response content
        self.assertIn("Tryb: Light", response.content.decode())
        self.assertIn("Rozgrzewka", response.content.decode())

    def test_set_work_mode_view_normal_mode(self) -> None:
        """Test set work mode view with normal mode"""
        response = self.client.post("/core/set-mode/", {"mode": "normal"})
        self.assertEqual(response.status_code, 200)

        # Check profile was updated - refresh from database
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.morning_buffer_minutes, 30)
        self.assertEqual(profile.between_tasks_buffer_minutes, 5)
        self.assertEqual(profile.current_strategy, "balanced")

        # Check response content
        self.assertIn("Tryb: Normal", response.content.decode())
        self.assertIn("Zrównoważony", response.content.decode())

    def test_set_work_mode_view_invalid_mode(self) -> None:
        """Test set work mode view with invalid mode"""
        response = self.client.post("/core/set-mode/", {"mode": "invalid"})
        self.assertEqual(response.status_code, 200)

        # Should default to normal mode - refresh from database
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(profile.morning_buffer_minutes, 30)
        self.assertEqual(profile.between_tasks_buffer_minutes, 5)
        self.assertEqual(profile.current_strategy, "balanced")

    def test_set_work_mode_view_requires_post(self) -> None:
        """Test set work mode view requires POST method"""
        response = self.client.get("/core/set-mode/")
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_set_work_mode_view_requires_login(self) -> None:
        """Test set work mode view requires authentication"""
        self.client.logout()
        response = self.client.post("/core/set-mode/", {"mode": "focus"})
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_settings_view_requires_login(self) -> None:
        """Test settings view requires authentication"""
        self.client.logout()
        response = self.client.get("/core/settings/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_view_requires_login(self) -> None:
        """Test dashboard view requires authentication"""
        self.client.logout()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_google_callback_requires_session_state(self) -> None:
        """Test Google callback requires session state"""
        # Clear session
        session = self.client.session
        session.clear()
        session.save()

        response = self.client.get("/core/google/callback/?code=test_code")
        # Should handle missing state gracefully
        self.assertEqual(response.status_code, 302)

    def test_settings_view_with_existing_profile(self) -> None:
        """Test settings view with existing profile"""
        # Create profile with specific data
        profile, created = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                "work_start_hour": "08:00",
                "work_end_hour": "16:00",
                "energy_profile": {"09": 3, "14": 1},
                "personal_start_hour": "17:00",
                "personal_end_hour": "22:00",
                "morning_buffer_minutes": 30,
                "evening_buffer_minutes": 30,
                "wip_limit": 5,
                "current_strategy": "balanced",
            },
        )

        # Update energy profile if profile already existed
        if not created:
            profile.energy_profile = {"09": 3, "14": 1}
            profile.save()

        response = self.client.get("/core/settings/")
        self.assertEqual(response.status_code, 200)

        # Form should be initialized with existing data
        form = response.context["form"]
        self.assertEqual(form.instance, profile)
        self.assertEqual(response.context["current_energy"], {"09": 3, "14": 1})

    def test_dashboard_view_date_context(self) -> None:
        """Test dashboard view includes current date"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Should include today's date
        self.assertEqual(response.context["today"], date.today())

    def test_set_work_mode_view_response_format(self) -> None:
        """Test set work mode view response format"""
        response = self.client.post("/core/set-mode/", {"mode": "focus"})
        self.assertEqual(response.status_code, 200)

        # Response should be HTML with badge styling
        content = response.content.decode()
        self.assertIn('class="badge bg-secondary"', content)
        self.assertIn('title="Strategia:', content)
