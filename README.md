# 🤖 PR Review Bot

Multi-agent code review system built with **CrewAI** and **LangChain OpenAI**.  
Four AI agents collaborate to perform a comprehensive pull request review, then **automatically post the review as a comment on your GitHub PR**.

---

## 📁 Project Structure

```
pr-review-bot/
├── agents/
│   ├── __init__.py
│   └── agents.py            # Agent definitions (4 agents)
├── tasks/
│   ├── __init__.py
│   └── tasks.py             # Task builder (dynamic code input)
├── config/
│   ├── __init__.py
│   └── settings.py          # LLM & GitHub config from .env
├── github_utils/
│   ├── __init__.py
│   └── client.py            # GitHub API client (fetch PR, post comment)
├── main.py                  # Entry point
├── .env                     # API keys & tokens
├── .env.example             # Template for .env
├── requirements.txt         # Dependencies
└── README.md
```

---

## 🧠 Agents

| Agent | Role | Focus |
|---|---|---|
| **Code Reviewer** | Senior Code Reviewer | PEP 8, naming, readability, dead code, error handling |
| **Security Expert** | Application Security Engineer | SQL injection, deserialization, weak crypto, hardcoded secrets |
| **Performance Engineer** | Performance Optimization Engineer | Inefficient loops, memory issues, algorithmic complexity |
| **Tech Lead** | Technical Lead | Synthesizes all reports → final markdown PR review |

---

## 🔄 Workflow

```
User provides PR link
        │
        ▼
┌──────────────────┐
│  GitHub API       │  Fetch PR files & diffs
└────────┬─────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐    ┌──────────────┐
│  Code Reviewer   │───▶│ Security Expert  │───▶│ Performance Engineer │───▶│  Tech Lead   │
│  (Quality)       │    │  (Vulnerabilities)│    │  (Optimization)      │    │  (Final)     │
└─────────────────┘    └─────────────────┘    └──────────────────────┘    └──────────────┘
                                                                              │
                                                                              ▼
                                                                    ┌──────────────────┐
                                                                    │  GitHub API       │  Post review comment
                                                                    └──────────────────┘
```

---

## 📋 Prerequisites

Trước khi bắt đầu, bạn cần có:

