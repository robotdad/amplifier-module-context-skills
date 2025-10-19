"""Tests for skills loading limits."""

from pathlib import Path

import pytest
from amplifier_module_context_skills import SkillsContext
from test_context import MockBaseContext


@pytest.mark.asyncio
async def test_can_load_skill_under_threshold():
    """Test can_load_skill returns True when under threshold."""
    base = MockBaseContext()
    context = SkillsContext(base, [Path("/nonexistent")], auto_inject_metadata=False)

    # No skills loaded yet
    can_load, warning = context.can_load_skill()
    assert can_load is True
    assert warning is None


@pytest.mark.asyncio
async def test_can_load_skill_at_warning_threshold():
    """Test can_load_skill warns at threshold."""
    base = MockBaseContext()
    context = SkillsContext(base, [Path("/nonexistent")], auto_inject_metadata=False)

    # Load skills up to warning threshold (3)
    context.mark_skill_loaded("skill1")
    context.mark_skill_loaded("skill2")
    context.mark_skill_loaded("skill3")

    can_load, warning = context.can_load_skill()
    assert can_load is True
    assert warning is not None
    assert "Warning" in warning
    assert "3" in warning


@pytest.mark.asyncio
async def test_can_load_skill_at_max():
    """Test can_load_skill blocks at maximum."""
    base = MockBaseContext()
    context = SkillsContext(base, [Path("/nonexistent")], auto_inject_metadata=False)

    # Load maximum skills (5)
    for i in range(5):
        context.mark_skill_loaded(f"skill{i}")

    can_load, error_msg = context.can_load_skill()
    assert can_load is False
    assert error_msg is not None
    assert "Maximum" in error_msg
    assert "5" in error_msg


@pytest.mark.asyncio
async def test_mark_skill_loaded_incremental():
    """Test that marking skills loaded increments count correctly."""
    base = MockBaseContext()
    context = SkillsContext(base, [Path("/nonexistent")], auto_inject_metadata=False)

    assert len(context.loaded_skills) == 0

    context.mark_skill_loaded("skill1")
    assert len(context.loaded_skills) == 1

    context.mark_skill_loaded("skill2")
    assert len(context.loaded_skills) == 2

    # Loading same skill again doesn't increase count (set behavior)
    context.mark_skill_loaded("skill1")
    assert len(context.loaded_skills) == 2


@pytest.mark.asyncio
async def test_clear_resets_loaded_skills():
    """Test that clearing context resets loaded skills tracking."""
    base = MockBaseContext()
    context = SkillsContext(base, [Path("/nonexistent")], auto_inject_metadata=False)

    # Load some skills
    context.mark_skill_loaded("skill1")
    context.mark_skill_loaded("skill2")
    assert len(context.loaded_skills) == 2

    # Clear context
    await context.clear()

    # Should reset loaded skills
    assert len(context.loaded_skills) == 0
    can_load, warning = context.can_load_skill()
    assert can_load is True
    assert warning is None
