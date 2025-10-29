"""
Amplifier context manager with progressive skills loading.
Provides automatic skills discovery and metadata injection.
"""

import logging
from pathlib import Path
from typing import Any

from amplifier_module_context_skills.discovery import SkillMetadata
from amplifier_module_context_skills.discovery import discover_skills
from amplifier_module_context_skills.discovery import discover_skills_multi_source
from amplifier_module_context_skills.discovery import get_default_skills_dirs

logger = logging.getLogger(__name__)


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> Any:
    """
    Mount the skills-aware context manager.

    Args:
        coordinator: Module coordinator
        config: Context configuration

    Returns:
        SkillsContext instance
    """
    config = config or {}

    # Determine base context to wrap
    base_context_name = config.get("base_context", "context-simple")
    base_context_source = config.get("base_context_source")
    base_context_config = config.get("base_context_config", {})

    # Load base context via coordinator
    base_context = coordinator.get("context")
    if base_context is None:
        # If no context mounted yet, we need to mount the base first
        # Use the coordinator's loader to load base context (supports git sources)
        loader = coordinator.loader

        logger.info(f"Loading base context '{base_context_name}' with source: {base_context_source}")

        try:
            # Load base context using loader (handles git sources properly)
            base_mount_fn = await loader.load(
                base_context_name, base_context_config, profile_source=base_context_source
            )

            if base_mount_fn is None:
                raise ValueError(f"Base context '{base_context_name}' not found")

            # Mount base context
            cleanup = await base_mount_fn(coordinator)
            if cleanup:
                coordinator.register_cleanup(cleanup)

            base_context = coordinator.get("context")

        except Exception as e:
            raise ValueError(f"Failed to load base context '{base_context_name}': {e}") from e

    # Create skills wrapper around base context
    auto_inject = config.get("auto_inject_metadata", True)

    logger.info(f"Mounting SkillsContext with config: {config}")

    # Read skills directories from config
    if "skills_dirs" in config:
        skills_dirs = config["skills_dirs"]
        if isinstance(skills_dirs, str):
            skills_dirs = [skills_dirs]
        skills_dirs = [Path(d).expanduser() for d in skills_dirs]
    elif "skills_dir" in config:
        skills_dirs = [Path(config["skills_dir"]).expanduser()]
    else:
        skills_dirs = get_default_skills_dirs()

    logger.info(f"Using skills directories: {skills_dirs}")

    logger.info(f"Using skills directories: {skills_dirs}")
    context = SkillsContext(base_context, skills_dirs, auto_inject)
    logger.info(f"Mounted SkillsContext wrapping {base_context.__class__.__name__} with {len(context.skills)} skills")

    # Register capabilities for tool-skills to use
    coordinator.register_capability("skills.registry", context.skills)
    coordinator.register_capability("skills.directories", skills_dirs)
    logger.info(f"Registered skills capabilities: {len(context.skills)} skills from {len(skills_dirs)} directories")

    # Emit discovery event
    await coordinator.hooks.emit(
        "skills:discovered",
        {
            "skill_count": len(context.skills),
            "skill_names": list(context.skills.keys()),
            "sources": [str(d) for d in skills_dirs],
        },
    )

    return context


class SkillsContext:
    """
    Context manager with progressive skills loading.

    Wraps a base context manager and adds skills awareness.
    """

    def __init__(
        self: "SkillsContext", base_context: Any, skills_dirs: list[Path], auto_inject_metadata: bool = True
    ) -> None:
        """
        Initialize skills-aware context.

        Args:
            base_context: Base context manager to wrap
            skills_dirs: List of directories containing skills (priority order)
            auto_inject_metadata: If True, inject skills metadata into system instruction
        """
        self.base = base_context
        self.skills_dirs = skills_dirs
        self.auto_inject_metadata = auto_inject_metadata

        # Discover skills from all sources
        self.skills: dict[str, SkillMetadata] = discover_skills_multi_source(skills_dirs)
        self.loaded_skills: set[str] = set()
        self.max_loaded_skills = 5  # Hard limit to prevent token runaway
        self.warn_threshold = 3  # Warn when approaching limit

        logger.info(f"Initialized SkillsContext with {len(self.skills)} skills from {len(skills_dirs)} sources")

    def get_skills_metadata(self: "SkillsContext") -> str:
        """
        Generate formatted skills metadata for system instruction.

        Returns:
            Formatted string listing available skills
        """
        if not self.skills:
            return ""

        lines = ["## Available Skills", ""]
        for name, metadata in sorted(self.skills.items()):
            lines.append(f"**{name}**: {metadata.description}")

        lines.extend(["", "To access full skill content, use the load_skill tool.", ""])

        return "\n".join(lines)

    def get_available_skills(self: "SkillsContext") -> list[str]:
        """
        Get list of available skill names.

        Returns:
            List of skill names
        """
        return list(self.skills.keys())

    def is_skill_loaded(self: "SkillsContext", skill_name: str) -> bool:
        """
        Check if a skill is already loaded.

        Args:
            skill_name: Name of skill to check

        Returns:
            True if skill is loaded
        """
        return skill_name in self.loaded_skills

    def can_load_skill(self: "SkillsContext") -> tuple[bool, str | None]:
        """
        Check if it's safe to load another skill.

        Returns:
            Tuple of (can_load, warning_message)
        """
        loaded_count = len(self.loaded_skills)

        if loaded_count >= self.max_loaded_skills:
            return (
                False,
                f"Maximum {self.max_loaded_skills} skills loaded. Consider clearing context or being more selective.",
            )

        if loaded_count >= self.warn_threshold:
            return (
                True,
                f"Warning: {loaded_count} skills already loaded. Approaching limit of {self.max_loaded_skills}.",
            )

        return (True, None)

    def mark_skill_loaded(self: "SkillsContext", skill_name: str) -> None:
        """
        Mark a skill as loaded.

        Args:
            skill_name: Name of skill that was loaded
        """
        self.loaded_skills.add(skill_name)
        loaded_count = len(self.loaded_skills)

        logger.debug(f"Marked skill as loaded: {skill_name} ({loaded_count}/{self.max_loaded_skills})")

        # Warn when approaching limit
        if loaded_count == self.warn_threshold:
            logger.warning(
                f"Skills context: {loaded_count} skills loaded. Approaching limit of {self.max_loaded_skills}."
            )
        elif loaded_count >= self.max_loaded_skills:
            logger.warning(
                f"Skills context: Maximum {self.max_loaded_skills} skills loaded. Consider clearing context."
            )

    # Context protocol implementation - delegate to base
    async def add_message(self: "SkillsContext", message: dict[str, Any]) -> None:
        """Add a message to the context."""
        await self.base.add_message(message)

    async def get_messages(self: "SkillsContext") -> list[dict[str, Any]]:
        """Get all messages in the context."""
        return await self.base.get_messages()

    async def should_compact(self: "SkillsContext") -> bool:
        """Check if context should be compacted."""
        return await self.base.should_compact()

    async def compact(self: "SkillsContext") -> None:
        """Compact the context to reduce size."""
        await self.base.compact()

    async def clear(self: "SkillsContext") -> None:
        """Clear all messages."""
        await self.base.clear()
        self.loaded_skills.clear()

    async def set_messages(self: "SkillsContext", messages: list[dict[str, Any]]) -> None:
        """Set messages (for session resume)."""
        if hasattr(self.base, "set_messages"):
            await self.base.set_messages(messages)
