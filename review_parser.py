"""Parse Tech Lead review output into inline comment dicts for GitHub API."""

import logging
import re
from typing import Optional

logger = logging.getLogger("pr-review-bot.review_parser")


def parse_inline_comments(review_text: str, pr_files: list[dict]) -> list[dict]:
    """Extract inline comments from review text, mapping file:line to diff positions.

    Args:
        review_text: The Tech Lead's review output.
        pr_files: List of PR file dicts from GitHub API (with 'filename' and 'patch' keys).

    Returns:
        List of dicts with keys: path, position, body. Max 20 comments.
    """
    # Build diff position maps for each file
    file_maps = {}
    for f in pr_files:
        filename = f.get("filename", "")
        patch = f.get("patch", "")
        if patch:
            file_maps[filename] = _build_line_to_position_map(patch)

    comments = []
    blocks = _extract_issue_blocks(review_text)

    for block in blocks:
        file_ref = block.get("file")
        line_num = block.get("line")
        body = block.get("body", "").strip()

        if not file_ref or not line_num or not body:
            continue

        position = _resolve_position(file_ref, line_num, file_maps)
        if position is None:
            logger.debug(
                f"Could not resolve position for {file_ref}:{line_num}, skipping"
            )
            continue

        comments.append({
            "path": file_ref,
            "position": position,
            "body": body,
        })

        if len(comments) >= 20:
            break

    return comments


def _extract_issue_blocks(review_text: str) -> list[dict]:
    """Extract structured issue blocks from the review text.

    Matches the Tech Lead output format:
        1. **[Title]** (`path/to/file.py:42`)
           body text...
    """
    blocks = []

    # Pattern 1: Tech Lead numbered blocking issues
    # e.g., 1. **Title** (`file.ts:42`) followed by body
    numbered = re.compile(
        r"\d+\.\s+\*\*([^*]+)\*\*\s*\(?`([^`]+?):(\d+)`\)?"  # 1. **Title** (`file:line`) or (`file:line`)
        r"\s*\n((?:(?!\d+\.\s+\*\*).)+)",                      # body until next numbered item
        re.DOTALL,
    )
    for m in numbered.finditer(review_text):
        title = m.group(1).strip()
        file_path = m.group(2).strip()
        line_num = int(m.group(3))
        body_text = m.group(4).strip()
        body = f"**{title}**\n\n{body_text}" if title else body_text
        blocks.append({"file": file_path, "line": line_num, "body": body})

    if blocks:
        return blocks

    # Pattern 2: Agent output format - **File:** `path` + **Line:** N
    file_pattern = re.compile(r"\*\*\s*File:\s*\*\*\s*`([^`]+)`")
    line_pattern = re.compile(r"\*\*\s*Line:\s*\*\*\s*(\d+)")

    file_matches = list(file_pattern.finditer(review_text))
    line_matches = list(line_pattern.finditer(review_text))

    for fm, lm in zip(file_matches, line_matches):
        file_path = fm.group(1).strip()
        line_num = int(lm.group(1))

        body_start = lm.end()
        next_file = file_pattern.search(review_text, fm.end() + 1)
        body_end = next_file.start() if next_file else len(review_text)
        body_text = review_text[body_start:body_end].strip()

        if len(body_text) > 500:
            body_text = body_text[:500] + "..."

        blocks.append({"file": file_path, "line": line_num, "body": body_text})

    return blocks


def _build_line_to_position_map(patch: str) -> dict[int, int]:
    """Parse unified diff to map file line numbers to diff positions.

    GitHub's review API uses `position`: the 1-based index of the line in the diff,
    counting every line (hunk headers, +, -, context, no-newline markers).

    Returns:
        Dict mapping file_line -> diff_position.
    """
    line_map = {}
    position = 0
    current_line = 0

    for line in patch.split("\n"):
        # Hunk header: @@ -a,b +c,d @@
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            position += 1
            continue

        position += 1

        if line.startswith("+"):
            line_map[current_line] = position
            current_line += 1
        elif line.startswith("-"):
            pass  # removed line, don't advance current_line
        else:
            # Context line (no prefix or space prefix)
            line_map[current_line] = position
            current_line += 1

    return line_map


def _resolve_position(
    file_path: str,
    line_num: int,
    file_maps: dict[str, dict[int, int]],
    nearby_range: int = 5,
) -> Optional[int]:
    """Resolve a file:line reference to a diff position.

    Tries exact match first, then nearby lines (+/- nearby_range).
    Falls back to fuzzy file path matching (case-insensitive, basename match).
    """
    line_map = file_maps.get(file_path)

    # Fuzzy fallback: try case-insensitive match, then basename match.
    # Basename match is skipped when multiple files share the same name
    # to avoid mapping to the wrong file (e.g., src/utils.py vs test/utils.py).
    if not line_map:
        lower_path = file_path.lower()
        for mapped_path in file_maps:
            if mapped_path.lower() == lower_path:
                line_map = file_maps[mapped_path]
                break
        if not line_map:
            basename = file_path.rsplit("/", 1)[-1].lower()
            matches = [
                file_maps[p] for p in file_maps
                if p.rsplit("/", 1)[-1].lower() == basename
            ]
            if len(matches) == 1:
                line_map = matches[0]

    if not line_map:
        return None

    if line_num in line_map:
        return line_map[line_num]

    for offset in range(1, nearby_range + 1):
        for candidate in [line_num - offset, line_num + offset]:
            if candidate in line_map:
                return line_map[candidate]

    return None
