# Review Agent — Plan Triển Khai

## 1. Tổng quan

Nâng cấp PR Review Bot hiện tại (CrewAI + 4 agents) để:
- **Đầu vào**: Link PR GitHub + Knowledge Base của dự án
- **Đầu ra**: Comment + Status (APPROVE / REQUEST CHANGES) trên GitHub

## 2. Trạng thái hiện tại

### Đã có
| Thành phần | File | Mô tả |
|---|---|---|
| 4 Agents | `agents/agents.py` | Code Reviewer, Security Expert, Performance Engineer, Tech Lead |
| GitHub Client | `github_utils/client.py` | Fetch PR files, diff, metadata, post comment |
| Tasks | `tasks/tasks.py` | 4 task sequential cho crew |
| Config | `config/settings.py` | Env-based config (LLM, GitHub token) |
| Main | `main.py` | Orchestrator: fetch PR → chạy agents → post comment |

### Chưa có
- Tích hợp Knowledge Base vào review process
- Submit formal GitHub review (APPROVE / REQUEST CHANGES)

## 3. Knowledge Base hiện có

User đã cung cấp KB dạng JSON (Project Understanding System) tại `knowledge_base/CrewAI_Review_Bot/`:

| File | Nội dung |
|---|---|
| `latest.json` | Snapshot đầy đủ: files, modules, symbols, relations, summaries, conventions, risks, glossary |
| `metadata.json` | Metadata dự án (branch, commit, stats) |
| `USE_GUIDE.md` | Hướng dẫn sử dụng KB |
| `indexes/semantic_index.json` | Semantic search index |

**Dữ liệu quan trọng cần dùng cho review**:
- **summaries** — Mô tả LLM-generated cho mỗi file/symbol
- **conventions** — Coding patterns phát hiện được (naming, module structure, ...)
- **risks** — Risk areas (authentication, config secrets, external API, ...)
- **relations** — Quan hệ dependency giữa files/modules

## 4. Plan triển khai

### Phase 1: Knowledge Base Loader

**Tạo `kb_loader.py`** (module mới, nằm ở root hoặc thư mục riêng)

```python
# kb_loader.py
def load_knowledge_base(kb_path: str, max_chars: int = 8000) -> str:
    """
    Load KB từ latest.json, trích xuất và format:
    - summaries (mô tả file/symbol)
    - conventions (coding patterns)
    - risks (risk areas)
    - relations (dependencies)

    Trả về chuỗi text format sẵn để inject vào agent tasks.
    """
```

**Format output** (inject vào agent tasks):
```
## Project Knowledge Base

### File Summaries
- main.py: Entry point, orchestrator...
- agents/agents.py: 4 specialized CrewAI agents...
...

### Coding Conventions
- Python snake_case file naming
- PascalCase class naming
- Python package modules with __init__.py
- Centralized configuration
- CLI entrypoint pattern

### Risk Areas
- Authentication in main.py (HIGH)
- Config Secrets in config/settings.py (HIGH)
- External API in github_utils/client.py (MEDIUM)
...

### Module Dependencies
- agents/agents.py → imports config/settings.py
- tasks/tasks.py → imports agents/agents.py
- main.py → imports all modules
```

### Phase 2: Cập nhật Config

**Sửa `config/settings.py`** — thêm 2 biến:
```python
KB_PATH = os.getenv("KB_PATH", "")          # Path tới thư mục KB
KB_MAX_CHARS = int(os.getenv("KB_MAX_CHARS", "8000"))  # Giới hạn context
```

**Sửa `.env.example`** — thêm:
```
KB_PATH=knowledge_base/CrewAI_Review_Bot
KB_MAX_CHARS=8000
```

### Phase 3: Cập nhật Agents

**Sửa `agents/agents.py`** — cập nhật goal của các agents:

| Agent | Thay đổi |
|---|---|
| code_reviewer | Thêm "...ensuring compliance with project-specific coding standards when provided" |
| security_expert | Thêm "...checking against project-specific security policies when provided" |
| performance_engineer | Thêm "...considering project-specific performance requirements when provided" |
| **tech_lead** | **Thêm yêu cầu output `VERDICT: APPROVE` hoặc `VERDICT: REQUEST CHANGES`** trên dòng riêng để parse programatically |

### Phase 4: Cập nhật Tasks

**Sửa `tasks/tasks.py`**:
- Đổi signature: `build_tasks(code)` → `build_tasks(code, knowledge_base="")`
- Nếu KB không rỗng, inject section `"## Project Knowledge Base"` vào đầu 3 task đầu
- Task 4 (compile_final_review): Inject KB reference + yêu cầu explicit `VERDICT:` trong output

### Phase 5: GitHub Review API

**Sửa `github_utils/client.py`** — thêm 2 methods:

```python
def get_pr_head_commit(self, owner, repo, pr_number) -> str:
    """Lấy SHA của head commit (cần cho Review API)"""
    # GET /repos/{owner}/{repo}/pulls/{pr_number}
    # return data["head"]["sha"]

def submit_review(self, owner, repo, pr_number, commit_id, body, event, comments=None) -> dict:
    """Submit formal GitHub review"""
    # POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews
    # event: "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
```

**GitHub Review API payload**:
```json
{
  "commit_id": "abc123...",
  "body": "## PR Review Bot — Automated Code Review\n\n...",
  "event": "APPROVE",
  "comments": []
}
```

### Phase 6: Cập nhật Main Orchestration

**Sửa `main.py`** — thay đổi luồng:

```
TRƯỚC:  PR URL → Fetch Code → 4 Agents → Post Comment
SAU:    PR URL + KB → Fetch Code → Load KB → 4 Agents → Parse Verdict → Submit Review
```

Chi tiết:
1. CLI: `python main.py <pr_url> [kb_path]` (kb_path optional)
2. Load KB: `kb_content = load_knowledge_base(kb_path, max_chars=KB_MAX_CHARS)`
3. Pass KB vào tasks: `build_tasks(code_content, knowledge_base=kb_content)`
4. Parse verdict từ Tech Lead output:
   ```python
   def parse_verdict(review_text) -> str:
       # Regex: VERDICT:\s*(APPROVE|REQUEST CHANGES)
       # Fallback: keyword search
       # Default: COMMENT
   ```
5. Submit review với fallback chain:
   - **(1)** Thử `submit_review` → formal review với status
   - **(2)** Nếu fail → `post_comment` → comment thường
   - **(3)** Nếu fail → save local file

## 5. Tóm tắt files cần thay đổi

| File | Action | Mô tả |
|---|---|---|
| `kb_loader.py` | **Tạo mới** | Load + format KB từ JSON |
| `config/settings.py` | **Sửa** | Thêm KB_PATH, KB_MAX_CHARS |
| `.env.example` | **Sửa** | Thêm 2 biến KB config |
| `agents/agents.py` | **Sửa** | Cập nhật goal/backstory agents |
| `tasks/tasks.py` | **Sửa** | Thêm knowledge_base param, inject vào tasks |
| `github_utils/client.py` | **Sửa** | Thêm submit_review, get_pr_head_commit |
| `main.py` | **Sửa** | Integrate KB + verdict parsing + review submission |

## 6. Luồng hoạt động

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

## 7. Verification

1. `python main.py <pr_url>` (không KB) → hoạt động như trước
2. `python main.py <pr_url> knowledge_base/CrewAI_Review_Bot` → KB được load, inject vào tasks
3. Kiểm tra GitHub PR → thấy formal review với status APPROVE/REQUEST_CHANGES
4. Test verdict parsing với output có/không có VERDICT marker
5. Test fallback chain khi thiếu GITHUB_TOKEN
