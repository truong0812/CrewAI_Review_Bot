# Plan: PR Review Bot — Requirements Extraction, Inline Comments, Webhook Server

## Context

PR review bot hiện chạy như CLI tool — user chạy `pr-review review <url>` để review PR. 3 tính năng cần thêm:

1. **Requirements Extraction**: Lấy PR description làm task requirements, agents review code có thỏa mãn requirements không
2. **Inline Comments**: Comment trực tiếp vào từng dòng code cụ thể thay vì chỉ 1 review tổng
3. **Webhook Server + Dev Response Loop**: FastAPI server nhận GitHub webhook, tự review khi PR mở/push, phản hồi khi dev comment (LLM classify intent → trả lời/giải thích/re-review)

## File Structure (Mới/Modified)

### New files
| File | Purpose |
|---|---|
| `engine.py` | Review engine tách từ cli.py, gọi bởi cả CLI và webhook |
| `requirements_extractor.py` | Parse PR body thành structured requirements |
| `review_parser.py` | Parse Tech Lead output → inline comment dicts cho GitHub API |
| `webhook/__init__.py` | Module init |
| `webhook/server.py` | FastAPI app, `/webhook` endpoint, `/health` endpoint |
| `webhook/signature.py` | HMAC-SHA256 webhook signature verification |
| `webhook/handlers.py` | Route events → handlers (pr_update, issue_comment, review_comment) |
| `webhook/response_loop.py` | Classify dev intent → trả lời/giải thích/re-review |
| `webhook/state.py` | Cache review state, detect bot's own comments |

### Modified files
| File | Changes |
|---|---|
| `cli.py` | Refactor: review command → thin wrapper gọi `engine.run_review()`; thêm `serve` command |
| `tasks/tasks.py` | `build_tasks()` thêm param `requirements`, inject requirements block vào reviewer tasks |
| `agents/agents.py` | Tech Lead thêm requirements coverage awareness |
| `github_utils/client.py` | Thêm `build_line_to_position_map()` cho inline comments, `fetch_linked_issues()` |
| `config/settings.py` | Thêm WEBHOOK_SECRET, WEBHOOK_PORT, WEBHOOK_HOST, RESPONSE_LOOP_ENABLED, AUTO_REVIEW_ON_PUSH |
| `pyproject.toml` | Thêm `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0`; include `webhook*` packages |
| `.env.example` | Thêm webhook config entries |

---

## Implementation Steps

### Step 1: Refactor — Extract `engine.py` from `cli.py`

**Tại sao**: Webhook server cần gọi cùng review logic. Không thể duplicate 200 dòng code.

Tạo `engine.py`:
- `ReviewResult` dataclass: `owner, repo, pr_number, verdict, review_body, commit_sha, review_url, inline_comments`
- `run_review(pr_url, *, kb_path, language, dry_run, verbose) -> ReviewResult`
- Move `parse_verdict()` từ `cli.py` sang `engine.py`

`cli.py` review command → thin wrapper: parse args → gọi `engine.run_review()` → print result
Thêm import backward compat: `parse_verdict` re-export từ `engine.py`

### Step 2: Inline Comments (`review_parser.py` + `GitHubClient` changes)

**Parser** (`review_parser.py`):
- `parse_inline_comments(review_text, pr_files) -> list[dict]`
- Regex extract `` `file.ts:42` `` patterns từ Tech Lead output
- Mỗi match → `{"path": "file.ts", "position": N, "body": "issue text"}`
- Max 20 inline comments, ưu tiên blocking issues

**Diff position mapping** (tricky part):
- GitHub review API dùng `position` (diff-relative index) chứ không phải `line` (file line number)
- Thêm `build_line_to_position_map()` vào `GitHubClient`:
  - Parse unified diff của mỗi file
  - Track `(filename, file_line) -> diff_position`
  - Parse `@@ -a,b +c,d @@` hunk headers để biết starting line
  - Fallback: thử nearby lines (+/- 3), skip nếu không tìm thấy

**Engine integration**:
- Sau khi chạy crew, parse inline comments
- Pass `comments` vào `submit_review()` (param đã tồn tại nhưng chưa dùng)
- Thêm note vào review body: "> _Chi tiết được comment trực tiếp trên code._"

