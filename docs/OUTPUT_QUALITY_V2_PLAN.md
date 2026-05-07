# 🚀 Plan Cải Thiện Chất Lượng Output V2

> **Status:** 📝 Chờ triển khai
> **Created:** 2026-05-07
> **Updated:** 2026-05-07 (Added Testing Strategy, Error Handling, Performance Optimization)
> **Based on:** Phân tích toàn bộ codebase hiện tại

---

## 📊 Phân tích hiện trạng

### ✅ Điểm mạnh (đã implement)
- 4 agents sequential pipeline (Code Review → Security → Performance → Tech Lead)
- Anti-false-positive instructions trong agent backstories
- KB loader với priority ordering & schema validation
- Fallback chain: submit_review → post_comment → save local
- File prioritization (source code trước, skip irrelevant files)

### ❌ Vấn đề còn tồn tại

| # | Vấn đề | Mức độ | File ảnh hưởng |
|---|--------|--------|----------------|
| 1 | **Context window quá nhỏ** — `max_chars=8000` default, PR lớn bị truncate mất files quan trọng | 🔴 HIGH | `client.py`, `settings.py` |
| 2 | **Tech Lead nhận raw free-text** — không có structured format từ 3 reviewers → khó parse, dễ miss findings | 🔴 HIGH | `tasks/tasks.py` |
| 3 | **Agents chạy độc lập, không share context** — Security Expert không biết Code Reviewer đã tìm gì → duplicate findings | 🟡 MEDIUM | `main.py`, `tasks/tasks.py` |
| 4 | **Output formatting không nhất quán** — mỗi lần chạy format khác nhau, đôi khi thiếu table hoặc verdict | 🟡 MEDIUM | `tasks/tasks.py` |
| 5 | **Không tận dụng PR metadata** — không xem PR size, changed files count để điều chỉnh review depth | 🟡 MEDIUM | `client.py`, `main.py` |
| 6 | **Review chỉ post 1 body comment lớn** — không có inline comments trên từng dòng code cụ thể | 🟢 LOW | `client.py`, `main.py` |
| 7 | **Missing testing framework** — không có unit/integration tests để validate changes | 🔴 HIGH | All files |
| 8 | **Poor error handling** — retry, fallback strategies khi API fail | 🔴 HIGH | `main.py`, `github_utils/client.py` |
| 9 | **No performance throttling** — large PRs có thể timeout hoặc exceed limits | 🟡 MEDIUM | `main.py`, `config/settings.py` |

---

## 🏗️ Plan Triển Khai — 8 Phases

### Priority Order (Impact cao → thấp)

```
Phase 0 (Testing Framework)    ████████████  Foundation for all changes
Phase 2 (Structured Output)     ████████████  Impact cao nhất, dễ nhất
Phase 8 (Basic Metrics)        ██████████    Measure success of other phases
Phase 3 (Context Passing)       █████████     Giảm duplicate findings
Phase 5 (Enhanced Tech Lead)    ████████      Cải thiện synthesis
Phase 1 (Dynamic Context)       ███████       Fix truncate issue
Phase 4 (PR Metadata)           ██████        Context-aware reviews
Phase 6 (Post-Processing)       █████         Ensure consistent output
Phase 7 (Inline Comments)       ████          UX improvement
Phase 9 (Documentation)         ███           Developer experience
```

---

## Phase 0: Testing Framework (MUST-DO trước triển khai)

**Mục tiêu:** Build comprehensive test suite để validate các changes trong các phases sau

**Files cần tạo:**
- `tests/` directory
- `tests/test_agents.py`
- `tests/test_tasks.py`
- `tests/test_client.py`
- `tests/test_main.py`
- `tests/test_output_quality.py`

### 0.1 Unit Tests

**test_output_quality.py**
```python
import pytest
from tasks.tasks import validate_output_format

def test_structured_output_validation():
    """Test structured output format compliance."""
    valid_output = """
## Code Quality Review
### Issue 1: Unused Import
- **File:** `main.py`
- **Line:** 10
- **Severity:** MINOR
- **Category:** style
- **Code:**
  ```python
  import unused_module
  ```
- **Problem:** Unused import
- **Suggested Fix:**
  ```python
  # Remove unused import
  ```
"""
    assert validate_output_format(valid_output, "code_quality") == True
    
    invalid_output = "Some random text without structure"
    assert validate_output_format(invalid_output, "code_quality") == False
```

**test_client.py**
```python
def test_github_client_retry():
    """Test retry mechanism for API failures."""
    from github_utils.client import GitHubClient
    
    client = GitHubClient()
    
    # Test with mock failure
    with pytest.raises(Exception):
        client.get_pr_metadata("owner", "repo", 123)  # Mock failure
    
    # Should retry and eventually succeed or fail gracefully
```

