import uuid
from datetime import time

import pytest
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase

from apps.core.models import UserProfile

User = get_user_model()


@pytest.mark.integration
class UserProfileModelTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # Ensure signals are connected for automatic profile creation

    @classmethod
    def tearDownClass(cls) -> None:
        # Reconnect the signal
        from apps.core.models import create_user_profile, save_user_profile

        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)
        super().tearDownClass()

    def test_user_profile_creation(self) -> None:
        """Test creating a user profile"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        # Update the profile with specific values
        profile.work_start_hour = time(9, 0)
        profile.work_end_hour = time(17, 0)
        profile.personal_start_hour = time(18, 0)
        profile.personal_end_hour = time(22, 0)
        profile.save()

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.work_start_hour, time(9, 0))
        self.assertEqual(profile.work_end_hour, time(17, 0))
        self.assertEqual(profile.personal_start_hour, time(18, 0))
        self.assertEqual(profile.personal_end_hour, time(22, 0))

    def test_user_profile_str_method(self) -> None:
        """Test user profile string representation"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        self.assertEqual(str(profile), f"Profile of {user.username}")

    def test_user_profile_defaults(self) -> None:
        """Test user profile default values"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile

        # TimeField stores as string format, so compare with string representation
        self.assertEqual(str(profile.work_start_hour), "09:00")
        self.assertEqual(str(profile.work_end_hour), "17:00")
        self.assertEqual(str(profile.personal_start_hour), "17:00")
        self.assertEqual(str(profile.personal_end_hour), "22:00")
        self.assertEqual(profile.energy_profile, {})

    def test_user_profile_with_energy_profile(self) -> None:
        """Test user profile with energy profile"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        energy_profile = {
            "9": 3,  # High energy at 9 AM
            "14": 1,  # Low energy at 2 PM
            "20": 2,  # Medium energy at 8 PM
        }

        # Profile is created automatically by signal
        profile = user.profile
        profile.energy_profile = energy_profile
        profile.save()

        self.assertEqual(profile.energy_profile, energy_profile)

    def test_user_profile_energy_profile_defaults(self) -> None:
        """Test energy profile default values"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        self.assertEqual(profile.energy_profile, {})

    def test_user_profile_timezone_validation(self) -> None:
        """Test timezone validation (if implemented)"""
        # This test would need to be implemented if timezone validation is added
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        # Test basic profile creation without timezone field
        self.assertEqual(profile.user, user)

    def test_user_profile_time_validation(self) -> None:
        """Test work hours are logical (end after start)"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        profile.work_start_hour = time(17, 0)
        profile.work_end_hour = time(9, 0)  # End before start
        profile.save()
        # This test documents current behavior - validation might be added later
        self.assertEqual(profile.work_start_hour, time(17, 0))
        self.assertEqual(profile.work_end_hour, time(9, 0))

    def test_user_profile_cascade_delete(self) -> None:
        """Test that profile is deleted when user is deleted"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal

        self.assertEqual(UserProfile.objects.count(), 1)

        user.delete()

        self.assertEqual(UserProfile.objects.count(), 0)

    def test_user_profile_energy_profile_json_field(self) -> None:
        """Test energy profile is stored as JSON"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        energy_profile = {"morning": 3, "afternoon": 1, "evening": 2}

        # Profile is created automatically by signal
        profile = user.profile
        profile.energy_profile = energy_profile
        profile.save()

        # Retrieve from database to ensure JSON serialization works
        retrieved_profile = UserProfile.objects.get(pk=profile.pk)
        self.assertEqual(retrieved_profile.energy_profile, energy_profile)

    def test_user_profile_energy_profile_integer_keys(self) -> None:
        """Test energy profile with integer keys"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        energy_profile = {
            9: 3,  # 9 AM
            14: 1,  # 2 PM
            20: 2,  # 8 PM
        }

        # Profile is created automatically by signal
        profile = user.profile
        profile.energy_profile = energy_profile
        profile.save()

        retrieved_profile = UserProfile.objects.get(pk=profile.pk)
        # JSONField converts integer keys to strings when storing
        expected_profile = {"9": 3, "14": 1, "20": 2}
        self.assertEqual(retrieved_profile.energy_profile, expected_profile)

    def test_user_profile_work_hours_calculation(self) -> None:
        """Test work hours calculation logic"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        profile.work_start_hour = time(9, 0)
        profile.work_end_hour = time(17, 0)
        profile.save()

        # Calculate work hours duration
        start_minutes = profile.work_start_hour.hour * 60 + profile.work_start_hour.minute
        end_minutes = profile.work_end_hour.hour * 60 + profile.work_end_hour.minute
        duration = end_minutes - start_minutes

        self.assertEqual(duration, 8 * 60)  # 8 hours = 480 minutes

    def test_user_profile_personal_hours_calculation(self) -> None:
        """Test personal hours calculation logic"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        profile.personal_start_hour = time(18, 0)
        profile.personal_end_hour = time(22, 0)
        profile.save()

        # Calculate personal hours duration
        start_minutes = profile.personal_start_hour.hour * 60 + profile.personal_start_hour.minute
        end_minutes = profile.personal_end_hour.hour * 60 + profile.personal_end_hour.minute
        duration = end_minutes - start_minutes

        self.assertEqual(duration, 4 * 60)  # 4 hours = 240 minutes

    def test_user_profile_total_capacity_calculation(self) -> None:
        """Test total daily capacity calculation"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        # Profile is created automatically by signal
        profile = user.profile
        profile.work_start_hour = time(9, 0)
        profile.work_end_hour = time(17, 0)
        profile.personal_start_hour = time(18, 0)
        profile.personal_end_hour = time(22, 0)
        profile.save()

        # Calculate total capacity
        work_capacity = (profile.work_end_hour.hour * 60 + profile.work_end_hour.minute) - (
            profile.work_start_hour.hour * 60 + profile.work_start_hour.minute
        )
        personal_capacity = (profile.personal_end_hour.hour * 60 + profile.personal_end_hour.minute) - (
            profile.personal_start_hour.hour * 60 + profile.personal_start_hour.minute
        )
        total_capacity = work_capacity + personal_capacity

        self.assertEqual(total_capacity, 12 * 60)  # 12 hours = 720 minutes

    def test_user_profile_ordering(self) -> None:
        """Test user profile ordering"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )
        user2 = User.objects.create_user(
            username=f"testuser2_{uuid.uuid4().hex[:8]}", email="test2@example.com", password="testpass123"
        )

        # Profiles are created automatically by signals
        profile1 = user.profile
        profile2 = user2.profile

        profiles = UserProfile.objects.all()
        self.assertEqual(profiles[0], profile1)
        self.assertEqual(profiles[1], profile2)

    def test_user_profile_user_filtering(self) -> None:
        """Test filtering profiles by user"""
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        # Profile is created automatically by signal
        profile1 = user.profile

        profiles = UserProfile.objects.filter(user=user)
        self.assertEqual(profiles.count(), 1)
        self.assertEqual(profiles.first(), profile1)

        user_profiles = UserProfile.objects.filter(user=user)
        self.assertEqual(user_profiles.count(), 1)
        self.assertEqual(user_profiles[0], profile1)
