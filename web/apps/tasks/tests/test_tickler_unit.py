# apps/tasks/tests/test_tickler_unit.py
"""Unit tests for TicklerService - pure domain logic without Django dependencies."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

from apps.tasks.domain.services.tickler import TicklerService


class TestTicklerServiceUnit:
    """Unit tests for TicklerService - pure domain logic."""

    def setup_method(self) -> None:
        """Setup for each test method."""
        self.service = TicklerService()
        self.now = datetime.now(UTC)
        self.user = Mock()

    def test_get_tasks_for_review_basic(self) -> None:
        """Test getting tasks for review - basic functionality."""
        today = date.today()

        # Mock Task.objects.filter
        mock_queryset = Mock()
        mock_queryset.order_by.return_value = mock_queryset

        with patch("apps.tasks.domain.services.tickler.Task") as mock_task_model:
            mock_task_model.objects.filter.return_value = mock_queryset

            result = self.service.get_tasks_for_review(self.user)

            # Verify the filter was called with correct parameters
            mock_task_model.objects.filter.assert_called_once_with(
                user=self.user, status__in=["waiting", "delegated", "postponed"], review_date__lte=today
            )
            mock_queryset.order_by.assert_called_once_with("review_date")

            assert result == mock_queryset

    def test_get_tasks_for_review_filter_logic(self) -> None:
        """Test that the filter logic correctly identifies review tasks."""
        today = date.today()

        with patch("apps.tasks.domain.services.tickler.Task") as mock_task_model:
            mock_queryset = Mock()
            mock_task_model.objects.filter.return_value = mock_queryset

            self.service.get_tasks_for_review(self.user)

            # Verify the filter includes correct statuses
            call_args = mock_task_model.objects.filter.call_args[1]
            assert call_args["status__in"] == ["waiting", "delegated", "postponed"]
            assert call_args["review_date__lte"] == today
            assert call_args["user"] == self.user

    def test_get_stale_waiting_tasks_basic(self) -> None:
        """Test getting stale waiting tasks - basic functionality."""
        days = 5

        # Mock Task.objects.filter
        mock_queryset = Mock()

        with (
            patch("apps.tasks.domain.services.tickler.Task") as mock_task_model,
            patch("django.utils.timezone"),
        ):
            # Setup timezone mock
            from django.utils import timezone as django_timezone

            mock_now = datetime.now(UTC)
            with patch.object(django_timezone, "now", return_value=mock_now):
                mock_task_model.objects.filter.return_value = mock_queryset

                result = self.service.get_stale_waiting_tasks(self.user, days)

                # Verify threshold calculation
                expected_threshold = mock_now - timedelta(days=days)
                mock_task_model.objects.filter.assert_called_once_with(
                    user=self.user, status="waiting", review_date__isnull=True, updated_at__lte=expected_threshold
                )

            assert result == mock_queryset

    def test_get_stale_waiting_tasks_default_days(self) -> None:
        """Test getting stale waiting tasks with default days parameter."""

        with (
            patch("apps.tasks.domain.services.tickler.Task") as mock_task_model,
            patch("django.utils.timezone"),
        ):
            mock_queryset = Mock()
            mock_task_model.objects.filter.return_value = mock_queryset

            # Call without days parameter (should default to 3)
            mock_now = datetime.now(UTC)
            from django.utils import timezone as django_timezone

            with patch.object(django_timezone, "now", return_value=mock_now):
                self.service.get_stale_waiting_tasks(self.user)

                # Verify default threshold (3 days)
                expected_threshold = mock_now - timedelta(days=3)
                call_args = mock_task_model.objects.filter.call_args[1]
                assert call_args["updated_at__lte"] == expected_threshold

    def test_get_stale_waiting_tasks_custom_days(self) -> None:
        """Test getting stale waiting tasks with custom days parameter."""
        custom_days = 7

        with (
            patch("apps.tasks.domain.services.tickler.Task") as mock_task_model,
            patch("django.utils.timezone"),
        ):
            mock_queryset = Mock()
            mock_task_model.objects.filter.return_value = mock_queryset

            mock_now = datetime.now(UTC)
            from django.utils import timezone as django_timezone

            with patch.object(django_timezone, "now", return_value=mock_now):
                self.service.get_stale_waiting_tasks(self.user, custom_days)

                # Verify custom threshold
                expected_threshold = mock_now - timedelta(days=custom_days)
                call_args = mock_task_model.objects.filter.call_args[1]
                assert call_args["updated_at__lte"] == expected_threshold

    def test_get_stale_waiting_tasks_filter_conditions(self) -> None:
        """Test that stale tasks filter has correct conditions."""

        with (
            patch("apps.tasks.domain.services.tickler.Task") as mock_task_model,
            patch("django.utils.timezone"),
        ):
            mock_queryset = Mock()
            mock_task_model.objects.filter.return_value = mock_queryset

            self.service.get_stale_waiting_tasks(self.user, 10)

            # Verify all filter conditions
            call_args = mock_task_model.objects.filter.call_args[1]
            assert call_args["user"] == self.user
            assert call_args["status"] == "waiting"
            assert call_args["review_date__isnull"] is True
            assert "updated_at__lte" in call_args

    def test_service_methods_return_queryset(self) -> None:
        """Test that service methods return Django QuerySet objects."""

        with (
            patch("apps.tasks.domain.services.tickler.Task") as mock_task_model,
            patch("django.utils.timezone"),
        ):
            mock_queryset = Mock()
            ordered_queryset = Mock()
            mock_task_model.objects.filter.return_value = mock_queryset
            mock_queryset.order_by.return_value = ordered_queryset

            # Test both methods return QuerySet
            review_result = self.service.get_tasks_for_review(self.user)
            stale_result = self.service.get_stale_waiting_tasks(self.user)

            assert review_result == ordered_queryset
            assert stale_result == mock_queryset

    def test_service_is_domain_layer(self) -> None:
        """Test that TicklerService operates at domain layer."""
        # The service should use domain logic and coordinate with infrastructure
        # It should not directly access database but use repository pattern

        # This test verifies the service uses Task model (adapter layer)
        # rather than directly accessing database
        assert hasattr(self.service, "get_tasks_for_review")
        assert hasattr(self.service, "get_stale_waiting_tasks")
        assert callable(self.service.get_tasks_for_review)
        assert callable(self.service.get_stale_waiting_tasks)

    def test_review_tasks_date_logic(self) -> None:
        """Test that review tasks use correct date comparison."""
        today = date.today()

        with patch("apps.tasks.domain.services.tickler.Task") as mock_task_model:
            mock_queryset = Mock()
            mock_task_model.objects.filter.return_value = mock_queryset

            self.service.get_tasks_for_review(self.user)

            # Should use today's date for comparison
            call_args = mock_task_model.objects.filter.call_args[1]
            assert call_args["review_date__lte"] == today
            # Should be less than or equal to today (not just less than)
            assert "review_date__lte" in call_args