### 0.2 Integration Tests

```python
def test_full_review_pipeline():
    """Test complete review pipeline with mock PR data."""
    # Mock PR data
    mock_pr = {
        "files": [
            {"filename": "src/main.py", "patch": "+++ ..."},
            {"filename": "tests/test_main.py", "patch": "+++ ..."}
        ]
    }
    
    # Run pipeline with mocked inputs
    result = run_full_review(mock_pr)
    
    # Validate output structure
    assert "VERDICT:" in result
    assert "Summary" in result
    assert "Blocking Issues" in result
```

### 0.3 Performance Tests

```python
def test_large_pr_handling():
    """Test system behavior with large PRs."""
    # Generate mock PR with 50+ files
    large_pr = create_large_mock_pr(file_count=50)
    
    # Should not timeout
    start = time.time()
    result = run_full_review(large_pr)
    elapsed = time.time() - start
    
    assert elapsed < 300  # < 5 minutes
    assert len(result) > 0
```

### 0.4 Error Scenarios

```python
def test_error_scenarios():
    """Test graceful handling of error scenarios."""
    # Empty PR
    assert handle_empty_pr() == "No files to review"
    
    # Binary files only
    assert handle_binary_only_pr() == "Skipping binary files review"
    
    # API rate limit
    assert handle_rate_limit() == "Retry after 60 seconds"
```

### Kết quả mong đợi
- 100% test coverage cho core functionality
- Test-driven implementation cho các phases sau
- Early detection of integration issues
- Performance benchmarks cho các threshold sizes

---

## Phase 1: Dynamic Context Window Sizing

**Mục tiêu:** PR lớn không bị mất files quan trọng, PR nhỏ được review chi tiết hơn

**Files thay đổi:**
- `config/settings.py`
- `github_utils/client.py`

### 1.1 Cập nhật `config/settings.py`

```python
# Thêm các config mới:

# Dynamic context sizing
MAX_TOTAL_CHARS = int(os.getenv("MAX_TOTAL_CHARS", "20000"))  # Tăng từ 8000 → 20000
MAX_PATCH_CHARS = int(os.getenv("MAX_PATCH_CHARS", "10000"))  # Per-file limit

# PR size thresholds
SMALL_PR_THRESHOLD = int(os.getenv("SMALL_PR_THRESHOLD", "5"))    # < 5 files = small
MEDIUM_PR_THRESHOLD = int(os.getenv("MEDIUM_PR_THRESHOLD", "15")) # < 15 files = medium

# Performance throttling
MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "4"))
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "45"))

# Retry configuration
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "2"))

# Configuration validation
def validate_settings():
    """Validate all settings are within reasonable bounds."""
    if MAX_TOTAL_CHARS > 50000:
        raise ValueError("MAX_TOTAL_CHARS too large - may exceed model context")
    if MAX_PATCH_CHARS > 25000:
        raise ValueError("MAX_PATCH_CHARS too large")
    if SMALL_PR_THRESHOLD >= MEDIUM_PR_THRESHOLD:
        raise ValueError("Thresholds must be SMALL < MEDIUM")
    if MAX_CONCURRENT_AGENTS > 10:
        raise ValueError("MAX_CONCURRENT_AGENTS too large")
    if AGENT_TIMEOUT_SECONDS > 120:
        raise ValueError("AGENT_TIMEOUT_SECONDS too large")
```

### 1.2 Enhanced Error Handling & Retry Logic

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_DELAY_SECONDS, max=10),
    retry_error_callback=lambda x: None
)
def _get_with_retry(self, url: str, **kwargs):
    """Wrapper for GET requests with retry logic."""
    resp = httpx.get(url, headers=self.headers, timeout=self.timeout, **kwargs)
    resp.raise_for_status()
    return resp
```

### 1.3 Cập nhật `github_utils/client.py`

Thêm method `get_pr_metadata()`:

```python
def get_pr_metadata(self, owner: str, repo: str, pr_number: int) -> dict:
    """Fetch PR metadata for context-aware review sizing."""
    url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = httpx.get(url, headers=self.headers, timeout=self.timeout)
    resp.raise_for_status()
    data = resp.json()
    return {
        "changed_files": data.get("changed_files", 0),
        "additions": data.get("additions", 0),
        "deletions": data.get("deletions", 0),
        "title": data.get("title", ""),
        "body": data.get("body", ""),
    }
```

Cập nhật `get_pr_code_for_review()` — dynamic sizing:

```python
def _calculate_max_chars(self, file_count: int, base_max: int) -> int:
    """Dynamic context sizing based on PR size."""
    if file_count <= 5:    # Small PR
        return base_max           # Full detail
    elif file_count <= 15:  # Medium PR
        return base_max * 1.5
    else:                   # Large PR
        return base_max * 2       # More space needed
