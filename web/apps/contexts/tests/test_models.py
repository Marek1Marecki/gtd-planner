import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.contexts.models import Context, Tag

User = get_user_model()


@pytest.mark.integration
class ContextModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_context_creation(self) -> None:
        """Test creating a basic context"""
        context = Context.objects.create(user=self.user, name="@office", icon="bi-building", color="#6c757d")
        self.assertEqual(context.user, self.user)
        self.assertEqual(context.name, "@office")
        self.assertEqual(context.icon, "bi-building")
        self.assertEqual(context.color, "#6c757d")
        self.assertTrue(context.is_active)

    def test_context_str_method(self) -> None:
        """Test context string representation"""
        context = Context.objects.create(user=self.user, name="@office")
        self.assertEqual(str(context), "@office")

    def test_context_defaults(self) -> None:
        """Test context default values"""
        context = Context.objects.create(user=self.user, name="@home")
        self.assertEqual(context.icon, "bi-tag")
        self.assertEqual(context.color, "#6c757d")
        self.assertTrue(context.is_active)

    def test_context_with_custom_icon_and_color(self) -> None:
        """Test context with custom icon and color"""
        context = Context.objects.create(user=self.user, name="@mobile", icon="bi-phone", color="#ff0000")
        self.assertEqual(context.icon, "bi-phone")
        self.assertEqual(context.color, "#ff0000")

    def test_context_deactivation(self) -> None:
        """Test deactivating a context"""
        context = Context.objects.create(user=self.user, name="@office")

        context.is_active = False
        context.save()

        updated_context = Context.objects.get(pk=context.pk)
        self.assertFalse(updated_context.is_active)

    def test_context_user_filtering(self) -> None:
        """Test contexts are filtered by user"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")

        user_context = Context.objects.create(user=self.user, name="@office")
        other_context = Context.objects.create(user=other_user, name="@home")

        user_contexts = Context.objects.filter(user=self.user)
        self.assertEqual(user_contexts.count(), 1)
        self.assertEqual(user_contexts[0], user_context)

        other_contexts = Context.objects.filter(user=other_user)
        self.assertEqual(other_contexts.count(), 1)
        self.assertEqual(other_contexts[0], other_context)

    def test_context_ordering_by_name(self) -> None:
        """Test contexts are ordered by name"""
        context_c = Context.objects.create(user=self.user, name="@c")
        context_a = Context.objects.create(user=self.user, name="@a")
        context_b = Context.objects.create(user=self.user, name="@b")

        contexts = Context.objects.filter(user=self.user).order_by("name")
        self.assertEqual(contexts[0], context_a)
        self.assertEqual(contexts[1], context_b)
        self.assertEqual(contexts[2], context_c)

    def test_context_same_name_different_users(self) -> None:
        """Test different users can have contexts with same name"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")

        context1 = Context.objects.create(user=self.user, name="@office")
        context2 = Context.objects.create(user=other_user, name="@office")

        self.assertEqual(context1.name, context2.name)
        self.assertNotEqual(context1.user, context2.user)

    def test_context_cascade_delete(self) -> None:
        """Test that contexts are deleted when user is deleted"""
        Context.objects.create(user=self.user, name="@office")

        self.assertEqual(Context.objects.count(), 1)

        self.user.delete()

        self.assertEqual(Context.objects.count(), 0)

    def test_context_active_filtering(self) -> None:
        """Test filtering active contexts"""
        active_context = Context.objects.create(user=self.user, name="@active")
        inactive_context = Context.objects.create(user=self.user, name="@inactive")
        inactive_context.is_active = False
        inactive_context.save()

        active_contexts = Context.objects.filter(user=self.user, is_active=True)
        self.assertEqual(active_contexts.count(), 1)
        self.assertEqual(active_contexts[0], active_context)

        inactive_contexts = Context.objects.filter(user=self.user, is_active=False)
        self.assertEqual(inactive_contexts.count(), 1)
        self.assertEqual(inactive_contexts[0], inactive_context)


