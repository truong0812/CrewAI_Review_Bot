# Plan Cải Thiện Chất Lượng Review (Đã triển khai ✅)

> **Status:** Tất cả phases đã được triển khai. File này lưu lại như tài liệu tham khảo.

## Phân tích vấn đề (đã giải quyết)

### Vấn đề 1: Context Truncation ✅ ĐÃ FIX
**Hiện tượng:** Model báo "main.py not provided for review", "tasks/tasks.py not provided for review"

**Nguyên nhân:** 
- `get_pr_code_for_review()` giới hạn `max_chars` quá nhỏ
- KB context chiếm nhiều chars → thực tế chỉ còn ít cho code
- PR có nhiều files → files cuối bị truncate

**Đã fix:**
1. `MAX_PATCH_CHARS = 8000` per file (trong `github_utils/client.py`)
2. File prioritization — source code files (.py, .js, .ts, v.v.) trước, skip .log/.bat/.png
3. Truncation an toàn với thông báo số files còn lại

### Vấn đề 2: False Positives ✅ ĐÃ FIX
**Hiện tượng:** Flag `.env.example` placeholder là "hardcoded secret", flag `os.getenv()` là "secret"

**Đã fix:** Cải thiện task prompts — thêm "IMPORTANT RULES" constraints vào mỗi task trong `tasks/tasks.py` và backstory trong `agents/agents.py`

### Vấn đề 3: Generic Findings ✅ ĐÃ FIX
**Hiện tượng:** "Inefficient loop", "Memory inefficiency" không kèm code cụ thể

**Đã fix:** Yêu cầu agents trích dẫn code cụ thể, giải thích tại sao, và cung cấp fix thay thế

### Vấn đề 4: GitHub 403 ✅ ĐÃ FIX
**Hiện tượng:** Token không có write permission

**Đã fix:** Fallback chain — submit_review → post_comment → save local

---

## Các Phases Đã Triển Khai

### Phase A: Tăng Context Window (`github_utils/client.py`) ✅

- ✅ `MAX_PATCH_CHARS = 8000` per file
- ✅ File prioritization: source code (.py, .js, .ts, etc.) → config files → skip irrelevant (.log, .bat, .png)
- ✅ Truncation thông minh với "X more file(s) (truncated)" message
- ✅ PR title + description included trong review context

### Phase B: Cải thiện Task Prompts (`tasks/tasks.py`) ✅

- ✅ Thêm anti-hallucination constraints vào mỗi task ("IMPORTANT RULES")
- ✅ Code Quality task: "Only report issues found in the ACTUAL CODE provided"
- ✅ Security task: "Do NOT flag placeholder values in .env.example"
- ✅ Performance task: "If no significant issues exist, say so — do NOT invent issues"
- ✅ Tech Lead task: "DISCARD false positives, MERGE duplicates"

### Phase C: Tối ưu KB (`kb_loader.py`) ✅

- ✅ Priority ordering: Conventions + Risks (HIGH) → Dependencies (MEDIUM) → Summaries (LOW)
- ✅ File summaries truncated to 100 chars each
- ✅ Skip KB internal files (knowledge_base/ paths)
- ✅ Safe truncation with warning message
- ✅ Schema validation (`_validate_kb_schema`)

### Phase D: Cải thiện Agent Goals (`agents/agents.py`) ✅

- ✅ Thêm anti-false-positive instructions vào backstory mỗi agent
- ✅ Security Expert: "Distinguish between REAL security risks and false positives"
- ✅ Code Reviewer: "You never fabricate issues or give generic advice"
- ✅ Performance Engineer: "You never invent problems just to have something to report"
- ✅ Tech Lead: "You actively filter out false positives from reviewers"

---

## Files Đã Thay Đổi

| File | Thay đổi | Status |
|---|---|---|
| `github_utils/client.py` | Tăng max_patch_chars, file prioritization, PR title/description | ✅ |
| `tasks/tasks.py` | Thêm IMPORTANT RULES constraints, KB injection | ✅ |
| `kb_loader.py` | Priority ordering, schema validation, safe truncation | ✅ |
| `agents/agents.py` | Anti-false-positive backstory cho tất cả agents | ✅ |