```

### 1.4 Performance Throttling

```python
def get_throttled_config(self, pr_size: str) -> dict:
    """Get throttled configuration based on PR size."""
    configs = {
        "SMALL": {
            "max_agents": MAX_CONCURRENT_AGENTS,
            "timeout": AGENT_TIMEOUT_SECONDS,
            "priority_files": []
        },
        "MEDIUM": {
            "max_agents": MAX_CONCURRENT_AGENTS - 1,
            "timeout": AGENT_TIMEOUT_SECONDS + 15,
            "priority_files": ["main.py", "src/**/*.py"]
        },
        "LARGE": {
            "max_agents": 2,  # Limit concurrent agents
            "timeout": 30,    # Shorter timeout
            "priority_files": ["src/**/*.py", "tests/**/*.py"],
            "skip_patterns": ["config/*", "*.md", "docs/*"]
        }
    }
    return configs.get(pr_size, configs["SMALL"])
```

### Kết quả mong đợi
- Small PR: review chi tiết 100% files
- Medium PR: review đầy đủ, truncate ít quan trọng
- Large PR: tăng context, skip config files, focus source code
- All PRs: graceful retry on API failures
- Configurable throttling based on PR size

---

## Phase 2: Structured Output Format cho Reviewers

**Mục tiêu:** 3 reviewers output theo format nhất quán → Tech Lead dễ parse và synthesize

**Files thay đổi:**
- `tasks/tasks.py`

### 2.1 Enforce structured markdown format

Cập nhật `expected_output` cho từng reviewer task:

**Code Quality Review** — yêu cầu format:
```markdown
## Code Quality Review

### Issue 1: [Short Title]
- **File:** `path/to/file.py`
- **Line:** 42
- **Severity:** MAJOR | MINOR
- **Category:** bug | style | maintainability | error-handling
- **Code:**
  ```python
  # problematic code snippet
  ```
- **Problem:** [1-2 sentences explaining why]
- **Suggested Fix:**
  ```python
  # corrected code
  ```

### Summary
- **MAJOR issues:** X
- **MINOR issues:** X
- **Files reviewed:** X/X
```

**Security Audit** — yêu cầu format:
```markdown
## Security Audit

### Finding 1: [Short Title]
- **File:** `path/to/file.py`
- **Line:** 42
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW
- **OWASP Category:** [e.g., A01:2021 – Broken Access Control]
- **Code:**
  ```python
  # vulnerable code
  ```
- **Vulnerability:** [explanation]
- **Remediation:**
  ```python
  # fixed code
  ```

### Summary
- **CRITICAL:** X | **HIGH:** X | **MEDIUM:** X | **LOW:** X
```

**Performance Analysis** — yêu cầu format:
```markdown
## Performance Analysis

### Issue 1: [Short Title]
- **File:** `path/to/file.py`
- **Line:** 42
- **Severity:** HIGH | MEDIUM | LOW
- **Current Complexity:** O(n²)
- **Code:**
  ```python
  # slow code
  ```
