"""Tests for skills-aware context."""

from pathlib import Path

import pytest
from amplifier_module_context_skills import SkillsContext


class MockBaseContext:
    """Mock base context for testing."""

    def __init__(self: "MockBaseContext") -> None:
        """Initialize mock context."""
        self.messages: list[dict] = []

    async def add_message(self: "MockBaseContext", message: dict) -> None:
        """Add message to context."""
        self.messages.append(message)

    async def get_messages(self: "MockBaseContext") -> list[dict]:
        """Get all messages."""
        return self.messages.copy()

    async def should_compact(self: "MockBaseContext") -> bool:
        """Check if should compact."""
        return False

    async def compact(self: "MockBaseContext") -> None:
        """Compact context."""
        # Mock implementation - no actual compaction needed
        return

    async def clear(self: "MockBaseContext") -> None:
        """Clear context."""
        self.messages.clear()


@pytest.mark.asyncio
async def test_skills_context_initialization():
    """Test initializing skills context."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"

    if not fixtures_dir.exists():
        pytest.skip("Fixtures directory not found")

    base = MockBaseContext()
    context = SkillsContext(base, fixtures_dir, auto_inject_metadata=False)

    assert len(context.skills) >= 1
    assert len(context.loaded_skills) == 0


@pytest.mark.asyncio
async def test_get_skills_metadata():
    """Test generating skills metadata string."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"

    if not fixtures_dir.exists():
        pytest.skip("Fixtures directory not found")

    base = MockBaseContext()
    context = SkillsContext(base, fixtures_dir, auto_inject_metadata=False)

    metadata = context.get_skills_metadata()

    assert "Available Skills" in metadata
    assert "load_skill tool" in metadata


@pytest.mark.asyncio
async def test_get_available_skills():
    """Test getting list of skill names."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "skills"

    if not fixtures_dir.exists():
        pytest.skip("Fixtures directory not found")

    base = MockBaseContext()
    context = SkillsContext(base, fixtures_dir, auto_inject_metadata=False)

    skills = context.get_available_skills()

    assert isinstance(skills, list)
    assert len(skills) >= 1


@pytest.mark.asyncio
async def test_skill_loaded_tracking():
    """Test tracking which skills are loaded."""
    base = MockBaseContext()
    context = SkillsContext(base, Path("/nonexistent"), auto_inject_metadata=False)

    assert not context.is_skill_loaded("test-skill")

    context.mark_skill_loaded("test-skill")

    assert context.is_skill_loaded("test-skill")


@pytest.mark.asyncio
async def test_context_delegation():
    """Test that context methods delegate to base."""
    base = MockBaseContext()
    context = SkillsContext(base, Path("/nonexistent"), auto_inject_metadata=False)

    # Test add_message
    await context.add_message({"role": "user", "content": "test"})
    messages = await context.get_messages()

    assert len(messages) == 1
    assert messages[0]["content"] == "test"

    # Test clear
    await context.clear()
    messages = await context.get_messages()

    assert len(messages) == 0
    assert len(context.loaded_skills) == 0


@pytest.mark.asyncio
async def test_empty_skills_directory():
    """Test with no skills available."""
    base = MockBaseContext()
    context = SkillsContext(base, Path("/nonexistent"), auto_inject_metadata=False)

    assert len(context.skills) == 0
    assert context.get_skills_metadata() == ""
    assert context.get_available_skills() == []
