# apps/tasks/tests/test_task_scorer_unit.py
"""Unit tests for TaskScorer - pure domain logic without Django dependencies."""

from datetime import datetime, timedelta, timezone

from apps.tasks.domain.entities import TaskEntity
from apps.tasks.domain.services.task_scorer import TaskScorer


class TestTaskScorerUnit:
    """Unit tests for TaskScorer - pure domain logic."""

    def setup_method(self) -> None:
        """Setup for each test method."""
        self.scorer = TaskScorer()
        self.now = datetime.now(timezone.utc)

    def test_calculate_score_basic(self) -> None:
        """Test basic score calculation."""
        task = TaskEntity(
            id=1,
            title="Test Task",
            priority=3,  # Medium priority
            duration_min=60,
            duration_max=120,
            complexity=2,  # Medium complexity
        )

        score = self.scorer.calculate_score(task, self.now)

        assert isinstance(score, float)
        assert score > 0

    def test_calculate_score_priority_normalization(self) -> None:
        """Test priority normalization (1-5 -> 0.0-1.0)."""
        high_priority_task = TaskEntity(id=1, title="High", priority=1, duration_min=60, complexity=1)
        low_priority_task = TaskEntity(id=2, title="Low", priority=5, duration_min=60, complexity=1)

        high_score = self.scorer.calculate_score(high_priority_task, self.now)
        low_score = self.scorer.calculate_score(low_priority_task, self.now)

        # High priority should have higher score
        assert high_score > low_score

    def test_calculate_score_duration_normalization(self) -> None:
        """Test duration normalization."""
        short_task = TaskEntity(id=1, title="Short", priority=3, duration_min=30, complexity=1)
        long_task = TaskEntity(id=2, title="Long", priority=3, duration_min=240, complexity=1)

        short_score = self.scorer.calculate_score(short_task, self.now)
        long_score = self.scorer.calculate_score(long_task, self.now)

        # Shorter tasks should have higher score
        assert short_score > long_score

    def test_calculate_score_complexity_normalization(self) -> None:
        """Test complexity normalization."""
        simple_task = TaskEntity(id=1, title="Simple", priority=3, duration_min=60, complexity=1)
        complex_task = TaskEntity(id=2, title="Complex", priority=3, duration_min=60, complexity=5)

        simple_score = self.scorer.calculate_score(simple_task, self.now)
        complex_score = self.scorer.calculate_score(complex_task, self.now)

        # Simpler tasks should have higher score
        assert simple_score > complex_score

    def test_calculate_score_with_due_date_urgent(self) -> None:
        """Test task scorer with urgent due date."""
        # Task due in 2 hours - should be very urgent
        task_with_due = TaskEntity(
            id=1,
            title="Urgent Task",
            priority=3,
            duration_min=60,
            complexity=2,
            due_date=self.now + timedelta(hours=2),
        )
        score = self.scorer.calculate_score(task_with_due, self.now)
        assert score > 0

    def test_calculate_score_with_due_date_overdue(self) -> None:
        """Test task scorer with overdue task."""
        # Task overdue by 1 day - should have maximum urgency
        task_overdue = TaskEntity(
            id=1,
            title="Overdue Task",
            priority=3,
            duration_min=60,
            complexity=2,
            due_date=self.now - timedelta(days=1),
        )
        score = self.scorer.calculate_score(task_overdue, self.now)
        assert score > 0

    def test_calculate_score_with_goal_deadline(self) -> None:
        """Test task scorer with goal deadline."""
        task_with_goal = TaskEntity(
            id=1,
            title="Goal Task",
            priority=3,
            duration_min=60,
            complexity=2,
            goal_deadline=self.now + timedelta(days=7),
        )
        score = self.scorer.calculate_score(task_with_goal, self.now)
        assert score > 0

    def test_calculate_score_with_project_deadline(self) -> None:
        """Test task scorer with project deadline."""
        task_with_project = TaskEntity(
            id=1,
            title="Project Task",
            priority=3,
            duration_min=60,
            complexity=2,
            project_deadline=self.now + timedelta(days=14),
        )
        score = self.scorer.calculate_score(task_with_project, self.now)
        assert score > 0

    def test_calculate_score_with_milestone(self) -> None:
        """Test task scorer with milestone bonus."""
        milestone_task = TaskEntity(
            id=1,
            title="Milestone Task",
            priority=3,
            duration_min=60,
            complexity=2,
            is_milestone=True,
        )
        regular_task = TaskEntity(
            id=2,
            title="Regular Task",
            priority=3,
            duration_min=60,
            complexity=2,
            is_milestone=False,
        )

        milestone_score = self.scorer.calculate_score(milestone_task, self.now)
        regular_score = self.scorer.calculate_score(regular_task, self.now)

        # Milestone should have higher score
        assert milestone_score > regular_score

    def test_calculate_score_energy_match(self) -> None:
        """Test energy matching bonus."""
        # High energy task in high energy slot
        high_energy_task = TaskEntity(
            id=1,
            title="High Energy Task",
            priority=3,
            duration_min=60,
            complexity=2,
            energy_required=3,
        )
        score_high_slot = self.scorer.calculate_score(high_energy_task, self.now, slot_energy_level=3)
        score_low_slot = self.scorer.calculate_score(high_energy_task, self.now, slot_energy_level=1)

        # Higher energy slot should give better score for high energy task
        assert score_high_slot > score_low_slot

    def test_calculate_score_sequence_bonus(self) -> None:
        """Test sequence bonus for same project."""
        task1 = TaskEntity(
            id=1,
            title="Task 1",
            priority=3,
            duration_min=60,
            complexity=2,
            project_id=1,
        )
        task2 = TaskEntity(
            id=2,
            title="Task 2",
            priority=3,
            duration_min=60,
            complexity=2,
            project_id=2,  # Different project
        )

        score_with_sequence = self.scorer.calculate_score(task1, self.now, last_project_id=1)
        score_without_sequence = self.scorer.calculate_score(task2, self.now, last_project_id=1)

        # Same project should get sequence bonus
        assert score_with_sequence > score_without_sequence

    def test_calculate_score_aging_bonus(self) -> None:
        """Test aging bonus for old tasks."""
        old_task = TaskEntity(
            id=1,
            title="Old Task",
            priority=3,
            duration_min=60,
            complexity=2,
            ready_since=self.now - timedelta(days=2),
        )
        new_task = TaskEntity(
            id=2,
            title="New Task",
            priority=3,
            duration_min=60,
            complexity=2,
            ready_since=self.now - timedelta(hours=1),
        )

        old_score = self.scorer.calculate_score(old_task, self.now)
        new_score = self.scorer.calculate_score(new_task, self.now)

        # Older task should get aging bonus
        assert old_score > new_score

    def test_calculate_score_end_of_day_factor(self) -> None:
        """Test end of day factor."""
        short_task = TaskEntity(
            id=1,
            title="Short Task",
            priority=3,
            duration_min=30,  # Short task
            complexity=2,
            due_date=self.now + timedelta(days=1),  # Due today
        )
        long_task = TaskEntity(
            id=2,
            title="Long Task",
            priority=3,
            duration_min=120,  # Long task
            complexity=4,  # Complex task
            due_date=self.now + timedelta(days=1),
        )

        # Near end of day (1 hour left)
        eod_score_short = self.scorer.calculate_score(short_task, self.now, hours_to_end_of_day=1.0)
        eod_score_long = self.scorer.calculate_score(long_task, self.now, hours_to_end_of_day=1.0)

        # Short task should be preferred near end of day
        assert eod_score_short > eod_score_long

    def test_get_weights_for_strategy_default(self) -> None:
        """Test getting default strategy weights."""
        weights = TaskScorer.get_weights_for_strategy("nonexistent")
        expected_keys = {
            "w_priority",
            "w_duration",
            "w_complexity",
            "w_urgency",
            "w_goal_urgency",
            "w_project_urgency",
            "bonus_sequence",
            "bonus_energy_match",
            "bonus_milestone",
        }
        assert set(weights.keys()) == expected_keys

    def test_get_weights_for_strategy_warmup(self) -> None:
        """Test warmup strategy weights."""
        weights = TaskScorer.get_weights_for_strategy("warmup")
        assert weights["w_complexity"] == 0.8  # Higher complexity weight
        assert weights["w_duration"] == 0.6  # Higher duration weight
        assert weights["w_priority"] == 0.1  # Lower priority weight

    def test_get_weights_for_strategy_deep_work(self) -> None:
        """Test deep work strategy weights."""
        weights = TaskScorer.get_weights_for_strategy("deep_work")
        assert weights["bonus_sequence"] == 2.5  # Very high sequence bonus

    def test_get_weights_for_strategy_deadline(self) -> None:
        """Test deadline strategy weights."""
        weights = TaskScorer.get_weights_for_strategy("deadline")
        assert weights["w_urgency"] == 3.0  # Very high urgency weight
        assert weights["w_goal_urgency"] == 2.0  # High goal urgency
        assert weights["w_project_urgency"] == 2.0  # High project urgency
        assert weights["w_complexity"] == 0.0  # Complexity ignored
