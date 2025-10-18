# Amplifier Skills Context Module

Context manager with progressive skills loading and metadata injection.

## Prerequisites

- **Python 3.11+**
- **[UV](https://github.com/astral-sh/uv)** - Fast Python package manager

### Installing UV

```bash
# macOS/Linux/WSL
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Purpose

Extends context management with automatic skills discovery and metadata injection. Provides agents with awareness of available skills without loading full content until needed (progressive disclosure).

**Key benefit:** Agents see what skills are available (~100 tokens) without loading full content (~1-5k tokens per skill) until explicitly needed.

## Contract

**Module Type:** Context
**Mount Point:** `context`
**Entry Point:** `amplifier_module_context_skills:mount`

## Behavior

- Discovers skills from `.amplifier/skills/` directory on initialization
- Optionally injects skills metadata into system instruction (~100 tokens total)
- Tracks loaded skills to prevent redundant loading
- Wraps any base context manager (context-simple, context-persistent, etc.)
- Delegates all standard context operations to base

## Configuration

```yaml
session:
  context: context-skills
  config:
    base_context: context-simple      # Which context to wrap
    skills_dir: .amplifier/skills     # Where to find skills
    auto_inject_metadata: true        # Add metadata to system instruction
```

## How It Works

### Session Start

1. **Discovery**: Scans `skills_dir` for `*/SKILL.md` files
2. **Parsing**: Extracts YAML frontmatter (name, description, metadata)
3. **Indexing**: Builds skills registry
4. **Injection** (if enabled): Adds metadata to system instruction

**Token cost:** ~100 tokens for 3 skills metadata

### During Execution

1. **Agent sees**: Skills list in system instruction
2. **Agent calls**: `load_skill(skill_name="...")` via tool
3. **Context tracks**: Marks skill as loaded
4. **Prevents**: Redundant loading of same skill

### Progressive Disclosure

```
Startup: 100 tokens (metadata for all skills)
On-demand: +2000 tokens (one skill loaded)
As-needed: +0 tokens (references read directly)

Total: 2100 tokens vs 6000 tokens (60% savings)
```

## Integration with tool-skills

Works seamlessly with `amplifier-module-tool-skills`:

```yaml
session:
  context: context-skills  # Provides discovery

tools:
  - module: tool-skills    # Provides loading
```

**Complete workflow:**

1. **Context**: Injects skills list into system instruction
2. **Agent**: Sees available skills automatically
3. **Tool**: Agent explicitly loads when needed
4. **Context**: Tracks loaded skills

## Context Wrapper Pattern

Skills-context **wraps** any base context:

```python
# Wraps context-simple
session:
  context: context-skills
  config:
    base_context: context-simple

# Wraps context-persistent
session:
  context: context-skills
  config:
    base_context: context-persistent
```

**Delegation:** All standard context methods delegate to base:
- `add_message()` → base.add_message()
- `get_messages()` → base.get_messages()
- `should_compact()` → base.should_compact()
- `compact()` → base.compact()
- `clear()` → base.clear() + clear loaded skills

## Usage Examples

### In Profile Configuration

```yaml
---
profile:
  name: with-skills
  extends: dev

session:
  context: context-skills
  config:
    base_context: context-simple
    skills_dir: .amplifier/skills
    auto_inject_metadata: true

tools:
  - module: tool-filesystem
  - module: tool-bash
  - module: tool-skills
    config:
      skills_dir: .amplifier/skills
---
```

### Skills Metadata Injection

When `auto_inject_metadata: true`:

```
System instruction includes:

## Available Skills

**amplifier-philosophy**: Design philosophy using Linux kernel metaphor...
**python-standards**: Python coding standards including type hints...
**module-development**: Guide for creating new modules...

To access full content, use the load_skill tool.
```

**Token cost:** ~100 tokens (vs 6000+ if all content loaded)

### Agent Experience

```
Agent starts session:
- Sees skills list in system instruction (automatic)
- Knows what expertise is available
- Can reference by name: "following python-standards skill"

Agent needs details:
- Calls load_skill(skill_name="python-standards")
- Receives full content
- Context marks as loaded
- Second load returns "already loaded" (prevents waste)
```

## API for Skills Awareness

Context provides skills-specific methods:

```python
# Get list of available skills
skills: list[str] = context.get_available_skills()
# Returns: ["amplifier-philosophy", "python-standards", ...]

# Check if skill is loaded
loaded: bool = context.is_skill_loaded("python-standards")
# Returns: True if already loaded

# Mark skill as loaded (called by tool)
context.mark_skill_loaded("python-standards")

# Get formatted metadata
metadata: str = context.get_skills_metadata()
# Returns: Formatted string for system instruction
```

## Skills Directory Locations

**Standard locations** (future multi-source support):

```
1. .amplifier/skills/          # Project skills (git-shared)
2. ~/.amplifier/skills/         # User skills (personal)
3. {app}/data/skills/          # Bundled skills (built-in)
```

**Current MVP:** Single directory from config

## Testing

```bash
# Run unit tests
make test

# Run specific test
uv run pytest tests/test_context.py::test_skills_context_initialization -v
```

## Development

```bash
# Install dependencies
make install

# Format and check code
make check

# Run all tests
make test
```

## Dependencies

- `amplifier-core` - Core protocols and types
- `pyyaml>=6.0` - YAML parsing

## Contributing

See main Amplifier repository for contribution guidelines.

## License

MIT

