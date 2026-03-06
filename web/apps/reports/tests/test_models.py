# apps/reports/tests/test_models.py
import uuid

import pytest
from django.test import TestCase

from apps.reports.models import ActivityLog, ReviewSession
from apps.tasks.models import Task


@pytest.mark.integration
class ActivityLogModelTest(TestCase):
    def test_activity_log_creation(self) -> None:
        """Test creating an activity log"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        # Create a task to log activity for
        task = Task.objects.create(user=user, title="Test Task", description="Test Description")

        # Create activity log
        log = ActivityLog.objects.create(
            user=user, action_type=ActivityLog.ActionType.CREATED, content_object=task, description="Task created"
        )

        self.assertEqual(log.user, user)
        self.assertEqual(log.action_type, ActivityLog.ActionType.CREATED)
        self.assertEqual(log.content_object, task)
        self.assertEqual(log.description, "Task created")
        self.assertIsNotNone(log.timestamp)

    def test_activity_log_str_method(self) -> None:
        """Test activity log string representation"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        task = Task.objects.create(user=user, title="Test Task")
        log = ActivityLog.objects.create(user=user, action_type=ActivityLog.ActionType.COMPLETED, content_object=task)

        expected = f"{user} - completed - {log.timestamp}"
        self.assertEqual(str(log), expected)

    def test_activity_log_ordering(self) -> None:
        """Test activity logs are ordered by timestamp descending"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        task = Task.objects.create(user=user, title="Test Task")

        # Create logs with different timestamps
        log1 = ActivityLog.objects.create(user=user, action_type=ActivityLog.ActionType.CREATED, content_object=task)

        # Small delay to ensure different timestamps
        import time

        time.sleep(0.01)

        log2 = ActivityLog.objects.create(user=user, action_type=ActivityLog.ActionType.COMPLETED, content_object=task)

        # Should be ordered by timestamp descending
        logs = ActivityLog.objects.all()
        self.assertEqual(logs[0], log2)  # Most recent first
        self.assertEqual(logs[1], log1)

    def test_activity_log_with_details(self) -> None:
        """Test activity log with JSON details"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        task = Task.objects.create(user=user, title="Test Task")

        details = {"old_status": "todo", "new_status": "done"}
        log = ActivityLog.objects.create(
            user=user, action_type=ActivityLog.ActionType.STATUS_CHANGE, content_object=task, details=details
        )

        self.assertEqual(log.details, details)

    def test_activity_log_all_action_types(self) -> None:
        """Test all action types can be created"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        task = Task.objects.create(user=user, title="Test Task")

        action_types = [
            ActivityLog.ActionType.CREATED,
            ActivityLog.ActionType.UPDATED,
            ActivityLog.ActionType.STATUS_CHANGE,
            ActivityLog.ActionType.COMPLETED,
            ActivityLog.ActionType.DELETED,
        ]

        for action_type in action_types:
            log = ActivityLog.objects.create(user=user, action_type=action_type, content_object=task)
            self.assertEqual(log.action_type, action_type)


@pytest.mark.integration
class ReviewSessionModelTest(TestCase):
    def test_review_session_creation(self) -> None:
        """Test creating a review session"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        session = ReviewSession.objects.create(
            user=user, reflection="Good progress this week", next_week_priorities="Complete project X"
        )

        self.assertEqual(session.user, user)
        self.assertEqual(session.reflection, "Good progress this week")
        self.assertEqual(session.next_week_priorities, "Complete project X")
        self.assertIsNotNone(session.date)

    def test_review_session_defaults(self) -> None:
        """Test review session default values"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        session = ReviewSession.objects.create(user=user)

        self.assertEqual(session.reflection, "")
        self.assertEqual(session.next_week_priorities, "")
        self.assertIsNotNone(session.date)

    def test_review_session_str_method(self) -> None:
        """Test review session string representation"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        session = ReviewSession.objects.create(user=user)
        expected_date = session.date.strftime("%Y-%m-%d")
        expected = f"Review {expected_date}"

        self.assertEqual(str(session), expected)

    def test_review_session_ordering(self) -> None:
        """Test review sessions are ordered by date descending"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}", email="test@example.com", password="testpass123"
        )

        session1 = ReviewSession.objects.create(user=user)

        # Small delay to ensure different timestamps
        import time

        time.sleep(0.01)

        session2 = ReviewSession.objects.create(user=user)

        # Should be ordered by date descending
        sessions = ReviewSession.objects.all()
        self.assertEqual(sessions[0], session2)  # Most recent first
        self.assertEqual(sessions[1], session1)

    def test_review_session_user_filtering(self) -> None:
        """Test filtering review sessions by user"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user1 = User.objects.create_user(
            username=f"testuser1_{uuid.uuid4().hex[:8]}", email="test1@example.com", password="testpass123"
        )
        user2 = User.objects.create_user(
            username=f"testuser2_{uuid.uuid4().hex[:8]}", email="test2@example.com", password="testpass123"
        )

        session1 = ReviewSession.objects.create(user=user1)
        session2 = ReviewSession.objects.create(user=user2)

        user1_sessions = ReviewSession.objects.filter(user=user1)
        user2_sessions = ReviewSession.objects.filter(user=user2)

        self.assertEqual(user1_sessions.count(), 1)
        self.assertEqual(user2_sessions.count(), 1)
        self.assertEqual(user1_sessions.first(), session1)
        self.assertEqual(user2_sessions.first(), session2)
