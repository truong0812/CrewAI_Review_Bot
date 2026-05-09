# Usage Guide — PR Review Bot

Hướng dẫn cài đặt, cấu hình và sử dụng PR Review Bot CLI.

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

### 3. Cài đặt package

```bash
pip install -e .
```

Lệnh này cài tất cả dependencies và đăng ký CLI command `pr-review`.

> ⏳ Quá trình cài có thể mất 2-5 phút do crewai có nhiều dependencies.

---

## Thiết lập lần đầu

### Dùng `pr-review init` (interactive)

```bash
pr-review init
```

CLI sẽ tạo file `.env` từ template và hỏi các giá trị cần thiết:

```
Configure your settings (press Enter to keep default):

  OPENAI_API_KEY:
  OPENAI_API_BASE [https://api.openai.com/v1]:
  LLM_MODEL [gpt-4o-mini]:
  GITHUB_TOKEN:
  REVIEW_LANGUAGE [en]:
```

### Hoặc thủ công

```bash
cp .env.example .env
# Sau đó chỉnh sửa file .env với API key và token của bạn
```

---

## Sử dụng

### `pr-review review` — Review PR

```bash
# Cơ bản — review một PR
pr-review review https://github.com/owner/repo/pull/123

# Với Knowledge Base
pr-review review https://github.com/owner/repo/pull/123 -k knowledge_base/CrewAI_Review_Bot

# Chạy review tiếng Việt
pr-review review https://github.com/owner/repo/pull/123 -l vi

# Dry run — không submit lên GitHub, chỉ lưu local
pr-review review https://github.com/owner/repo/pull/123 --dry-run -o review.md

# Verbose — xem chi tiết agent logs
pr-review review https://github.com/owner/repo/pull/123 -v
```

#### Tất cả options

| Option | Short | Mô tả |
|---|---|---|
| `--kb-path PATH` | `-k` | Đường dẫn Knowledge Base (override .env) |
| `--language LANG` | `-l` | Ngôn ngữ review: `en` hoặc `vi` (override .env) |
| `--output PATH` | `-o` | File lưu review local (khi dry-run hoặc fallback) |
| `--dry-run` | — | Chạy review nhưng không submit lên GitHub |
| `--verbose` | `-v` | Hiển thị chi tiết agent logs |

### `pr-review config` — Xem / thay đổi cấu hình

```bash
# Hiển thị tất cả settings hiện tại
pr-review config

# Thay đổi một giá trị (ghi vào .env)
pr-review config --set LLM_MODEL gpt-4o
pr-review config --set REVIEW_LANGUAGE vi
pr-review config --set GITHUB_TOKEN ghp_newtoken123
```

Output của `pr-review config`:

```
Config (from /path/to/.env):
--------------------------------------------------
  OPENAI_API_KEY                 nvap...c1sp
  OPENAI_API_BASE                https://integrate.api.nvidia.com/v1
  LLM_MODEL                      qwen/qwen3-coder-480b-a35b-instruct
  GITHUB_TOKEN                   ghp_...t6Yf
  API_TIMEOUT                    30
  REVIEW_LANGUAGE                vi
  ...
--------------------------------------------------
```

> API keys và tokens tự động được mask trong output.

### `pr-review init` — Khởi tạo cấu hình

```bash
# Tạo .env lần đầu
pr-review init

# Ghi đè .env cũ (backup tự động)
pr-review init --force
```

### Chạy bằng batch script (Windows)

```cmd
run.bat review https://github.com/owner/repo/pull/123
```

### Backward compatibility

Cách cũ vẫn hoạt động:

```bash
python main.py https://github.com/owner/repo/pull/123
```

Sẽ tự động chuyển sang `pr-review review`.

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

Looks good to me. Approved!

VERDICT: APPROVE
```

### Khi có issues

```markdown
## Review

Hi @dev, found 1 issue that should be fixed before merging — string interpolation
in the query builder is vulnerable to SQL injection. Overall clean work though!

### Good Points
- Clean separation of concerns in the API layer
- Proper error handling in the main module

### Needs Fixing
1. **SQL injection in query builder** (`db/query.py:42`)
   ```python
   query = f"SELECT * FROM users WHERE id = {user_id}"
   ```
   String interpolation in SQL query allows injection attacks.
   Fix: Use parameterized queries.