- **Problem:** [explain why it's slow]
- **Optimized Alternative:**
  ```python
  # faster code
  ```
- **Expected Impact:** [e.g., "50% faster for large inputs"]

### Summary
- Issues found: X (or "No significant performance issues found")
```

### 2.2 Cập nhật task `description` — thêm format template

Thêm vào cuối mỗi task description:

```python
"""
...
**OUTPUT FORMAT:**
Follow this exact markdown structure for each issue:
- File path with backticks
- Line number
- Severity level
- Code snippet in fenced block
- Explanation
- Fix with code

End with a **Summary** section showing issue counts.
"""
```

### Kết quả mong đợi
- Output nhất quán giữa các lần chạy
- Tech Lead dễ extract issues → giảm miss rate
- Dễ post-process (Phase 6)

---

## Phase 3: Context Passing Between Agents

**Mục tiêu:** Agents chia sẻ findings → giảm duplicate, tăng quality

**Files thay đổi:**
- `tasks/tasks.py` — dùng CrewAI `context` parameter

### 3.1 Sử dụng CrewAI Task context

CrewAI hỗ trợ `context` parameter — cho phép task sau nhận output của task trước:

```python
# Task 1: Code Quality (unchanged)
review_code_quality = Task(...)

# Task 2: Security — nhận context từ Code Quality
audit_security = Task(
    ...,
    context=[review_code_quality],  # ← THÊM: nhận findings từ Code Reviewer
)

# Task 3: Performance — nhận context từ Code Quality + Security
analyze_performance = Task(
    ...,
    context=[review_code_quality, audit_security],  # ← THÊM
)

# Task 4: Tech Lead — nhận TẤT CẢ (mặc định sequential đã có)
compile_final_review = Task(
    ...,
    context=[review_code_quality, audit_security, analyze_performance],  # ← Explicit
)
```

### 3.2 Cập nhật task descriptions — reference previous findings

Thêm vào Security task:

```python
"""
...
**CONTEXT:** You receive the Code Quality review above. Use it to:
- Avoid reporting duplicates (if Code Reviewer already flagged a related issue)
- Focus on security-specific aspects not covered by code quality review
"""
```

Thêm vào Performance task:

```python
"""
...
**CONTEXT:** You receive findings from Code Quality and Security reviews. Use these to:
- Avoid re-reporting issues already identified
- Cross-reference performance issues with security implications
- Focus exclusively on performance aspects
"""
```

### Kết quả mong đợi
- Giảm 50-70% duplicate findings
- Tech Lead nhận đầy đủ context từ tất cả reviewers
- Mỗi agent focus vào specialty của mình

---

## Phase 4: PR Metadata-Aware Review

**Mục tiêu:** Agents biết PR size, ngôn ngữ chính, scope → điều chỉnh review phù hợp

**Files thay đổi:**
- `github_utils/client.py` — thêm `get_pr_metadata()`
- `main.py` — fetch và format metadata
- `tasks/tasks.py` — nhận metadata block

### 4.1 Thêm metadata fetch

Trong `main.py`:

```python
# --- Fetch PR metadata ---
pr_metadata = gh.get_pr_metadata(owner, repo, pr_number)
file_count_from_meta = pr_metadata["changed_files"]
total_changes = pr_metadata["additions"] + pr_metadata["deletions"]

# Determine PR size category
if file_count_from_meta <= 5:
    pr_size = "SMALL"
elif file_count_from_meta <= 15:
    pr_size = "MEDIUM"
else:
    pr_size = "LARGE"
```

### 4.2 Format metadata block inject vào tasks

```python
metadata_block = (
    f"## PR Metadata\n"
    f"- **Size:** {pr_size} ({file_count_from_meta} files, "
    f"+{pr_metadata['additions']}/-{pr_metadata['deletions']} lines)\n"
    f"- **Title:** {pr_metadata['title']}\n"
    f"- **Description:** {pr_metadata['body'] or 'No description provided'}\n\n"
    f"**Review guidance:** "
    f"{'This is a small PR — review every line thoroughly.' if pr_size == 'SMALL' else ''}"
    f"{'This is a medium PR — focus on the most significant changes.' if pr_size == 'MEDIUM' else ''}"
    f"{'This is a large PR — prioritize source code files and critical changes.' if pr_size == 'LARGE' else ''}\n"
)
```

### 4.3 Dynamic context sizing

```python
# Adjust max_chars based on PR size
if pr_size == "SMALL":
    max_chars = MAX_TOTAL_CHARS           # 20000
elif pr_size == "MEDIUM":
    max_chars = int(MAX_TOTAL_CHARS * 1.5) # 30000
else:
    max_chars = MAX_TOTAL_CHARS * 2        # 40000

code_content = gh.get_pr_code_for_review(owner, repo, pr_number, max_chars=max_chars)
```

### Kết quả mong đợi
- Small PR: review sâu, từng dòng
- Large PR: review tập trung, không bị truncate

---

## Phase 5: Enhanced Tech Lead Synthesis

**Mục tiêu:** Tech Lead output chất lượng cao hơn — structured, deduplicated, confident

**Files thay đổi:**
- `agents/agents.py` — cập nhật Tech Lead backstory
- `tasks/tasks.py` — cập nhật Tech Lead task

### 5.1 Cập nhật Tech Lead Agent

```python
tech_lead = Agent(
    role="Technical Lead — PR Quality Gate",
    goal=(
        "Synthesize structured findings from Code Quality, Security, and Performance reviews "
        "into a single, clear, actionable PR review. Deduplicate findings, filter false positives, "
        "assess confidence, and provide a definitive APPROVE or REQUEST CHANGES verdict."
    ),
    backstory=(
        "You are a seasoned technical lead responsible for final PR approval decisions. "
        "You excel at synthesizing structured feedback from multiple specialized reviewers.\n\n"
        "Your key skills:\n"
        "1. **DEDUPLICATION:** You identify when multiple reviewers flag the same issue and merge them.\n"
        "2. **FALSE POSITIVE FILTERING:** You discard findings about files not in the PR, "
        ".env.example placeholders, generic advice without code references.\n"
        "3. **SEVERITY ASSESSMENT:** You honestly classify issues — only real bugs and security "
        "vulnerabilities are BLOCKING. Style preferences are always NON-BLOCKING.\n"
        "4. **CONFIDENCE SCORING:** For each issue, you assess HIGH/MEDIUM/LOW confidence.\n"
        "5. **PRAGMATISM:** You are not afraid to APPROVE a PR that only has minor suggestions.\n\n"
        "You NEVER invent issues not raised by reviewers. You NEVER exaggerate severity."
    ),
    llm=_llm,
    verbose=True,
)
```

### 5.2 Cập nhật Tech Lead Task — structured synthesis

```python
compile_final_review = Task(
    description=(
        "You are the Tech Lead. Synthesize the following structured reviews into a final PR review:\n"
        "1. Code Quality Review\n"
        "2. Security Audit\n"
        "3. Performance Analysis\n\n"
        "Create a structured markdown review:\n\n"
        "## 🤖 Automated PR Review\n\n"
        "### 📊 Summary\n"
        "| Category | Blocking | Non-Blocking | Total |\n"
        "|----------|----------|--------------|-------|\n"
        "| 🐛 Code Quality | X | X | X |\n"
        "| 🔒 Security | X | X | X |\n"
        "| ⚡ Performance | X | X | X |\n\n"
        "### 🔴 Blocking Issues (Must Fix)\n"
        "[List with file, line, explanation]\n\n"
        "### 🟡 Non-Blocking Issues (Suggestions)\n"
        "[List with file, line, explanation]\n\n"
        "### ✅ Positive Notes\n"
        "[What's done well]\n\n"
        "### 📋 Action Items\n"
        "1. [Priority-ordered list]\n\n"
        "**VERDICT RULES:**\n"
        "- Only BLOCKING issues → VERDICT: REQUEST CHANGES\n"
        "- No BLOCKING issues (even with NON-BLOCKING) → VERDICT: APPROVE\n"
        "- You MUST include exactly: `VERDICT: APPROVE` or `VERDICT: REQUEST CHANGES`\n"
        "  on its own line at the very end.\n\n"
        "**QUALITY GATE RULES:**\n"
        "- DISCARD findings about files not in the PR\n"
        "- DISCARD .env.example placeholder 'secrets'\n"
        "- DISCARD generic advice without specific code references\n"
        "- MERGE duplicate findings from different reviewers\n"
        "- Only real bugs + security vulnerabilities = BLOCKING\n"
    ),
    expected_output=(
        "A complete structured markdown PR review with: "
        "summary table, blocking issues, non-blocking issues, positive notes, "
        "prioritized action items, and final verdict line. "
        "Ready to post as GitHub PR review comment."
    ),
    agent=tech_lead,
    context=[review_code_quality, audit_security, analyze_performance],
)
```

### Kết quả mong đợi
- Output format nhất quán với summary table
- Deduplication rõ ràng
- Confidence assessment cho mỗi issue

---

## Phase 6: Review Output Post-Processing

**Mục tiêu:** Đảm bảo output luôn đúng format trước khi submit lên GitHub

**Files thay đổi:**
- `main.py` — thêm `post_process_review()` function

### 6.1 Thêm post-processing function

```python
import datetime

def post_process_review(review_text: str, pr_url: str, pr_metadata: dict) -> str:
    """Post-process the Tech Lead's review output.
    
    Ensures:
    - Review has proper header with metadata
    - Verdict line is present
    - Output fits within GitHub comment limit (65536 chars)
    - Format is clean and consistent
    """
    # Add metadata header
    header = (
        f"## 🤖 PR Review Bot — Automated Code Review\n"
        f"> **PR:** {pr_url} | "
        f"> **Files:** {pr_metadata.get('changed_files', '?')} | "
        f"> **Changes:** +{pr_metadata.get('additions', '?')}/-{pr_metadata.get('deletions', '?')} | "
        f"> **Reviewed:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"---\n\n"
    )
    
    # Ensure verdict exists
    if "VERDICT:" not in review_text.upper():
        # Try to infer from content
        verdict = parse_verdict(review_text)
        review_text += f"\n\nVERDICT: {verdict.replace('_', ' ')}"
    
    # Combine
    full_review = header + review_text
    
    # GitHub comment limit: 65536 characters
    GITHUB_COMMENT_LIMIT = 65000  # leave margin
    if len(full_review) > GITHUB_COMMENT_LIMIT:
        truncation_notice = "\n\n---\n*⚠️ Review truncated to fit GitHub comment limit.*\n"
        full_review = full_review[:GITHUB_COMMENT_LIMIT - len(truncation_notice)] + truncation_notice
    
    return full_review
```

### 6.2 Cập nhật main flow

```python
# Thay vì:
review_body = f"## 🤖 PR Review Bot — Automated Code Review\n\n{result_str}"

# Dùng:
review_body = post_process_review(result_str, pr_url, pr_metadata)
```

### Kết quả mong đợi
- Output luôn có header, metadata, verdict
- Không bao giờ exceed GitHub limit
- Consistent format mỗi lần chạy

---

## Phase 7: Inline Comment Support

**Mục tiêu:** Post inline comments trên specific lines thay vì chỉ 1 body comment lớn

**Files thay đổi:**
- `github_utils/client.py` — thêm `parse_inline_comments()` helper
- `main.py` — thêm logic extract và submit inline comments

### 7.1 Parse inline comments từ Tech Lead output

```python
def parse_inline_comments(review_text: str, files: list[dict]) -> list[dict]:
    """Extract inline comments from structured review output.
    
    Looks for patterns like:
    - **File:** `path/to/file.py`
    - **Line:** 42
    
    Returns list of dicts compatible with GitHub Review API:
    [{"path": "...", "line": N, "body": "..."}]
    """
    import re
    
    comments = []
    # Pattern: file path + line number + issue description
    pattern = re.compile(
        r"\*\*File:\*\*\s*`([^`]+)`\s*\n.*?\*\*Line:\*\*\s*(\d+)",
        re.DOTALL
    )
    
    # Build set of valid filenames from PR
    valid_files = {f.get("filename", "") for f in files}
    
    for match in pattern.finditer(review_text):
        filepath = match.group(1)
        line_num = int(match.group(2))
        
        # Only comment on files actually in the PR
        if filepath not in valid_files:
            continue
        
        # Extract the surrounding context as comment body
        # (from this match to the next issue or end of section)
        start = match.start()
        # Find the issue block
        block_end = review_text.find("###", start + 1)
        if block_end == -1:
            block_end = review_text.find("**File:**", start + 1)
        if block_end == -1:
            block_end = len(review_text)
        
        issue_block = review_text[start:block_end].strip()
        
        # Truncate long comments
        if len(issue_block) > 1000:
            issue_block = issue_block[:997] + "..."
        
        comments.append({
            "path": filepath,
            "line": line_num,
            "body": issue_block,
        })
    
    return comments
```

### 7.2 Submit review with inline comments

```python
# Trong main.py, sau khi có review_body:

# Try to extract inline comments
inline_comments = parse_inline_comments(result_str, files)

if inline_comments:
    print(f"   📝 Submitting with {len(inline_comments)} inline comments")
    review_result = gh.submit_review(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        commit_id=commit_sha,
        body=review_body,
        event=event,
        comments=inline_comments,  # ← Inline comments
    )
else:
    # Fallback: body-only review
    review_result = gh.submit_review(...)
```

### Kết quả mong đợi
- Developer thấy issue ngay tại dòng code cần fix
- Review trực quan và dễ follow hơn
- Fallback gracefully nếu không parse được inline comments

---

## Phase 8: Basic Metrics (Foundation for Phase 8 Original)

**Mục tiêu:** Collect essential metrics to track review quality and system performance

**Files thay đổi:**
- `config/settings.py` — Add metrics config
- `main.py` — Basic metrics collection

### 8.1 Metrics Configuration

```python
# In config/settings.py
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_FILE_PATH = os.getenv("METRICS_FILE_PATH", "review_metrics.jsonl")
MAX_METRICS_SIZE = int(os.getenv("MAX_METRICS_SIZE", "10000"))  # Max lines in metrics file
```

### 8.2 Basic Metrics Collection

```python
# In main.py
def log_basic_metrics(pr_metadata: dict, verdict: str, elapsed_time: float, file_count: int):
    """Log basic metrics for quality tracking."""
    if not ENABLE_METRICS:
        return
    
    import json
    from datetime import datetime
    
    metric = {
        "timestamp": datetime.now().isoformat(),
        "pr_files": pr_metadata.get("changed_files", 0),
        "pr_additions": pr_metadata.get("additions", 0),
        "pr_deletions": pr_metadata.get("deletions", 0),
        "verdict": verdict,
        "elapsed_seconds": round(elapsed_time, 2),
        "files_reviewed": file_count,
        "review_size": len(result_str) if 'result_str' in locals() else 0
    }
    
    # Rotate metrics file if too large
    if os.path.exists(METRICS_FILE_PATH):
        with open(METRICS_FILE_PATH, "r") as f:
            lines = f.readlines()
        if len(lines) > MAX_METRICS_SIZE:
            # Keep only last 5000 lines
            with open(METRICS_FILE_PATH, "w") as f:
                f.writelines(lines[-5000:])
    
    # Append new metric
    with open(METRICS_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(metric) + "\n")
```

### Kết quả mong đợi
- Track verdict distribution (APPROVE vs REQUEST CHANGES)
- Monitor review execution time
- Track PR sizes being reviewed
- Basic quality trending

---

## Phase 8: Review Quality Metrics & Logging (Enhanced)

**Mục tiêu:** Track review quality over time, debug issues

**Files thay đổi:**
- `main.py` — thêm metrics collection và logging

### 8.1 Thêm metrics collection

```python
import json
import time

def collect_review_metrics(
    pr_url: str,
    pr_metadata: dict,
    review_text: str,
    verdict: str,
    elapsed_time: float,
    files_fetched: int,
) -> dict:
    """Collect metrics about the review for quality tracking."""
    
    # Count issues from structured output
    blocking_count = review_text.lower().count("blocking")
    major_count = len(re.findall(r"Severity:\s*MAJOR|CRITICAL|HIGH", review_text, re.IGNORECASE))
    minor_count = len(re.findall(r"Severity:\s*MINOR|LOW", review_text, re.IGNORECASE))
    
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "pr_url": pr_url,
        "pr_size": {
            "files": pr_metadata.get("changed_files", 0),
            "additions": pr_metadata.get("additions", 0),
            "deletions": pr_metadata.get("deletions", 0),
        },
        "review": {
            "verdict": verdict,
            "files_reviewed": files_fetched,
            "blocking_issues": blocking_count,
            "major_issues": major_count,
            "minor_issues": minor_count,
            "review_length": len(review_text),
            "has_summary_table": "| Category" in review_text or "| ---" in review_text,
        },
        "performance": {
            "elapsed_seconds": round(elapsed_time, 2),
        },
    }