### Step 3: Requirements Extraction (`requirements_extractor.py`)

**Core**: `extract_requirements(pr_title, pr_body) -> str`

Parse strategy:
- Markdown checkboxes: `- [ ] task`, `- [x] done`
- Acceptance criteria sections (headers: "## Acceptance Criteria", "## Requirements", "## Checklist")
- `Fixes #N`, `Closes #N` references (plumbing cho future issue fetching)
- Format output:
  ```
  ## PR Requirements
  ### From PR Description
  - [ ] Add authentication
  - [x] Write tests
  ```

**Extensibility** (cho future):
- `RequirementSource` ABC với `fetch(context) -> str`
- `PRBodySource` (default), sẵn sàng thêm `GitHubIssueSource`, `ExternalURLSource`
- Registry pattern: `register_source(name, source)`

**Task modification** (`tasks/tasks.py`):
- `build_tasks(code, knowledge_base, pr_author, requirements="")` — thêm param
- Inject `requirements_block` vào 4 reviewer tasks + Tech Lead task
- Instruction: "REQUIREMENT COVERAGE CHECK: đánh giá mỗi requirement MET/PARTIALLY MET/NOT MET"

**Tech Lead update** (`agents/agents.py`):
- Goal thêm: "If requirements are provided, evaluate whether code satisfies them"
- Output format thêm "Requirement Coverage" section

**Engine integration**: Fetch PR metadata → extract requirements → pass vào `build_tasks()`

### Step 4: Webhook Server

#### 4a. Config + Signature
- `config/settings.py`: WEBHOOK_SECRET, WEBHOOK_PORT (8000), WEBHOOK_HOST (0.0.0.0)
- `webhook/signature.py`: `verify_signature(body, header, secret)` — HMAC-SHA256

#### 4b. FastAPI App (`webhook/server.py`)
- `POST /webhook` — nhận GitHub events, verify signature, dispatch async
- `GET /health` — health check
- Return 202 immediately (review mất 1-5 phút, GitHub timeout 10s)
- Run CrewAI trong ThreadPoolExecutor (CrewAI.kickoff() là sync, cần bridge sang async)

#### 4c. Event Handlers (`webhook/handlers.py`)
- `pull_request` (opened, synchronize) → `handle_pr_update()` → gọi `engine.run_review()`
- `issue_comment` (created) → `handle_issue_comment()` → response loop
- `pull_request_review_comment` (created) → `handle_review_comment()` → response loop
- Skip bot's own comments (fetch bot username qua `/user` endpoint, cache)

#### 4d. Response Loop (`webhook/response_loop.py`)

**Intent classification** (single LLM call, không dùng full crew):
```
"question"  → answer_question() — LLM generate explanation, post as reply comment
"fixed"     → acknowledge + đợi synchronize event → auto re-review
"pushback"  → evaluate_pushback() — LLM evaluate, post response hoặc retraction
"other"     → ignore
```

Prompt classify: ngắn gọn, trả về 1 word. Support Vietnamese comments.

#### 4e. State Management (`webhook/state.py`)
- GitHub API là source of truth (list reviews, get review body)
- In-memory cache tối ưu (rebuild from API on restart)
- Cache: `{key: "owner/repo#pr", value: {last_review_sha, last_review_body, timestamp}}`

#### 4f. CLI Command
```python
@cli.command()
@click.option("--port", "-p", ...)
@click.option("--host", "-h", ...)
def serve(port, host):
    """Start webhook server."""
    uvicorn.run(app, host=host, port=port)
```

#### 4g. Dependencies
- `fastapi>=0.110.0`
- `uvicorn[standard]>=0.29.0`

---

## Verification

1. **Engine refactor**: Chạy `pr-review review <url> --dry-run` — output giống hệt trước
2. **Inline comments**: Review PR thật, verify inline comments xuất hiện đúng dòng trên GitHub
3. **Requirements**: Tạo PR có checklist trong body, verify agents đánh giá coverage
4. **Webhook**: `pr-review serve` + ngrok tunnel, mở PR → auto review
5. **Response loop**: Comment trên PR review → bot reply phù hợp, push commit → auto re-review
6. **All existing tests pass**
