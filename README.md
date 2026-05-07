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
├── docs/
│   └── USAGE.md             # Full usage guide
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
| **Code Reviewer** | Senior Code Reviewer | PEP 8, naming, readability, dead code, error handling |
| **Security Expert** | Application Security Engineer | SQL injection, deserialization, weak crypto, hardcoded secrets |
| **Performance Engineer** | Performance Optimization Engineer | Inefficient loops, memory issues, algorithmic complexity |
| **Tech Lead** | Technical Lead | Synthesizes all reports → final PR review with **VERDICT: APPROVE / REQUEST CHANGES** |

---

## 🔄 Workflow

```
PR URL + optional KB path
         │
         ▼
┌──────────────────┐
│  GitHub API       │  Fetch PR files, diffs, title, description
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Knowledge Base   │  Load conventions, risks, dependencies, summaries
│  (optional)       │
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
                                                                    │  Parse Verdict    │
                                                                    └────────┬─────────┘
                                                                             │
                                                                             ▼
                                                                    ┌──────────────────┐
                                                                    │  GitHub Review API│
                                                                    │  (fallback:       │
                                                                    │   comment → file) │
                                                                    └──────────────────┘
```

---

## 🚀 Quick Start

```bash
# 1. Setup
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env with your keys

# 2. Run
python main.py https://github.com/owner/repo/pull/123
```

📖 **Full installation, configuration, and usage guide:** [docs/USAGE.md](docs/USAGE.md)

---

## 📦 Dependencies

- [`crewai`](https://github.com/crewAIInc/crewAI) — Multi-agent orchestration framework
- [`langchain-openai`](https://github.com/langchain-ai/langchain) — OpenAI LLM integration for LangChain
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — Load environment variables from `.env` file
- [`httpx`](https://github.com/encode/httpx) — HTTP client for GitHub API

---

## 📌 Features

- ✅ Simple and runnable — chỉ cần cung cấp PR link
- ✅ **Formal GitHub Review** — Submit APPROVE / REQUEST CHANGES / COMMENT
- ✅ **Knowledge Base integration** — Context-aware reviews với KB của dự án
- ✅ **Multi-language support** — Review output in any language (`REVIEW_LANGUAGE=en/vi/ja/...`)
- ✅ **Verdict parsing** — Tự động parse verdict để submit đúng review status
- ✅ **Fallback chain** — submit_review → post_comment → save local
- ✅ **Smart file prioritization** — Source code files trước, skip .log/.bat/.png
- ✅ Hỗ trợ mọi OpenAI-compatible LLM provider
- ✅ **Anti-false-positive** — Agents được thiết kế tránh false positives
- ✅ Không cần webhook hay server — chạy locally

---

## 🔮 Known Issues & Roadmap

| # | Vấn đề | Mức độ |
|---|--------|--------|
| 1 | **Context limit khi PR lớn** — truncation và file prioritization nhưng chưa tối ưu hoàn toàn | 🟡 Medium |
| 2 | **Agent reviews chạy sequential** — 4 agents × LLM call = 2-5 min/PR | 🟡 Medium |
| 3 | **Review chất lượng phụ thuộc model** — model nhỏ cho feedback chung chung | 🟡 Medium |
| 4 | **Không có caching** — mỗi lần chạy fetch lại PR và gọi LLM mới | 🟢 Low |

### Roadmap

- [ ] Chạy agents song song (hierarchical process)
- [ ] Inline review comments trên từng line diff
- [ ] GitHub Actions integration
- [ ] Smart context management (RAG / summarization)
- [ ] Retry logic cho API errors
- [ ] Review history (SQLite)

---

## 📄 License

MIT
