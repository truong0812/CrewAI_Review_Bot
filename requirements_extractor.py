"""Extract structured requirements from PR title and body."""

import re


def extract_requirements(pr_title: str, pr_body: str) -> str:
    """Parse PR description into structured requirements.

    Extracts:
    - Markdown checkboxes: - [ ] task, - [x] done
    - Acceptance criteria sections
    - Fixes/Closes issue references

    Args:
        pr_title: The PR title.
        pr_body: The PR description/body.

    Returns:
        Formatted requirements string, empty if none found.
    """
    if not pr_body:
        return ""

    sections = []
    lines = pr_body.split("\n")

    # Extract checkboxes
    checkboxes = _extract_checkboxes(lines)
    if checkboxes:
        sections.append("### From PR Description\n" + "\n".join(checkboxes))

    # Extract acceptance criteria from specific sections
    criteria = _extract_acceptance_criteria(lines)
    if criteria:
        sections.append("### Acceptance Criteria\n" + "\n".join(criteria))

    # Extract issue references
    refs = _extract_issue_refs(pr_body)
    if refs:
        sections.append("### Linked Issues\n" + "\n".join(refs))

    if not sections:
        # If no structured content, use the whole body as context
        trimmed = pr_body.strip()
        if len(trimmed) > 500:
            trimmed = trimmed[:500] + "..."
        if trimmed:
            sections.append("### PR Description\n" + trimmed)

    return "## PR Requirements\n\n" + "\n\n".join(sections) + "\n"


def _extract_checkboxes(lines: list[str]) -> list[str]:
    """Extract markdown checkbox items."""
    items = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+\[[ xX]\]\s+", stripped):
            items.append(stripped)
    return items


def _extract_acceptance_criteria(lines: list[str]) -> list[str]:
    """Extract items from Acceptance Criteria / Requirements / Checklist sections."""
    criteria_headers = {
        "acceptance criteria", "requirements", "checklist",
        "criteria", "definition of done",
    }
    items = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        # Check if this is a section header
        header_match = re.match(r"^#{1,4}\s+(.+)$", stripped)
        if header_match:
            header_text = header_match.group(1).lower()
            in_section = header_text in criteria_headers
            continue

        # Check for underline-style headers
        if stripped and all(c in "=-" for c in stripped):
            continue

        # End section at next header
        if stripped.startswith("#"):
            in_section = False
            continue

        if in_section and stripped:
            items.append(stripped)

    return items


def _extract_issue_refs(body: str) -> list[str]:
    """Extract Fixes #N / Closes #N references."""
    refs = []
    seen = set()
    for match in re.finditer(r"(?:fixes|closes|resolves)\s+#(\d+)", body, re.IGNORECASE):
        num = match.group(1)
        if num not in seen:
            seen.add(num)
            refs.append(f"- #{num}")
    return refs
