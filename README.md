# 🤖 PR Review Bot

Multi-agent code review system built with **CrewAI** and **LangChain OpenAI**.  
Four AI agents collaborate to perform a comprehensive pull request review, enriched with **project Knowledge Base context**, then **automatically submit a formal review (APPROVE / REQUEST CHANGES) on your GitHub PR**.

---

## 📁 Project Structure

```
pr-review-bot/
├── agents/
│   ├── __init__.py
│   └── agents.py            # Agent definitions (4 agents)
├── tasks/
│   ├── __init__.py
│   └── tasks.py             # Task builder (dynamic code + KB input)
├── config/
│   ├── __init__.py
│   └── settings.py          # LLM, GitHub & KB config from .env
├── github_utils/
│   ├── __init__.py
│   └── client.py            # GitHub API client (fetch PR, submit review, post comment)
├── knowledge_base/
│   └── CrewAI_Review_Bot/   # Project KB (latest.json, conventions, risks, summaries)
├── kb_loader.py              # Knowledge Base loader (JSON → formatted context)
├── main.py                   # Entry point (orchestrator)
├── .env                      # API keys & tokens
├── .env.example              # Template for .env
├── requirements.txt          # Dependencies
├── run.bat                   # Windows quick-run script
├── install.bat               # Windows dependency installer
└── README.md
```

---

## 🧠 Agents

| Agent | Role | Focus |
|---|---|---|
| **Code Reviewer** | Senior Code Reviewer | PEP 8, naming, readability, dead code, error handling, project-specific standards |
| **Security Expert** | Application Security Engineer | SQL injection, deserialization, weak crypto, hardcoded secrets, project-specific security policies |
| **Performance Engineer** | Performance Optimization Engineer | Inefficient loops, memory issues, algorithmic complexity, project-specific perf requirements |
| **Tech Lead** | Technical Lead | Synthesizes all reports → final markdown PR review with **VERDICT: APPROVE / REQUEST CHANGES** |

> Tất cả agents đều được thiết kế để **chỉ báo cáo issues thực tế**, tránh false positives (không flag `.env.example` placeholders, không báo generic advice).

---

## 🔄 Workflow

```
User provides PR link + optional KB path
         │
         ▼
┌──────────────────┐
│  GitHub API       │  Fetch PR files, diffs, title, description
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Knowledge Base   │  Load conventions, risks, dependencies, summaries
│  (optional)       │  from latest.json
└────────┬─────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐    ┌──────────────┐
│  Code Reviewer   │───▶│ Security Expert  │───▶│ Performance Engineer │───▶│  Tech Lead   │
│  (Quality)       │    │  (Vulnerabilities)│    │  (Optimization)      │    │  (Final)     │
│  + KB context    │    │  + KB context    │    │  + KB context        │    │  + Verdict   │
└─────────────────┘    └─────────────────┘    └──────────────────────┘    └──────────────┘
                                                                               │
                                                                               ▼
                                                                    ┌──────────────────┐
                                                                    │  Parse Verdict    │  APPROVE / REQUEST_CHANGES / COMMENT
                                                                    └────────┬─────────┘
                                                                             │
                                                                             ▼
                                                                    ┌──────────────────┐
                                                                    │  GitHub Review API│  Submit formal review
                                                                    │  (fallback:       │  with status
                                                                    │   comment → file) │
                                                                    └──────────────────┘
```

---

## 📋 Prerequisites

Trước khi bắt đầu, bạn cần có:

| Yêu cầu | Cách lấy | Link |
|---|---|---|
| **Python 3.10+** | Cài từ python.org hoặc winget | [python.org](https://www.python.org/downloads/) |
| **LLM API Key** | OpenAI, NVIDIA NIM, Groq, hoặc OpenRouter | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **GitHub Personal Access Token** | Tạo tại GitHub Settings (cần `repo` scope) | [github.com/settings/tokens](https://github.com/settings/tokens) |

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

Hoặc dùng script Windows:
```cmd
install.bat
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

1. Truy cập provider API (OpenAI, NVIDIA NIM, Groq, v.v.)
2. Tạo API key
3. Copy key và dán vào file `.env`:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
```

**Nếu dùng provider khác** (NVIDIA NIM, Groq, OpenRouter, v.v.), thay `OPENAI_API_BASE`:

```env
# Ví dụ dùng NVIDIA NIM:
OPENAI_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=meta/llama-3.3-70b-instruct

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
   - ✅ `repo` — Đọc PR và submit review (full repository access)
   - Hoặc với fine-grained token: **Read & Write** cho "Pull requests" và "Issues"
4. Copy token và dán vào file `.env`:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Bước 7: Cấu hình Knowledge Base (tùy chọn)

Nếu bạn có Knowledge Base JSON cho dự án, đặt nó vào thư mục `knowledge_base/` và cấu hình:

```env
KB_PATH=knowledge_base/CrewAI_Review_Bot
KB_MAX_CHARS=8000
```

> KB sẽ cung cấp context về coding conventions, risk areas, file summaries và dependencies cho agents.

### File `.env` hoàn chỉnh:

```env
# LLM Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# GitHub Configuration
GITHUB_TOKEN=ghp-your-github-token-here
API_TIMEOUT=30
REVIEW_OUTPUT_PATH=

# Knowledge Base Configuration
KB_PATH=knowledge_base/CrewAI_Review_Bot
KB_MAX_CHARS=8000
```

> **💡 Lưu ý khi dùng provider khác OpenAI:** Project khởi tạo LLM với `base_url=OPENAI_API_BASE` trong `agents/agents.py`, nên hỗ trợ mọi OpenAI-compatible provider.

---

## ▶️ Hướng dẫn sử dụng

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

## 📤 Kết quả output

Bot sẽ tự động **submit một formal GitHub review** trên PR của bạn với status **APPROVE** hoặc **REQUEST CHANGES**:

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

VERDICT: REQUEST CHANGES
```

### Fallback chain

Nếu không thể submit formal review, bot sẽ thử theo thứ tự:
1. **Formal Review API** — Submit review với status (APPROVE / REQUEST CHANGES / COMMENT)
2. **Issue Comment** — Post review như comment thường
3. **Local File** — Lưu vào `review_output.md` locally

---

## ⚙️ Configuration

Tất cả cấu hình được quản lý qua file `.env`:

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key (hoặc compatible provider) | — |
| `OPENAI_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | Tên model sử dụng | `gpt-4o-mini` |
| `GITHUB_TOKEN` | GitHub Personal Access Token (cần `repo` scope) | — |
| `API_TIMEOUT` | Timeout cho GitHub API calls (giây) | `30` |
| `REVIEW_OUTPUT_PATH` | Đường dẫn lưu review local (khi GitHub fail) | `review_output.md` |
| `KB_PATH` | Đường dẫn tới thư mục Knowledge Base | `""` (tắt) |
| `KB_MAX_CHARS` | Giới hạn ký tự cho KB context | `8000` |

### Thay đổi model

```env
# Dùng GPT-4o (chất lượng tốt nhất, giá cao):
LLM_MODEL=gpt-4o

# Dùng GPT-4o-mini (tiết kiệm chi phí):
LLM_MODEL=gpt-4o-mini

# Dùng NVIDIA NIM Llama 3.3 70B (mặc định trong .env.example):
OPENAI_API_BASE=https://integrate.api.nvidia.com/v1
LLM_MODEL=meta/llama-3.3-70b-instruct

# Dùng Groq Llama 3.1 (miễn phí, nhanh):
OPENAI_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
```

---

## 📚 Knowledge Base

Project hỗ trợ tích hợp **Knowledge Base** để cung cấp context cho agents:

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

## 🐛 Troubleshooting

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

---

## 📦 Dependencies

- [`crewai`](https://github.com/crewAIInc/crewAI) — Multi-agent orchestration framework
- [`langchain-openai`](https://github.com/langchain-ai/langchain) — OpenAI LLM integration for LangChain
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — Load environment variables from `.env` file
- [`httpx`](https://github.com/encode/httpx) — HTTP client for GitHub API (installed with crewai)

---

## 📌 Features

- ✅ Simple and runnable — chỉ cần cung cấp PR link
- ✅ **Formal GitHub Review** — Submit APPROVE / REQUEST CHANGES / COMMENT
- ✅ **Knowledge Base integration** — Context-aware reviews với KB của dự án
- ✅ **Verdict parsing** — Tự động parse verdict để submit đúng review status
- ✅ **Fallback chain** — submit_review → post_comment → save local
- ✅ **Smart file prioritization** — Source code files trước, skip .log/.bat/.png
- ✅ Hỗ trợ mọi OpenAI-compatible LLM provider
- ✅ **Anti-false-positive** — Agents được thiết kế tránh false positives
- ✅ Không cần webhook hay server — chạy locally

---

## 🔮 Các vấn đề đã biết & Hướng cải thiện

### Vấn đề đã biết

| # | Vấn đề | Mô tả | Mức độ |
|---|--------|-------|--------|
| 1 | **Context limit khi PR lớn** | PR có nhiều files/diffs lớn có thể vượt context window của model. Đã có truncation (8000 chars/file) và file prioritization nhưng chưa tối ưu hoàn toàn. | 🟡 Medium |
| 2 | **Agent reviews chạy chậm** | 4 agents chạy sequential, mỗi agent gọi LLM riêng → tổng thời gian 2-5 phút/PR. Chưa tận dụng được parallel execution. | 🟡 Medium |
| 3 | **Review chất lượng phụ thuộc model** | Model nhỏ đôi khi đưa ra feedback chung chung, thiếu cụ thể. Model lớn (70B+) cho kết quả tốt hơn nhiều. | 🟡 Medium |
| 4 | **Không có caching** | Mỗi lần chạy đều fetch lại PR từ GitHub và gọi LLM mới. Không cache kết quả cho các lần chạy lặp lại. | 🟢 Low |
| 5 | **Error handling cơ bản** | Chưa có retry logic khi API lỗi tạm thời (rate limit, network timeout). | 🟢 Low |

### Hướng cải thiện

#### 🏗️ Architecture
- [ ] **Chạy agents song song (hierarchical process)**: Cho phép Code Reviewer, Security Expert, Performance Engineer chạy đồng thời → giảm thời gian review xuống ~1/3.
- [ ] **Streaming output**: Hiển thị kết quả từng agent real-time thay vì đợi tất cả xong.
- [ ] **Add more agents**: Thêm agent chuyên review tests, docs, dependencies.

#### 🧠 LLM & Context
- [ ] **Smart context management**: Thay vì truncate cơ bản, dùng RAG hoặc summarization để chọn đoạn code quan trọng nhất.
- [ ] **Chunked review**: Chia PR lớn thành các chunk nhỏ, review từng phần rồi tổng hợp.
- [ ] **Support more models**: Thêm support cho Anthropic Claude, Google Gemini.
- [ ] **Custom temperature/settings**: Cho phép cấu hình temperature, max_tokens cho từng agent riêng.

#### 🔗 GitHub Integration
- [ ] **Inline review comments**: Post comment trực tiếp trên từng line diff (GitHub Review API).
- [ ] **PR event webhook**: Tự động chạy review khi có PR mới (cần server).
- [ ] **GitHub Actions integration**: Chạy bot như một GitHub Action.
- [ ] **Rate limiting**: Tự động delay giữa các API calls để tránh rate limit.

#### 📊 Quality & UX
- [ ] **Review history**: Lưu lịch sử review vào database (SQLite) để theo dõi xu hướng.
- [ ] **Configurable rules**: Cho phép custom rules per project.
- [ ] **Rich terminal output**: Dùng `rich` library cho terminal output đẹp hơn.
- [ ] **Review score**: Tính điểm chất lượng PR (A/B/C/D/F).

#### 🛡️ Reliability
- [ ] **Retry logic**: Tự động retry khi LLM API lỗi (exponential backoff).
- [ ] **Graceful degradation**: Nếu 1 agent fail, vẫn chạy agents còn lại.
- [ ] **Unit tests**: Thêm test suite cho agents, tasks, và GitHub client.
- [ ] **CI/CD pipeline**: Tự động test khi push code.

---

## 📄 License

MIT