| Yêu cầu | Cách lấy | Link |
|---|---|---|
| **Python 3.10+** | Cài từ python.org hoặc winget | [python.org](https://www.python.org/downloads/) |
| **OpenAI API Key** | Tạo tại OpenAI platform | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **GitHub Personal Access Token** | Tạo tại GitHub Settings | [github.com/settings/tokens](https://github.com/settings/tokens) |

---

## 🚀 Hướng dẫn cài đặt chi tiết

### Bước 1: Clone hoặc tải dự án

```bash
cd pr-review-bot
```

### Bước 2: Tạo virtual environment

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

### Bước 3: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

> ⏳ Quá trình cài có thể mất 2-5 phút do crewai có nhiều dependencies.

---

## 🔑 Hướng dẫn cấu hình

### Bước 4: Tạo file `.env`

```bash
# Copy file mẫu
cp .env.example .env
```

### Bước 5: Cấu hình OpenAI API Key

1. Truy cập [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Nhấn **"Create new secret key"**
3. Copy key và dán vào file `.env`:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
```

**Nếu dùng provider khác** (Azure OpenAI, Groq, OpenRouter, v.v.), thay thêm `OPENAI_API_BASE`:

```env
# Ví dụ dùng OpenRouter:
OPENAI_API_BASE=https://openrouter.ai/api/v1

# Ví dụ dùng Groq:
OPENAI_API_BASE=https://api.groq.com/openai/v1

# Ví dụ dùng local LM Studio:
OPENAI_API_BASE=http://localhost:1234/v1
```

### Bước 6: Cấu hình GitHub Token

1. Truy cập [github.com/settings/tokens](https://github.com/settings/tokens)
2. Nhấn **"Generate new token (classic)"** hoặc **"Fine-grained token"**
3. Chọn quyền (scopes):
   - ✅ `repo` — Đọc PR và post comment (full repository access)
   - Hoặc với fine-grained token: **Read & Write** cho "Pull requests" và "Issues"
4. Copy token và dán vào file `.env`:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### File `.env` hoàn chỉnh:

```env
# LLM Configuration
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# GitHub Configuration
GITHUB_TOKEN=ghp-your-actual-github-token-here
```

---

## ▶️ Hướng dẫn sử dụng

### Chạy từ command line

```bash
# Kích hoạt venv trước (nếu chưa)
.venv\Scripts\activate

# Chạy review PR
python main.py https://github.com/owner/repo/pull/123
```

### Chạy bằng batch script (Windows)

```cmd
run.bat https://github.com/owner/repo/pull/123
```

### Ví dụ thực tế

```bash
# Review PR số 42 trong repo của bạn
python main.py https://github.com/myusername/myproject/pull/42

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

📥 Fetching PR files from GitHub...
✅ Fetched 5 file(s) from PR

🚀 Starting multi-agent review...

[Agent logs here...]

============================================================
  📋 Final PR Review
============================================================

[Review content]

📤 Posting review comment to GitHub PR...
✅ Review posted: https://github.com/myusername/myproject/issues/42#issuecomment-xxx

Done! ✨
```

---

## 📤 Kết quả output

Bot sẽ tự động đăng một comment trên PR của bạn với nội dung markdown cấu trúc:

```markdown
## 🤖 PR Review Bot — Automated Code Review

### Summary
| # | Category | Issue | Severity |
|---|----------|-------|----------|
| 1 | Security | SQL injection in query | 🔴 Critical |
| 2 | Security | Hardcoded API key | 🔴 Critical |
| 3 | Quality | Unused variable `items` | 🟡 Minor |
| 4 | Performance | range(len()) anti-pattern | 🟡 Minor |

### 🔴 BLOCKING Issues (must fix)
1. **SQL Injection** — Use parameterized queries
2. **Hardcoded secret** — Move to environment variable

### 🟡 NON-BLOCKING Issues (suggestions)
1. Use `for item in data` instead of `range(len())`
2. Add docstrings to `authenticate()`

### Verdict: **REQUEST CHANGES** ❌
```

> Nếu không thể post lên GitHub (network error, token hết hạn, v.v.), review sẽ được lưu vào file `review_output.md` locally.

---

## ⚙️ Configuration

Tất cả cấu hình được quản lý qua file `.env`:

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key (hoặc compatible provider) | — |
| `OPENAI_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Tên model sử dụng | `gpt-4o-mini` |
| `GITHUB_TOKEN` | GitHub Personal Access Token (cần `repo` scope) | — |

### Thay đổi model

```env
# Dùng GPT-4o (chất lượng tốt hơn, giá cao hơn):
LLM_MODEL=gpt-4o

# Dùng GPT-4o-mini (mặc định, tiết kiệm chi phí):
LLM_MODEL=gpt-4o-mini

# Dùng GPT-3.5 Turbo (rẻ nhất):
LLM_MODEL=gpt-3.5-turbo
```

---

## 🐛 Troubleshooting

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `ModuleNotFoundError: No module named 'crewai'` | Chưa cài dependencies | Chạy `pip install -r requirements.txt` |
| `❌ GITHUB_TOKEN not configured` | Chưa set token trong `.env` | Thêm `GITHUB_TOKEN=ghp-xxx` vào `.env` |
| `❌ Invalid PR URL` | Sai format URL | Đảm bảo URL có dạng `https://github.com/owner/repo/pull/123` |
| `❌ Failed to fetch PR: 401` | GitHub token không hợp lệ | Tạo token mới và kiểm tra quyền `repo` |
| `❌ Failed to fetch PR: 404` | PR không tồn tại hoặc token không có quyền truy cập | Kiểm tra URL và quyền của token |
| `❌ Failed to post comment: 403` | Token không có quyền write | Cấp quyền `repo` cho token |
| `Connection error` | Không có internet hoặc firewall chặn | Kiểm tra kết nối mạng |

---

## 📦 Dependencies

- [`crewai`](https://github.com/crewAIInc/crewAI) — Multi-agent orchestration framework
- [`langchain-openai`](https://github.com/langchain-ai/langchain) — OpenAI LLM integration for LangChain
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — Load environment variables from `.env` file
- [`httpx`](https://github.com/encode/httpx) — HTTP client for GitHub API (installed with crewai)

---

## 📌 Constraints

- ✅ Simple and runnable — chỉ cần cung cấp PR link
- ✅ Tự động comment trên GitHub PR
- ✅ Hỗ trợ mọi OpenAI-compatible LLM provider
- ✅ Fallback lưu local file nếu GitHub lỗi
- ✅ Không cần webhook hay server — chạy locally

---

## 📄 License

MIT
 File `.env` hoàn chỉnh:

```env
# LLM Configuration
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# GitHub Configuration
GITHUB_TOKEN=ghp-your-actual-github-token-here
```

---

## ▶️ Hướng dẫn sử dụng

### Chạy từ command line

```bash
# Kích hoạt venv trước (nếu chưa)
.venv\Scripts\activate

# Chạy review PR
python main.py https://github.com/owner/repo/pull/123
```

### Chạy bằng batch script (Windows)

```cmd
run.bat https://github.com/owner/repo/pull/123
```

### Ví dụ thực tế

```bash
# Review PR số 42 trong repo của bạn
python main.py https://github.com/myusername/myproject/pull/42

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

📥 Fetching PR files from GitHub...
✅ Fetched 5 file(s) from PR

🚀 Starting multi-agent review...

[Agent logs here...]

============================================================
  📋 Final PR Review
============================================================

[Review content]

📤 Posting review comment to GitHub PR...
✅ Review posted: https://github.com/myusername/myproject/issues/42#issuecomment-xxx

Done! ✨
```

---

## 📤 Kết quả output

Bot sẽ tự động đăng một comment trên PR của bạn với nội dung markdown cấu trúc:

```markdown
## 🤖 PR Review Bot — Automated Code Review

### Summary
| # | Category | Issue | Severity |
|---|----------|-------|----------|
| 1 | Security | SQL injection in query | 🔴 Critical |
| 2 | Security | Hardcoded API key | 🔴 Critical |
| 3 | Quality | Unused variable `items` | 🟡 Minor |
| 4 | Performance | range(len()) anti-pattern | 🟡 Minor |

### 🔴 BLOCKING Issues (must fix)
1. **SQL Injection** — Use parameterized queries
2. **Hardcoded secret** — Move to environment variable

### 🟡 NON-BLOCKING Issues (suggestions)
1. Use `for item in data` instead of `range(len())`
2. Add docstrings to `authenticate()`

### Verdict: **REQUEST CHANGES** ❌
```

> Nếu không thể post lên GitHub (network error, token hết hạn, v.v.), review sẽ được lưu vào file `review_output.md` locally.

---

## ⚙️ Configuration

Tất cả cấu hình được quản lý qua file `.env`:

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key (hoặc compatible provider) | — |
| `OPENAI_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Tên model sử dụng | `gpt-4o-mini` |
| `GITHUB_TOKEN` | GitHub Personal Access Token (cần `repo` scope) | — |

### Thay đổi model

```env
# Dùng GPT-4o (chất lượng tốt hơn, giá cao hơn):
LLM_MODEL=gpt-4o

# Dùng GPT-4o-mini (mặc định, tiết kiệm chi phí):
LLM_MODEL=gpt-4o-mini

# Dùng GPT-3.5 Turbo (rẻ nhất):
LLM_MODEL=gpt-3.5-turbo
```

---

## 🐛 Troubleshooting

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `ModuleNotFoundError: No module named 'crewai'` | Chưa cài dependencies | Chạy `pip install -r requirements.txt` |
| `❌ GITHUB_TOKEN not configured` | Chưa set token trong `.env` | Thêm `GITHUB_TOKEN=ghp-xxx` vào `.env` |
| `❌ Invalid PR URL` | Sai format URL | Đảm bảo URL có dạng `https://github.com/owner/repo/pull/123` |
| `❌ Failed to fetch PR: 401` | GitHub token không hợp lệ | Tạo token mới và kiểm tra quyền `repo` |
| `❌ Failed to fetch PR: 404` | PR không tồn tại hoặc token không có quyền truy cập | Kiểm tra URL và quyền của token |
| `❌ Failed to post comment: 403` | Token không có quyền write | Cấp quyền `repo` cho token |
| `Connection error` | Không có internet hoặc firewall chặn | Kiểm tra kết nối mạng |

---

## 📦 Dependencies

- [`crewai`](https://github.com/crewAIInc/crewAI) — Multi-agent orchestration framework
- [`langchain-openai`](https://github.com/langchain-ai/langchain) — OpenAI LLM integration for LangChain
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — Load environment variables from `.env` file
- [`httpx`](https://github.com/encode/httpx) — HTTP client for GitHub API (installed with crewai)

---

## 📌 Constraints

- ✅ Simple and runnable — chỉ cần cung cấp PR link
- ✅ Tự động comment trên GitHub PR
- ✅ Hỗ trợ mọi OpenAI-compatible LLM provider
- ✅ Fallback lưu local file nếu GitHub lỗi
- ✅ Không cần webhook hay server — chạy locally

---

## 📄 License

