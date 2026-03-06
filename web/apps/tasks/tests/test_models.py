from datetime import date, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.tasks.models import ChecklistItem, RecurringPattern, Task

User = get_user_model()


@pytest.mark.integration
class TaskModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_task_creation(self) -> None:
        """Test creating a basic task"""
        task = Task.objects.create(title="Test Task", description="Test Description", user=self.user)
        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.description, "Test Description")
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, "inbox")
        self.assertEqual(task.priority, 3)
        self.assertEqual(task.energy_required, 2)
        self.assertEqual(task.complexity, 1)

    def test_task_str_method(self) -> None:
        """Test task string representation"""
        task = Task.objects.create(title="Test Task", user=self.user)
        self.assertEqual(str(task), "Test Task")

    def test_task_defaults(self) -> None:
        """Test task default values"""
        task = Task.objects.create(title="Test Task", user=self.user)
        self.assertEqual(task.status, "inbox")
        self.assertEqual(task.priority, 3)
        self.assertEqual(task.energy_required, 2)
        self.assertEqual(task.complexity, 1)
        self.assertFalse(task.is_private)
        self.assertFalse(task.is_milestone)
        self.assertEqual(task.percent_complete, 0)
        self.assertIsNone(task.due_date)
        self.assertIsNone(task.project)

    def test_task_with_optional_fields(self) -> None:
        """Test creating task with all optional fields"""
        due_date = date.today() + timedelta(days=7)
        task = Task.objects.create(
            title="Complex Task",
            description="Complex Description",
            user=self.user,
            priority=1,
            energy_required=5,
            complexity=3,
            due_date=due_date,
            is_private=True,
            is_milestone=True,
            percent_complete=50,
        )
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.energy_required, 5)
        self.assertEqual(task.complexity, 3)
        self.assertEqual(task.due_date, due_date)
        self.assertTrue(task.is_private)
        self.assertTrue(task.is_milestone)
        self.assertEqual(task.percent_complete, 50)

    def test_task_with_all_fields(self) -> None:
        """Test task with all optional fields"""
        from apps.projects.models import Project

        project = Project.objects.create(user=self.user, title="Test Project")
        task = Task.objects.create(
            user=self.user,
            title="Complete Task",
            description="Test description",
            priority=1,
            duration_min=60,
            complexity=3,
            status="scheduled",
            due_date=timezone.now() + timedelta(days=1),
            project=project,
            is_milestone=True,
            is_critical_path=True,
        )

        self.assertEqual(task.title, "Complete Task")
        self.assertEqual(task.description, "Test description")
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.duration_min, 60)
        self.assertEqual(task.complexity, 3)
        self.assertEqual(task.status, "scheduled")
        self.assertEqual(task.project, project)
        self.assertTrue(task.is_milestone)
        self.assertTrue(task.is_critical_path)

    def test_task_auto_timestamps(self) -> None:
        """Test task auto-generated timestamps"""
        task = Task.objects.create(user=self.user, title="Timestamp Task")

        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)
        self.assertIsInstance(task.created_at, datetime)
        self.assertIsInstance(task.updated_at, datetime)


@pytest.mark.integration
class RecurringPatternModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_recurring_pattern_creation(self) -> None:
        """Test creating a basic recurring pattern"""
        pattern = RecurringPattern.objects.create(title="Daily Task", frequency="DAILY", interval=1, user=self.user)
        self.assertEqual(pattern.title, "Daily Task")
        self.assertEqual(pattern.frequency, "DAILY")
        self.assertEqual(pattern.interval, 1)
        self.assertEqual(pattern.user, self.user)
        self.assertTrue(pattern.is_active)
        self.assertEqual(pattern.generated_count, 0)

    def test_recurring_pattern_str_method(self) -> None:
        """Test recurring pattern string representation"""
        pattern = RecurringPattern.objects.create(title="Weekly Task", frequency="WEEKLY", interval=1, user=self.user)
        self.assertEqual(str(pattern), "Pattern: Weekly Task (Co tydzień)")

    def test_recurring_pattern_defaults(self) -> None:
        """Test recurring pattern default values"""
        pattern = RecurringPattern.objects.create(title="Test Pattern", frequency="DAILY", user=self.user)
        self.assertEqual(pattern.interval, 1)
        self.assertTrue(pattern.is_active)
        self.assertEqual(pattern.generated_count, 0)
        self.assertIsNone(pattern.end_date)
        self.assertFalse(pattern.is_dynamic)

    def test_recurring_pattern_with_end_date(self) -> None:
        """Test recurring pattern with end date"""
        end_date = date.today() + timedelta(days=30)
        pattern = RecurringPattern.objects.create(
            title="Limited Pattern", frequency="daily", user=self.user, end_date=end_date
        )
        self.assertEqual(pattern.end_date, end_date)

    def test_recurring_pattern_dynamic(self) -> None:
        """Test dynamic recurring pattern"""
        pattern = RecurringPattern.objects.create(
            title="Dynamic Pattern", frequency="daily", user=self.user, is_dynamic=True
        )
        self.assertTrue(pattern.is_dynamic)


@pytest.mark.integration
class ChecklistItemModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.task = Task.objects.create(title="Parent Task", user=self.user)

    def test_checklist_item_creation(self) -> None:
        """Test creating a checklist item"""
        item = ChecklistItem.objects.create(task=self.task, text="Checklist item", order=1)
        self.assertEqual(item.task, self.task)
        self.assertEqual(item.text, "Checklist item")
        self.assertEqual(item.order, 1)
        self.assertFalse(item.is_completed)

    def test_checklist_item_str_method(self) -> None:
        """Test checklist item string representation"""
        item = ChecklistItem.objects.create(task=self.task, text="Test item", order=1)
        self.assertEqual(str(item), "Test item")

    def test_checklist_item_defaults(self) -> None:
        """Test checklist item default values"""
        item = ChecklistItem.objects.create(task=self.task, text="Test item")
        self.assertEqual(item.order, 0)  # default value
        self.assertFalse(item.is_completed)

    def test_checklist_item_completion(self) -> None:
        """Test marking checklist item as completed"""
        item = ChecklistItem.objects.create(task=self.task, text="Test item", order=1)
        self.assertFalse(item.is_completed)

        item.is_completed = True
        item.save()

        updated_item = ChecklistItem.objects.get(pk=item.pk)
        self.assertTrue(updated_item.is_completed)

    def test_checklist_item_ordering(self) -> None:
        """Test checklist item ordering within a task"""
        item1 = ChecklistItem.objects.create(task=self.task, text="Item 1", order=2)
        item2 = ChecklistItem.objects.create(task=self.task, text="Item 2", order=1)

        items = ChecklistItem.objects.filter(task=self.task)
        self.assertEqual(items[0], item2)  # order=1
        self.assertEqual(items[1], item1)  # order=2

    def test_checklist_item_cascade_delete(self) -> None:
        """Test that checklist items are deleted when task is deleted"""
        ChecklistItem.objects.create(task=self.task, text="Test item", order=1)

        self.assertEqual(ChecklistItem.objects.count(), 1)

        self.task.delete()

        self.assertEqual(ChecklistItem.objects.count(), 0)