@pytest.mark.integration
class TagModelTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_tag_creation(self) -> None:
        """Test creating a basic tag"""
        tag = Tag.objects.create(user=self.user, name="#urgent", color="#ff0000")
        self.assertEqual(tag.user, self.user)
        self.assertEqual(tag.name, "#urgent")
        self.assertEqual(tag.color, "#ff0000")

    def test_tag_str_method(self) -> None:
        """Test tag string representation"""
        tag = Tag.objects.create(user=self.user, name="#urgent")
        self.assertEqual(str(tag), "#urgent")

    def test_tag_defaults(self) -> None:
        """Test tag default values"""
        tag = Tag.objects.create(user=self.user, name="#important")
        self.assertEqual(tag.color, "#17a2b8")

    def test_tag_with_custom_color(self) -> None:
        """Test tag with custom color"""
        tag = Tag.objects.create(user=self.user, name="#bug", color="#dc3545")
        self.assertEqual(tag.color, "#dc3545")

    def test_tag_user_filtering(self) -> None:
        """Test tags are filtered by user"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")

        user_tag = Tag.objects.create(user=self.user, name="#urgent")
        other_tag = Tag.objects.create(user=other_user, name="#feature")

        user_tags = Tag.objects.filter(user=self.user)
        self.assertEqual(user_tags.count(), 1)
        self.assertEqual(user_tags[0], user_tag)

        other_tags = Tag.objects.filter(user=other_user)
        self.assertEqual(other_tags.count(), 1)
        self.assertEqual(other_tags[0], other_tag)

    def test_tag_ordering_by_name(self) -> None:
        """Test tags are ordered by name"""
        tag_c = Tag.objects.create(user=self.user, name="#c")
        tag_a = Tag.objects.create(user=self.user, name="#a")
        tag_b = Tag.objects.create(user=self.user, name="#b")

        tags = Tag.objects.filter(user=self.user).order_by("name")
        self.assertEqual(tags[0], tag_a)
        self.assertEqual(tags[1], tag_b)
        self.assertEqual(tags[2], tag_c)

    def test_tag_same_name_different_users(self) -> None:
        """Test different users can have tags with same name"""
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="otherpass123")

        tag1 = Tag.objects.create(user=self.user, name="#urgent")
        tag2 = Tag.objects.create(user=other_user, name="#urgent")

        self.assertEqual(tag1.name, tag2.name)
        self.assertNotEqual(tag1.user, tag2.user)

    def test_tag_cascade_delete(self) -> None:
        """Test that tags are deleted when user is deleted"""
        Tag.objects.create(user=self.user, name="#urgent")

        self.assertEqual(Tag.objects.count(), 1)

        self.user.delete()

        self.assertEqual(Tag.objects.count(), 0)

    def test_tag_color_validation(self) -> None:
        """Test tag color format validation (if implemented)"""
        # Valid hex colors
        valid_colors = ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000"]

        for color in valid_colors:
            tag = Tag.objects.create(user=self.user, name=f"#test{color}", color=color)
            self.assertEqual(tag.color, color)

    def test_context_and_tag_relationship(self) -> None:
        """Test that contexts and tags are independent but share user"""
        context = Context.objects.create(user=self.user, name="@office")
        tag = Tag.objects.create(user=self.user, name="#urgent")

        # Both should belong to same user
        self.assertEqual(context.user, tag.user)
        self.assertEqual(context.user, self.user)
        self.assertEqual(tag.user, self.user)

    def test_multiple_contexts_and_tags_per_user(self) -> None:
        """Test creating multiple contexts and tags for single user"""
        contexts = [
            Context.objects.create(user=self.user, name="@office"),
            Context.objects.create(user=self.user, name="@home"),
            Context.objects.create(user=self.user, name="@mobile"),
        ]

        tags = [
            Tag.objects.create(user=self.user, name="#urgent"),
            Tag.objects.create(user=self.user, name="#important"),
            Tag.objects.create(user=self.user, name="#feature"),
        ]

        self.assertEqual(Context.objects.filter(user=self.user).count(), 3)
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 3)

        for context in contexts:
            self.assertEqual(context.user, self.user)

        for tag in tags:
            self.assertEqual(tag.user, self.user)