```

### 8.2 Log metrics

```python
# Cuối main(), sau khi submit review:

# --- Collect and log metrics ---
elapsed = time.time() - start_time
metrics = collect_review_metrics(pr_url, pr_metadata, result_str, verdict, elapsed, file_count)

metrics_path = os.getenv("REVIEW_METRICS_PATH", "review_metrics.jsonl")
with open(metrics_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(metrics) + "\n")

print(f"📊 Metrics logged to {metrics_path}")
print(f"   ⏱️  Time: {metrics['performance']['elapsed_seconds']}s")
print(f"   📋 Issues: {metrics['review']['major_issues']} major, {metrics['review']['minor_issues']} minor")
```

### Kết quả mong đợi
- Mỗi review ghi 1 line JSON vào metrics file
- Có thể phân tích xu hướng: verdict ratio, issue counts, review time
- Debug được khi nào quality giảm

---

## Phase 9: Documentation Updates

**Mục tiêu:** Update documentation để developer hiểu và sử dụng các features mới

**Files thay đổi:**
- `README.md`
- `docs/CONFIGURATION.md` (new)
- `docs/EXAMPLES.md` (new)

### 9.1 Cập nhật README.md

```markdown
## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_TOTAL_CHARS` | 20000 | Max total chars cho PR code context |
| `MAX_PATCH_CHARS` | 10000 | Max chars per file patch |
| `SMALL_PR_THRESHOLD` | 5 | Files count threshold cho SMALL PR |
| `MEDIUM_PR_THRESHOLD` | 15 | Files count threshold cho MEDIUM PR |
| `MAX_CONCURRENT_AGENTS` | 4 | Max agents chạy concurrent |
| `AGENT_TIMEOUT_SECONDS` | 45 | Timeout per agent (seconds) |
| `MAX_RETRY_ATTEMPTS` | 3 | Số lần retry API calls |
| `ENABLE_METRICS` | true | Bật/tắt metrics collection |
| `METRICS_FILE_PATH` | review_metrics.jsonl | Path to metrics log file |
```

### 9.2 Tạo CONFIGURATION.md

Document chi tiết:
- Mỗi config variable: type, default, range, effect
- Examples cho các scenarios khác nhau (small team, enterprise, CI/CD)
- Troubleshooting guide cho common issues

### 9.3 Tạo EXAMPLES.md

Example output cho:
- Small PR review output (APPROVE)
- Large PR review output (REQUEST CHANGES)
- Review with inline comments
- Review with security findings

### Kết quả mong đợi
- Developer dễ dàng config và customize
- Onboarding nhanh cho team members mới
- Troubleshooting guide giảm support burden

---

## 📁 Summary — Files cần thay đổi

| File | Phases | Mô tả thay đổi |
|------|--------|----------------|
| `tests/` (new) | 0 | Test suite: unit, integration, performance |
| `config/settings.py` | 1 | Thêm config mới + validation + throttling |
| `github_utils/client.py` | 1, 4, 7 | Dynamic sizing, metadata fetch, inline comments, retry logic |
| `tasks/tasks.py` | 2, 3, 5 | Structured output templates, context passing, enhanced Tech Lead task |
| `agents/agents.py` | 5 | Enhanced Tech Lead backstory |
| `main.py` | 1, 4, 6, 7, 8 | Metadata, post-processing, inline comments, metrics, dynamic sizing, throttling |
| `README.md` | 9 | Update config reference |
| `docs/CONFIGURATION.md` (new) | 9 | Detailed config documentation |
| `docs/EXAMPLES.md` (new) | 9 | Example review outputs |

## 🔄 Thứ tự triển khai khuyến nghị

```
1. Phase 0 → Testing Framework        (tests/ directory) - Foundation
2. Phase 2 → Structured Output        (tasks/tasks.py)
3. Phase 8 (Basic) → Metrics         (main.py) - Measure success
4. Phase 3 → Context Passing          (tasks/tasks.py)
5. Phase 5 → Enhanced Tech Lead       (agents/agents.py + tasks/tasks.py)
6. Phase 1 → Dynamic Context          (config/settings.py + client.py)
7. Phase 4 → PR Metadata              (client.py + main.py)
8. Phase 6 → Post-Processing         (main.py)
9. Phase 7 → Inline Comments          (client.py + main.py)
10. Phase 8 (Enhanced) → Metrics      (main.py)
11. Phase 9 → Documentation           (README.md, docs/)
```

## ⚠️ Risks & Considerations

| Risk | Mitigation |
|------|-----------|
| LLM có thể không tuân thủ structured format | Thêm format examples trong prompt; post-processing fallback |
| Context passing tăng token usage | Chỉ pass summary, không pass full output |
| Inline comments cần đúng line numbers | Fallback to body-only nếu parse fail |
| Metrics file grows unbounded | Rotate/log rotation; JSONL format dễ process |
| Dynamic sizing có thể exceed model context | Hard cap ở model's context window |
| Missing testing leads to bugs | Phase 0 MUST be implemented first |
| API rate limits cause failures | Retry mechanism with exponential backoff |
| Large PRs cause timeouts | Performance throttling based on size |
| Configuration errors in production | Add validation function for settings |
| Multi-language PRs get inconsistent reviews | Language-specific review strategies |

## 🔧 **Additional Edge Cases to Handle**

### Binary Files
```python
def is_binary_file(filename: str, content: str) -> bool:
    """Detect if file is binary."""
    binary_extensions = {'.exe', '.dll', '.so', '.png', '.jpg', '.pdf', '.zip'}
    return any(filename.endswith(ext) for ext in binary_extensions)
