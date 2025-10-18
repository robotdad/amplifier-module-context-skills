"""
Skill discovery and metadata parsing.
Shared utilities for finding and parsing SKILL.md files.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Metadata from a SKILL.md file's YAML frontmatter."""

    name: str
    description: str
    path: Path
    version: str | None = None
    license: str | None = None
    metadata: dict[str, Any] | None = None


def parse_skill_frontmatter(skill_path: Path) -> dict[str, Any] | None:
    """
    Parse YAML frontmatter from a SKILL.md file.

    Args:
        skill_path: Path to SKILL.md file

    Returns:
        Dictionary of frontmatter fields, or None if invalid
    """
    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {skill_path}: {e}")
        return None

    # Check for YAML frontmatter (--- ... ---)
    if not content.startswith("---"):
        logger.debug(f"No frontmatter in {skill_path}")
        return None

    # Split on --- markers
    parts = content.split("---", 2)
    if len(parts) < 3:
        logger.debug(f"Incomplete frontmatter in {skill_path}")
        return None

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(parts[1])
        return frontmatter if isinstance(frontmatter, dict) else None
    except yaml.YAMLError as e:
        logger.warning(f"Invalid YAML in {skill_path}: {e}")
        return None


def extract_skill_body(skill_path: Path) -> str | None:
    """
    Extract the markdown body from a SKILL.md file (without frontmatter).

    Args:
        skill_path: Path to SKILL.md file

    Returns:
        Markdown content after frontmatter, or None if invalid
    """
    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {skill_path}: {e}")
        return None

    # Extract body after frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()

    # No frontmatter, return entire content
    return content.strip()


def discover_skills(skills_dir: Path) -> dict[str, SkillMetadata]:
    """
    Discover all skills in a directory.

    Args:
        skills_dir: Directory containing skill subdirectories

    Returns:
        Dictionary mapping skill names to metadata
    """
    skills = {}

    if not skills_dir.exists():
        logger.debug(f"Skills directory does not exist: {skills_dir}")
        return skills

    if not skills_dir.is_dir():
        logger.warning(f"Skills path is not a directory: {skills_dir}")
        return skills

    # Scan for SKILL.md files
    for skill_file in skills_dir.glob("*/SKILL.md"):
        try:
            # Parse frontmatter
            frontmatter = parse_skill_frontmatter(skill_file)
            if not frontmatter:
                logger.debug(f"Skipping {skill_file} - no valid frontmatter")
                continue

            # Extract required fields
            name = frontmatter.get("name")
            description = frontmatter.get("description")

            if not name or not description:
                logger.warning(f"Skipping {skill_file} - missing required fields (name, description)")
                continue

            # Create metadata
            metadata = SkillMetadata(
                name=name,
                description=description,
                path=skill_file,
                version=frontmatter.get("version"),
                license=frontmatter.get("license"),
                metadata=frontmatter.get("metadata"),
            )

            skills[name] = metadata
            logger.debug(f"Discovered skill: {name} at {skill_file}")

        except Exception as e:
            logger.warning(f"Error processing {skill_file}: {e}")
            continue

    logger.info(f"Discovered {len(skills)} skills in {skills_dir}")
    return skills