### Suggestions (non-blocking)
- `main.py:10` — Unused import, consider removing to keep the file clean.

### Conclusion
Fix the SQL injection and we're good to merge. Solid work overall!

VERDICT: REQUEST CHANGES
```

### Khi dùng tiếng Việt (`-l vi` hoặc `REVIEW_LANGUAGE=vi`)

Section headers tự động chuyển sang tiếng Việt:

```markdown
## Review

Chào @dev, mình thấy PR này có một số điểm làm tốt và cũng có vài điểm cần cải tiến.

### Điểm tốt
- Cấu trúc code rõ ràng, dễ theo dõi

### Cần xử lý
1. **Excessive logging** (`src/api/client.ts:68`)
   ...

### Góp ý nhỏ
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

```bash
# Dùng CLI:
pr-review config --set LLM_MODEL gpt-4o
pr-review config --set OPENAI_API_BASE https://integrate.api.nvidia.com/v1
```

Hoặc chỉnh `.env` trực tiếp:

```env
# GPT-4o (chất lượng tốt nhất, giá cao):
LLM_MODEL=gpt-4o

# NVIDIA NIM Llama 3.3 70B:
OPENAI_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=meta/llama-3.3-70b-instruct

# Groq Llama 3.1 (miễn phí, nhanh):
OPENAI_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant

# OpenRouter:
OPENAI_API_BASE=https://openrouter.ai/api/v1

# Local LM Studio:
OPENAI_API_BASE=http://localhost:1234/v1
```

### Thay đổi ngôn ngữ review

```bash
# Dùng CLI option (một lần):
pr-review review <url> -l vi

# Hoặc thay đổi mặc định:
pr-review config --set REVIEW_LANGUAGE vi
```

> Khi đổi ngôn ngữ, section headers (Good Points / Needs Fixing / Suggestions / Conclusion) sẽ tự động chuyển sang ngôn ngữ tương ứng (Điểm tốt / Cần xử lý / Góp ý nhỏ / Kết luận).

---

## Knowledge Base

Project hỗ trợ tích hợp **Knowledge Base** để cung cấp context cho agents.

### Format KB

KB được lưu dưới dạng JSON (`latest.json`) với cấu trúc:

| Section | Mô tả | Priority |
|---|---|---|
| **Conventions** | Coding patterns, naming conventions | HIGH |
| **Risks** | Risk areas (authentication, secrets, external APIs) | HIGH |
| **Dependencies** | Quan hệ imports/depends_on giữa files | MEDIUM |
| **Summaries** | Mô tả ngắn gọn từng file | LOW |

### Sử dụng KB

```bash
# Qua CLI option:
pr-review review <url> -k knowledge_base/CrewAI_Review_Bot

# Hoặc set mặc định trong .env:
pr-review config --set KB_PATH knowledge_base/CrewAI_Review_Bot
```

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
| `pr-review: command not found` | Chưa cài package | Chạy `pip install -e .` |
| `ModuleNotFoundError: No module named 'crewai'` | Chưa cài dependencies | Chạy `pip install -e .` |
| `GITHUB_TOKEN not configured` | Chưa set token | Chạy `pr-review init` hoặc `pr-review config --set GITHUB_TOKEN ghp_xxx` |
| `Invalid PR URL` | Sai format URL | Đảm bảo URL có dạng `https://github.com/owner/repo/pull/123` |
| `Failed to fetch PR: 401` | GitHub token không hợp lệ | Tạo token mới và kiểm tra quyền `repo` |
| `Failed to fetch PR: 404` | PR không tồn tại hoặc token không có quyền | Kiểm tra URL và quyền của token |
| `Failed to submit review: 403` | Token không có quyền write | Cấp quyền `repo` cho token |
| `KB file not found` | Sai đường dẫn KB | Kiểm tra `KB_PATH` qua `pr-review config` |
| `KB file has invalid schema` | File JSON corrupt hoặc sai format | Kiểm tra `latest.json` có key `files` dạng list |
| `Connection error` | Không có internet hoặc firewall chặn | Kiểm tra kết nối mạng |
| `Incorrect API key provided` (401) | Dùng provider key nhưng base URL sai | Đảm bảo `OPENAI_API_BASE` được set đúng |
| `Crew Execution Failed` (context limit) | PR quá lớn, vượt context window | Dùng model có context lớn hơn hoặc giảm `KB_MAX_CHARS` |