```

### Generated Files
```python
def is_generated_file(filename: str) -> bool:
    """Detect if file is auto-generated."""
    generated_patterns = ['node_modules/', 'dist/', 'build/', '.env', '*.min.js']
    return any(pattern in filename for pattern in generated_patterns)
```

### Empty PR
```python
def handle_empty_pr(pr_files: list) -> str:
    """Handle PR with no changed files."""
    if not pr_files:
        return "No code files to review"
    if all(is_binary_file(f.get('filename', '')) for f in pr_files):
        return "PR contains only binary files - no code review needed"
```

### Multi-language PR
```python
def get_language_specific_settings(pr_files: list) -> dict:
    """Get review settings based on primary language."""
    extensions = {}
    for f in pr_files:
        ext = f.get('filename', '').split('.')[-1]
        extensions[ext] = extensions.get(ext, 0) + 1
    
    primary_lang = max(extensions.items(), key=lambda x: x[1])[0]
    
    lang_settings = {
        'python': {'review_style': 'pep8', 'focus_on': 'bugs, security'},
        'javascript': {'review_style': 'eslint', 'focus_on': 'async, security'},
        'go': {'review_style': 'golint', 'focus_on': 'concurrency, performance'}
    }
    
    return lang_settings.get(primary_lang, {'review_style': 'general'})
```

---

## 📈 Success Metrics

Sau khi triển khai, đo lường success bằng:

### Core Quality Metrics
1. **False positive rate** giảm ≥ 50% (so với trước Phase 2)
2. **Duplicate findings** giảm ≥ 70% (so với trước Phase 3)
3. **Verdict accuracy** — APPROVE cho clean PR, REQUEST CHANGES cho buggy PR
4. **Output format consistency** — 100% reviews có summary table + verdict
5. **Files reviewed ratio** — ≥ 90% source files được review (trước truncation)

### Performance Metrics
6. **Average review time** — < 5 minutes cho small PR, < 10 minutes cho large PR
7. **Success rate** — > 95% reviews complete without errors
8. **API success rate** — > 99% API calls succeed with retry
9. **Memory usage** — < 4GB per review process

### Developer Experience
10. **Review clarity score** — developer satisfaction rating (1-5 scale)
11. **Time to fix** — average time for developers to address issues
12. **False positive feedback rate** — < 10% of marked issues are false positives

### System Health
13. **Error rate** — < 1% reviews fail due to system errors
14. **Timeout rate** — < 5% reviews timeout due to large PRs
15. **Review completeness** — ≥ 95% of critical files reviewed
