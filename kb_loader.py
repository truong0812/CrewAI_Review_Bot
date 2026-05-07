"""Knowledge Base loader for PR Review Bot.

Loads project knowledge from latest.json and formats it for injection
into agent task descriptions.
"""

import json
import os
from typing import Optional


def load_knowledge_base(kb_path: str, max_chars: int = 8000) -> str:
    """Load and format the Knowledge Base for agent context.

    Reads ``latest.json`` from the given KB directory, extracts relevant
    sections (summaries, conventions, risks, dependencies) and returns
    a formatted markdown string ready to inject into task descriptions.

    Args:
        kb_path: Path to the KB directory containing ``latest.json``.
        max_chars: Maximum characters for the output (default 8000).

    Returns:
        Formatted markdown string with KB context, or empty string if
        KB cannot be loaded.
    """
    if not kb_path:
        return ""

    latest_path = os.path.join(kb_path, "latest.json")
    if not os.path.isfile(latest_path):
        print(f"⚠️ KB file not found: {latest_path}")
        return ""

    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ Failed to load KB: {e}")
        return ""

    # Build lookup maps
    file_map = {f["file_id"]: f["path"] for f in data.get("files", [])}
    module_map = {m["module_id"]: m["name"] for m in data.get("modules", [])}

    sections = []

    # --- File Summaries (file-level only) ---
    summaries_section = _build_summaries(data.get("summaries", []), file_map)
    if summaries_section:
        sections.append(summaries_section)

    # --- Coding Conventions ---
    conventions_section = _build_conventions(data.get("conventions", []))
    if conventions_section:
        sections.append(conventions_section)

    # --- Risk Areas ---
    risks_section = _build_risks(data.get("risks", []))
    if risks_section:
        sections.append(risks_section)

    # --- Module Dependencies ---
    deps_section = _build_dependencies(data.get("relations", []), file_map, module_map)
    if deps_section:
        sections.append(deps_section)

    if not sections:
        return ""

    # Combine and truncate
    result = "## Project Knowledge Base\n\n" + "\n\n".join(sections)

    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n... (KB truncated to fit context limit)"

    return result


def _build_summaries(summaries: list, file_map: dict) -> str:
    """Build File Summaries section from KB data."""
    file_summaries = []
    for s in summaries:
        if s.get("level") != "file" or s.get("target_type") != "file":
            continue
        file_path = file_map.get(s["target_id"], "unknown")
        # Skip KB internal files
        if "knowledge_base/" in file_path:
            continue
        content = s.get("content", "").strip()
        if content:
            file_summaries.append(f"- **{file_path}**: {content}")

    if not file_summaries:
        return ""

    return "### File Summaries\n" + "\n".join(file_summaries)


def _build_conventions(conventions: list) -> str:
    """Build Coding Conventions section from KB data."""
    items = []
    for c in conventions:
        name = c.get("name", "")
        desc = c.get("description", "")
        if name and desc:
            items.append(f"- **{name}**: {desc}")

    if not items:
        return ""

    return "### Coding Conventions\n" + "\n".join(items)


def _build_risks(risks: list) -> str:
    """Build Risk Areas section from KB data."""
    items = []
    for r in risks:
        name = r.get("name", "")
        severity = r.get("severity", "unknown").upper()
        file_path = r.get("file_path", "")
        if name:
            label = f"**{name}**"
            if file_path:
                label += f" in `{file_path}`"
            label += f" ({severity})"
            items.append(f"- {label}")

    if not items:
        return ""

    return "### Risk Areas\n" + "\n".join(items)


def _build_dependencies(relations: list, file_map: dict, module_map: dict) -> str:
    """Build Module Dependencies section from KB relations."""
    deps = []
    for rel in relations:
        rel_type = rel.get("relation_type", "")
        if rel_type not in ("imports", "depends_on"):
            continue
        source_type = rel.get("source_type", "")
        target_type = rel.get("target_type", "")

        # File-level dependencies only
        if source_type == "File" and target_type == "File":
            source = file_map.get(rel["source_id"], "unknown")
            target = file_map.get(rel["target_id"], "unknown")
            # Skip KB internal references
            if "knowledge_base/" in source or "knowledge_base/" in target:
                continue
            arrow = "→" if rel_type == "imports" else "→ (depends on)"
            deps.append(f"- `{source}` {arrow} `{target}`")

    if not deps:
        return ""

    return "### Module Dependencies\n" + "\n".join(deps)