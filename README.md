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
| **LLM API Key** | OpenAI, Groq, hoặc OpenRouter | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
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

### Bước 5: Cấu hình LLM API Key

1. Truy cập [platform.openai.com/api-keys](https://platform.openai.com/api-keys) (hoặc provider khác)
2. Tạo API key
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

> **💡 Lưu ý khi dùng Groq:** CrewAI đọc env var `OPENAI_BASE_URL` (internal). Project đã tự động map từ `OPENAI_API_BASE` sang `OPENAI_BASE_URL` trong `agents/agents.py`.

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

# Dùng Groq Llama 3.1 (miễn phí, nhanh):
OPENAI_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
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
| `Incorrect API key provided` (OpenAI 401) | Dùng Groq key nhưng CrewAI gửi đến OpenAI | Đảm bảo `OPENAI_API_BASE` được set đúng trong `.env` |
| `Crew Execution Failed` (context limit) | PR quá lớn, vượt context window của LLM | Dùng model có context lớn hơn (GPT-4o, Groq `llama-3.1-70b`) |

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

## 🔮 Các vấn đề đã biết & Hướng cải thiện

### Vấn đề đã biết

| # | Vấn đề | Mô tả | Mức độ |
|---|--------|-------|--------|
| 1 | **Context limit khi PR lớn** | PR có nhiều files/diffs lớn có thể vượt context window của model (đặc biệt với `llama-3.1-8b-instant` — 128K tokens). Đã có truncation cơ bản (12K chars) nhưng chưa tối ưu. | 🟡 Medium |
| 2 | **Agent reviews chạy chậm** | 4 agents chạy sequential, mỗi agent gọi LLM riêng → tổng thời gian 2-5 phút/PR. Chưa tận dụng được parallel execution. | 🟡 Medium |
| 3 | **Review chất lượng phụ thuộc model** | Model nhỏ (`llama-3.1-8b-instant`) đôi khi đưa ra feedback chung chung, thiếu cụ thể. GPT-4o cho kết quả tốt hơn nhiều. | 🟡 Medium |
| 4 | **Không có caching** | Mỗi lần chạy đều fetch lại PR từ GitHub và gọi LLM mới. Không cache kết quả cho các lần chạy lặp lại. | 🟢 Low |
| 5 | **Error handling cơ bản** | Chưa có retry logic khi API lỗi tạm thời (rate limit, network timeout). | 🟢 Low |
| 6 | **Windows long path issue** | Không cài được `litellm` trên Windows nếu chưa bật Long Paths (cần admin quyền). | 🟢 Low |

### Hướng cải thiện

#### 🏗️ Architecture
- [ ] **Chạy agents song song (hierarchical process)**: Cho phép Code Reviewer, Security Expert, Performance Engineer chạy đồng thời → giảm thời gian review xuống ~1/3.
- [ ] **Streaming output**: Hiển thị kết quả từng agent real-time thay vì đợi tất cả xong.
- [ ] **Add more agents**: Thêm agent chuyên review tests, docs, dependencies.

#### 🧠 LLM & Context
- [ ] **Smart context management**: Thay vì truncate cơ bản, dùng RAG hoặc summarization để chọn đoạn code quan trọng nhất.
- [ ] **Chunked review**: Chia PR lớn thành các chunk nhỏ, review từng phần rồi tổng hợp.
- [ ] **Support more models**: Thêm support cho Anthropic Claude, Google Gemini (qua litellm khi fix được long path issue).
- [ ] **Custom temperature/settings**: Cho phép cấu hình temperature, max_tokens cho từng agent riêng.

#### 🔗 GitHub Integration
- [ ] **Inline review comments**: Post comment trực tiếp trên từng line diff (GitHub Review API) thay vì một comment tổng.
- [ ] **PR event webhook**: Tự động chạy review khi có PR mới (cần server).
- [ ] **GitHub Actions integration**: Chạy bot như một GitHub Action.
- [ ] **Rate limiting**: Tự động delay giữa các API calls để tránh rate limit.

#### 📊 Quality & UX
- [ ] **Review history**: Lưu lịch sử review vào database (SQLite) để theo dõi xu hướng.
- [ ] **Configurable rules**: Cho phép custom rules per project (ví dụ: bỏ qua certain files, set severity threshold).
- [ ] **Rich terminal output**: Dùng `rich` library cho terminal output đẹp hơn với colors, tables, progress bars.
- [ ] **Review score**: Tính điểm chất lượng PR (A/B/C/D/F) dựa trên số lượng và severity của issues.

#### 🛡️ Reliability
- [ ] **Retry logic**: Tự động retry khi LLM API lỗi (exponential backoff).
- [ ] **Graceful degradation**: Nếu 1 agent fail, vẫn chạy agents còn lại và tổng hợp kết quả riêng phần.
- [ ] **Unit tests**: Thêm test suite cho agents, tasks, và GitHub client.
- [ ] **CI/CD pipeline**: Tự động test khi push code.

---

## 📄 License

MIT