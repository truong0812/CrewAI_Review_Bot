# Usage Guide — PR Review Bot

Hướng dẫn cài đặt, cấu hình và sử dụng PR Review Bot.

---

## Prerequisites

| Yêu cầu | Cách lấy | Link |
|---|---|---|
| **Python 3.10+** | Cài từ python.org hoặc winget | [python.org](https://www.python.org/downloads/) |
| **LLM API Key** | OpenAI, NVIDIA NIM, Groq, hoặc OpenRouter | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **GitHub Personal Access Token** | Tạo tại GitHub Settings (cần `repo` scope) | [github.com/settings/tokens](https://github.com/settings/tokens) |

---

## Cài đặt

### 1. Clone hoặc tải dự án

```bash
cd pr-review-bot
```

### 2. Tạo virtual environment

```bash
# Tạo venv
python -m venv .venv

# Kích hoạt venv
# Windows CMD:
.venv\Scripts\activate.bat

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Linux/macOS:
source .venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

Hoặc dùng script Windows:
```cmd
install.bat
```

> ⏳ Quá trình cài có thể mất 2-5 phút do crewai có nhiều dependencies.

---

## Cấu hình

### 4. Tạo file `.env`

```bash
cp .env.example .env
```

### 5. Cấu hình LLM API Key

1. Truy cập provider API (OpenAI, NVIDIA NIM, Groq, v.v.)
2. Tạo API key
3. Copy key và dán vào file `.env`:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
```

**Nếu dùng provider khác** (NVIDIA NIM, Groq, OpenRouter, v.v.), thay `OPENAI_API_BASE`:

```env
# NVIDIA NIM:
OPENAI_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=meta/llama-3.3-70b-instruct

# OpenRouter:
OPENAI_API_BASE=https://openrouter.ai/api/v1

# Groq:
OPENAI_API_BASE=https://api.groq.com/openai/v1

# Local LM Studio:
OPENAI_API_BASE=http://localhost:1234/v1
```

### 6. Cấu hình GitHub Token

1. Truy cập [github.com/settings/tokens](https://github.com/settings/tokens)
2. Nhấn **"Generate new token (classic)"** hoặc **"Fine-grained token"**
3. Chọn quyền (scopes):
   - ✅ `repo` — Đọc PR và submit review (full repository access)
   - Hoặc với fine-grained token: **Read & Write** cho "Pull requests" và "Issues"
4. Copy token và dán vào file `.env`:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 7. Cấu hình Knowledge Base (tùy chọn)

Nếu bạn có Knowledge Base JSON cho dự án, đặt nó vào thư mục `knowledge_base/` và cấu hình:

```env
KB_PATH=knowledge_base/CrewAI_Review_Bot
KB_MAX_CHARS=8000
```

> KB sẽ cung cấp context về coding conventions, risk areas, file summaries và dependencies cho agents.

### File `.env` hoàn chỉnh

```env
# LLM Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# GitHub Configuration
GITHUB_TOKEN=ghp-your-github-token-here
API_TIMEOUT=30
REVIEW_OUTPUT_PATH=

# Review Configuration
REVIEW_LANGUAGE=en

# Knowledge Base Configuration
KB_PATH=knowledge_base/CrewAI_Review_Bot
KB_MAX_CHARS=8000
```

> **Lưu ý khi dùng provider khác OpenAI:** Project khởi tạo LLM với `base_url=OPENAI_API_BASE` trong `agents/agents.py`, nên hỗ trợ mọi OpenAI-compatible provider.

---

## Sử dụng

### Chạy từ command line

```bash
# Kích hoạt venv trước (nếu chưa)
.venv\Scripts\activate

# Chạy review PR (không KB)
python main.py https://github.com/owner/repo/pull/123

# Chạy review PR với Knowledge Base
python main.py https://github.com/owner/repo/pull/123 knowledge_base/CrewAI_Review_Bot
```

### Chạy bằng batch script (Windows)

```cmd
run.bat https://github.com/owner/repo/pull/123
```

### Ví dụ thực tế

```bash
# Review PR số 42 trong repo của bạn (không KB)
python main.py https://github.com/myusername/myproject/pull/42

# Review PR với Knowledge Base context
python main.py https://github.com/myusername/myproject/pull/42 knowledge_base/CrewAI_Review_Bot

# Review PR trong organization
python main.py https://github.com/myorg/frontend-app/pull/158
```

### Kết quả trên terminal

```
============================================================
  🤖 PR Review Bot — Multi-Agent Code Review
============================================================
  📌 PR: myusername/myproject#42
  🔗 https://github.com/myusername/myproject/pull/42

📚 Loading Knowledge Base from: knowledge_base/CrewAI_Review_Bot
✅ KB loaded (4521 chars)

📥 Fetching PR files from GitHub...
✅ Fetched 5 file(s) from PR

🚀 Starting multi-agent review...
   (with Knowledge Base context)

[Agent logs here...]

⚖️  Parsed verdict: REQUEST_CHANGES

📤 Submitting review to GitHub PR...
   HEAD commit: abc123def456...
✅ Review submitted (REQUEST_CHANGES): https://github.com/...

Done! ✨
```

---

## Output Format

Bot submit một **formal GitHub review** trên PR với status **APPROVE** hoặc **REQUEST CHANGES**.
Review được viết theo style của senior colleague — có lời chào author, khen ngợi, numbered issues, và kết luận tự nhiên.

### Khi không có issues (LGTM)

```markdown
Hi @dev, I've reviewed the PR.

**Assessment:**
- The component structure is clean and well-organized.
- Error handling covers edge cases properly.
- Good use of project conventions.

Looks good to me. Approved! 🦾

VERDICT: APPROVE
```

### Khi có issues

```markdown
## 📝 Review

Hi @dev, found 1 issue that should be fixed before merging — string interpolation
in the query builder is vulnerable to SQL injection. Overall clean work though!

### ✅ Good Points
- Clean separation of concerns in the API layer
- Proper error handling in the main module

### ⚠️ Needs Fixing
1. **SQL injection in query builder** (`db/query.py:42`)
   ```python
   query = f"SELECT * FROM users WHERE id = {user_id}"
   ```
   String interpolation in SQL query allows injection attacks.
   Fix: Use parameterized queries.

### 💡 Suggestions (non-blocking)
- `main.py:10` — Unused import, consider removing to keep the file clean.

### Conclusion
Fix the SQL injection and we're good to merge. Solid work overall!

VERDICT: REQUEST CHANGES
```

### Khi dùng tiếng Việt (`REVIEW_LANGUAGE=vi`)

Section headers tự động chuyển sang tiếng Việt:

```markdown
## 📝 Review

Chào @dev, mình thấy PR này có một số điểm làm tốt và cũng có vài điểm cần cải tiến.

### ✅ Điểm tốt
- Cấu trúc code rõ ràng, dễ theo dõi

### ⚠️ Cần xử lý
1. **Excessive logging** (`src/api/client.ts:68`)
   ...

### 💡 Góp ý nhỏ
- ...

### Kết luận
Code nhìn chung đã ổn, chỉ cần khắc phục phần log là có thể merge được!

VERDICT: REQUEST CHANGES
```

### Fallback chain

Nếu không thể submit formal review, bot thử theo thứ tự:
1. **Formal Review API** — Submit review với status (APPROVE / REQUEST CHANGES / COMMENT)
2. **Issue Comment** — Post review như comment thường
3. **Local File** — Lưu vào `review_output.md` locally

---

## Configuration Reference

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key (hoặc compatible provider) | — |
| `OPENAI_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Tên model sử dụng | `gpt-4o-mini` |
| `GITHUB_TOKEN` | GitHub Personal Access Token (cần `repo` scope) | — |
| `API_TIMEOUT` | Timeout cho GitHub API calls (giây) | `30` |
| `REVIEW_OUTPUT_PATH` | Đường dẫn lưu review local (khi GitHub fail) | `review_output.md` |
| `REVIEW_LANGUAGE` | Ngôn ngữ review output — hỗ trợ `en` (English) và `vi` (Vietnamese) | `en` |
| `KB_PATH` | Đường dẫn tới thư mục Knowledge Base | `""` (tắt) |
| `KB_MAX_CHARS` | Giới hạn ký tự cho KB context | `8000` |

### Thay đổi model

```env
# GPT-4o (chất lượng tốt nhất, giá cao):
LLM_MODEL=gpt-4o

# GPT-4o-mini (tiết kiệm chi phí):
LLM_MODEL=gpt-4o-mini

# NVIDIA NIM Llama 3.3 70B:
OPENAI_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=meta/llama-3.3-70b-instruct

# Groq Llama 3.1 (miễn phí, nhanh):
OPENAI_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
```

### Thay đổi ngôn ngữ review

Hiện tại bot hỗ trợ 2 ngôn ngữ:

```env
# English (mặc định)
REVIEW_LANGUAGE=en

# Tiếng Việt
REVIEW_LANGUAGE=vi
```

> **Lưu ý:** Khi đổi ngôn ngữ, section headers (Good Points / Needs Fixing / Suggestions / Conclusion) sẽ tự động chuyển sang ngôn ngữ tương ứng (Điểm tốt / Cần xử lý / Góp ý nhỏ / Kết luận).

---

## Knowledge Base

Project hỗ trợ tích hợp **Knowledge Base** để cung cấp context cho agents.

### Format KB

KB được lưu dưới dạng JSON (`latest.json`) với cấu trúc:

| Section | Mô tả | Priority |
|---|---|---|
| **Conventions** | Coding patterns, naming conventions | 🔴 HIGH |
| **Risks** | Risk areas (authentication, secrets, external APIs) | 🔴 HIGH |
| **Dependencies** | Quan hệ imports/depends_on giữa files | 🟡 MEDIUM |
| **Summaries** | Mô tả ngắn gọn từng file | 🟢 LOW |

### Cách KB hoạt động

1. `kb_loader.py` đọc `latest.json` từ thư mục KB
2. Trích xuất conventions, risks, dependencies, summaries
3. Format thành markdown block
4. Inject vào task descriptions của 3 agents đầu (Code Reviewer, Security, Performance)
5. Agents sử dụng KB context để review theo chuẩn dự án

### Cấu trúc thư mục KB

```
knowledge_base/
└── YourProject/
    ├── latest.json           # Snapshot hiện tại
    ├── metadata.json         # Metadata (branch, commit, stats)
    ├── USE_GUIDE.md          # Hướng dẫn sử dụng KB
    ├── indexes/
    │   └── semantic_index.json
    └── snapshots/
        └── 2026-05-06/
```

---

## Troubleshooting

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `ModuleNotFoundError: No module named 'crewai'` | Chưa cài dependencies | Chạy `pip install -r requirements.txt` |
| `❌ GITHUB_TOKEN not configured` | Chưa set token trong `.env` | Thêm `GITHUB_TOKEN=ghp-xxx` vào `.env` |
| `❌ Invalid PR URL` | Sai format URL | Đảm bảo URL có dạng `https://github.com/owner/repo/pull/123` |
| `❌ Failed to fetch PR: 401` | GitHub token không hợp lệ | Tạo token mới và kiểm tra quyền `repo` |
| `❌ Failed to fetch PR: 404` | PR không tồn tại hoặc token không có quyền | Kiểm tra URL và quyền của token |
| `❌ Failed to submit review: 403` | Token không có quyền write | Cấp quyền `repo` cho token |
| `⚠️ KB file not found` | Sai đường dẫn KB | Kiểm tra `KB_PATH` trong `.env` |
| `⚠️ KB file has invalid schema` | File JSON corrupt hoặc sai format | Kiểm tra `latest.json` có key `files` dạng list |
| `Connection error` | Không có internet hoặc firewall chặn | Kiểm tra kết nối mạng |
| `Incorrect API key provided` (401) | Dùng provider key nhưng base URL sai | Đảm bảo `OPENAI_API_BASE` được set đúng |
| `Crew Execution Failed` (context limit) | PR quá lớn, vượt context window | Dùng model có context lớn hơn hoặc giảm `KB_MAX_CHARS` |
