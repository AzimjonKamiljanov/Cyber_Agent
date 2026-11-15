#!/usr/bin/env python3
"""
Customization pack validator for Cyber Agent.
Verifies rules and skills conform to Antigravity specifications.
"""

import sys
from pathlib import Path


def parse_frontmatter(content: str) -> dict[str, str] | None:
    """Extract simple key-value YAML frontmatter."""
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    fm_text = parts[1]
    data: dict[str, str] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            data[key] = val
    return data


def validate_rules(rules_dir: Path) -> list[str]:
    errors: list[str] = []
    if not rules_dir.exists() or not rules_dir.is_dir():
        return [f"Rules directory does not exist: {rules_dir}"]

    valid_triggers = {"always_on", "model_decision", "glob", "manual"}

    for item in rules_dir.iterdir():
        if item.is_dir():
            errors.append(f"Rules directory must be flat, found subdirectory: {item.name}")
            continue

        if not item.name.endswith(".md"):
            errors.append(f"Non-markdown file in rules directory: {item.name}")
            continue

        size = item.stat().st_size
        if size >= 24000:
            errors.append(f"Rule file {item.name} exceeds 24,000 bytes ({size} bytes)")

        try:
            content = item.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            errors.append(f"Could not read {item.name}: {e}")
            continue

        fm = parse_frontmatter(content)
        if fm is None:
            errors.append(f"Rule file {item.name} missing or invalid YAML frontmatter")
            continue

        trigger = fm.get("trigger")
        if not trigger:
            errors.append(f"Rule file {item.name} missing 'trigger' in frontmatter")
        elif trigger not in valid_triggers:
            errors.append(f"Rule file {item.name} has invalid trigger '{trigger}' (must be one of {valid_triggers})")

        if trigger == "model_decision" and not fm.get("description"):
            errors.append(f"Rule file {item.name} (trigger: model_decision) missing 'description'")

        if trigger == "glob" and not fm.get("globs"):
            errors.append(f"Rule file {item.name} (trigger: glob) missing 'globs'")

    return errors


def validate_skills(skills_dir: Path) -> list[str]:
    errors: list[str] = []
    if not skills_dir.exists() or not skills_dir.is_dir():
        return [f"Skills directory does not exist: {skills_dir}"]

    skill_folders = [p for p in skills_dir.iterdir() if p.is_dir()]
    if not skill_folders:
        return [f"No skill folders found in: {skills_dir}"]

    for skill_path in skill_folders:
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"Skill directory {skill_path.name} missing SKILL.md")
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            errors.append(f"Could not read {skill_file}: {e}")
            continue

        fm = parse_frontmatter(content)
        if fm is None:
            errors.append(f"{skill_file} missing or invalid YAML frontmatter")
            continue

        if not fm.get("description"):
            errors.append(f"{skill_file} missing 'description' in frontmatter")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    agents_md = repo_root / "AGENTS.md"
    rules_dir = repo_root / ".agents" / "rules"
    skills_dir = repo_root / ".agents" / "skills"

    all_errors: list[str] = []

    if not agents_md.exists():
        all_errors.append("AGENTS.md missing in repository root")

    all_errors.extend(validate_rules(rules_dir))
    all_errors.extend(validate_skills(skills_dir))

    if all_errors:
        print("FAIL: Customization validation failed with errors:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("OK: All rules and skills passed customization verification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
