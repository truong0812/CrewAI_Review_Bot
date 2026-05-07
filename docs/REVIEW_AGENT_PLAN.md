# Review Agent — Tài liệu thiết kế (Đã triển khai ✅)

> **Status:** Đã triển khai hoàn toàn. File này lưu lại như tài liệu tham khảo.

## 1. Tổng quan

PR Review Bot sử dụng CrewAI + 4 agents để:
- **Đầu vào**: Link PR GitHub + Knowledge Base của dự án (tùy chọn)
- **Đầu ra**: Formal Review (APPROVE / REQUEST CHANGES / COMMENT) trên GitHub PR

## 2. Kiến trúc hiện tại

### Các thành phần

| Thành phần | File | Mô tả |
|---|---|---|
| 4 Agents | `agents/agents.py` | Code Reviewer, Security Expert, Performance Engineer, Tech Lead |
| GitHub Client | `github_utils/client.py` | Fetch PR files, diff, metadata, submit review, post comment |
| Tasks | `tasks/tasks.py` | 4 task sequential cho crew, hỗ trợ KB injection |
| Config | `config/settings.py` | Env-based config (LLM, GitHub token, KB) |
| KB Loader | `kb_loader.py` | Load Knowledge Base từ JSON, format cho agent context |
| Main | `main.py` | Orchestrator: fetch PR → load KB → chạy agents → parse verdict → submit review |

### Luồng hoạt động

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  PR URL + KB    │────▶│  Fetch PR    │────▶│  Load KB        │
│  (CLI input)    │     │  from GitHub │     │  from JSON      │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Submit Review   │◀────│  Parse       │◀────│  4 Agents Run   │
│  to GitHub       │     │  Verdict     │     │  (sequential)   │
│  (APPROVE/RCC)   │     │  APPROVE/RCC │     │  + KB context   │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │
         ▼ (fallback)
┌─────────────────┐     ┌──────────────┐
│  Post Comment   │────▶│  Save Local  │
│  (issue comment)│     │  (markdown)  │
└─────────────────┘     └──────────────┘
```

## 3. Chi tiết triển khai

### Phase 1: Knowledge Base Loader ✅

**File:** `kb_loader.py`

```python
def load_knowledge_base(kb_path: str, max_chars: int = 4000) -> str:
    """Load KB từ latest.json, trích xuất và format:
    - conventions (coding patterns) — HIGH priority
    - risks (risk areas) — HIGH priority
    - relations (dependencies) — MEDIUM priority
    - summaries (file descriptions) — LOW priority
    """
```

**Tính năng:**
- Đọc `latest.json` từ thư mục KB
- Schema validation (`_validate_kb_schema`)
- Ưu tiên conventions & risks trước, summaries sau
- Truncate an toàn với warning message
- Skip KB internal files trong output

### Phase 2: Config ✅

**File:** `config/settings.py`

```python
KB_PATH = os.getenv("KB_PATH", "")                              # Path tới thư mục KB
KB_MAX_CHARS = int(os.getenv("KB_MAX_CHARS", "8000"))           # Giới hạn context (safe parsing)
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))               # GitHub API timeout
REVIEW_OUTPUT_PATH = os.getenv("REVIEW_OUTPUT_PATH", "")        # Local fallback path
```

### Phase 3: Agents ✅

**File:** `agents/agents.py`

| Agent | Đặc điểm |
|---|---|
| code_reviewer | Review code quality, kiểm tra project-specific coding standards |
| security_expert | Security audit, kiểm tra project-specific security policies |
| performance_engineer | Performance analysis, kiểm tra project-specific perf requirements |
| **tech_lead** | Synthesize reports → final review với `VERDICT: APPROVE` hoặc `VERDICT: REQUEST CHANGES` |

Tất cả agents có anti-false-positive instructions trong backstory.

### Phase 4: Tasks ✅

**File:** `tasks/tasks.py`

- Signature: `build_tasks(code, knowledge_base="")` 
- Nếu KB không rỗng, inject vào 3 task đầu (Code Reviewer, Security, Performance)
- Task 4 (Tech Lead): Yêu cầu explicit `VERDICT:` trong output
- Mỗi task có IMPORTANT RULES để tránh false positives

### Phase 5: GitHub Review API ✅

**File:** `github_utils/client.py`

```python
def get_pr_head_commit(self, owner, repo, pr_number) -> str:
    """Lấy SHA của head commit (cần cho Review API)"""

def submit_review(self, owner, repo, pr_number, commit_id, body, event, comments=None) -> dict:
    """Submit formal GitHub review"""
    # event: "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
```

### Phase 6: Main Orchestration ✅

**File:** `main.py`

Luồng:
1. CLI: `python main.py <pr_url> [kb_path]` (kb_path optional)
2. Load KB: `kb_content = load_knowledge_base(kb_path, max_chars=KB_MAX_CHARS)`
3. Pass KB vào tasks: `build_tasks(code_content, knowledge_base=kb_content)`
4. Parse verdict: `parse_verdict(review_text)` — regex + keyword fallback
5. Submit review với fallback chain:
   - **(1)** `submit_review` → formal review với status
   - **(2)** `post_comment` → comment thường
   - **(3)** Save local file

## 4. Files đã triển khai

| File | Action | Status |
|---|---|---|
| `kb_loader.py` | **Tạo mới** | ✅ Hoàn thành |
| `config/settings.py` | **Sửa** | ✅ Hoàn thành |
| `.env.example` | **Sửa** | ✅ Hoàn thành |
| `agents/agents.py` | **Sửa** | ✅ Hoàn thành |
| `tasks/tasks.py` | **Sửa** | ✅ Hoàn thành |
| `github_utils/client.py` | **Sửa** | ✅ Hoàn thành |
| `main.py` | **Sửa** | ✅ Hoàn thành |