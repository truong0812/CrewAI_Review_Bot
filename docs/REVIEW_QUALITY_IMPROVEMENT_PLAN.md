# Plan Cải Thiện Chất Lượng Review

## Phân tích vấn đề hiện tại

### Vấn đề 1: Context Truncation (NGHIÊM TRỌNG)
**Hiện tượng:** Model báo "main.py not provided for review", "tasks/tasks.py not provided for review"

**Nguyên nhân:** 
- `get_pr_code_for_review()` giới hạn `max_chars=12000`
- KB context chiếm `5587 chars` → thực tế chỉ còn ~6400 chars cho code
- PR có 5 files → 2 files cuối bị truncate

**Fix:**
1. Tăng `max_chars` từ 12000 → 30000 (model 70B có context 128k)
2. Tăng `max_patch_chars` từ 3000 → 8000 per file
3. Ưu tiên file `.py` trước, bỏ qua file `.env.example`, `.bat`, log files

### Vấn đề 2: False Positives
**Hiện tượng:** Flag `.env.example` placeholder là "hardcoded secret", flag `os.getenv()` là "secret"

**Fix:** Cải thiện task prompts — thêm "IMPORTANT" constraints

### Vấn đề 3: Generic Findings
**Hiện tượng:** "Inefficient loop", "Memory inefficiency" không kèm code cụ thể

**Fix:** Yêu cầu agents trích dẫn code cụ thể và giải thích tại sao

### Vấn đề 4: GitHub 403
**Hiện tượng:** Token không có write permission

**Fix:** Cần user cấp token với scope `repo`

---

## Plan triển khai

### Phase A: Tăng Context Window (github_utils/client.py)
- [ ] Tăng `max_chars` mặc định từ 12000 → 30000
- [ ] Tăng `max_patch_chars` từ 3000 → 8000
- [ ] Thêm logic ưu tiên Python files, skip irrelevant files (.bat, .log, .txt)

### Phase B: Cải thiện Task Prompts (tasks/tasks.py)
- [ ] Thêm anti-hallucination constraints vào mỗi task
- [ ] Code Quality task: "DO NOT flag .env.example placeholder values as secrets"
- [ ] Security task: "Only report REAL hardcoded secrets (actual API keys, tokens, passwords), NOT placeholder/example values"
- [ ] Performance task: "Provide SPECIFIC code examples, NOT generic advice"
- [ ] Tech Lead task: "Discard duplicate or invalid findings from reviewers"

### Phase C: Giảm KB Size (kb_loader.py)
- [ ] Giảm default `KB_MAX_CHARS` từ 8000 → 3000
- [ ] Chỉ giữ: Conventions + Risk Areas (bỏ File Summaries quá dài)
- [ ] Hoặc: Summarize file summaries thành 1 dòng thay vì paragraph

### Phase D: Cải thiện Agent Goals (agents/agents.py)
- [ ] Thêm instruction tránh false positives vào backstory
- [ ] Security Expert: "Distinguish between example/template files and actual source code"

---

## Files cần thay đổi

| File | Thay đổi | Ưu tiên |
|---|---|---|
| `github_utils/client.py` | Tăng max_chars, ưu tiên .py files | 🔴 HIGH |
| `tasks/tasks.py` | Cải thiện prompts với constraints | 🔴 HIGH |
| `kb_loader.py` | Giảm KB size, ưu tiên info quan trọng | 🟡 MEDIUM |
| `agents/agents.py` | Cải thiện backstory tránh false positives | 🟡 MEDIUM |
| `.env` | Tăng `max_chars` config | 🟢 LOW |

## Thứ tự triển khai
1. **Phase A** (client.py) — Sửa truncation, tăng context
2. **Phase B** (tasks.py) — Cải thiện prompts
3. **Phase C** (kb_loader.py) — Tối ưu KB
4. **Phase D** (agents.py) — Cải thiện agent instructions
5. **Test lại** với PR #3