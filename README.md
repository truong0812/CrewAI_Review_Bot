# 🤖 PR Review Bot

Multi-agent code review system built with **CrewAI** and **LangChain OpenAI**.  
Four AI agents collaborate to perform a comprehensive pull request review on a Python code snippet.

---

## 📁 Project Structure

```
pr-review-bot/
├── agents/
│   ├── __init__.py
│   └── agents.py            # Agent definitions (4 agents)
├── tasks/
│   ├── __init__.py
│   └── tasks.py             # Task definitions (4 sequential tasks)
├── config/
│   ├── __init__.py
│   └── settings.py          # LLM config & hardcoded code snippet
├── main.py                  # Entry point
├── .env                     # API key & base URL configuration
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
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐    ┌──────────────┐
│  Code Reviewer   │───▶│ Security Expert  │───▶│ Performance Engineer │───▶│  Tech Lead   │
│  (Quality)       │    │  (Vulnerabilities)│    │  (Optimization)      │    │  (Final)     │
└─────────────────┘    └─────────────────┘    └──────────────────────┘    └──────────────┘
```

The process is **sequential**: each agent completes its task before the next one starts. The Tech Lead receives context from all prior reviews and compiles the final structured markdown output.

---

## 📥 Input

The code snippet is hardcoded in `config/settings.py` and contains intentional issues:

```python
import hashlib
import pickle

def authenticate(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    password_hash = hashlib.md5(password.encode()).hexdigest()
    data = pickle.loads(user_input)
    items = []
    for i in range(len(data)):
        items.append(data[i].upper())
    API_KEY = "sk-1234567890abcdef"
    return result
```

**Intentional issues include:**
- 🔴 SQL Injection via f-string interpolation
- 🔴 Insecure deserialization with `pickle.loads()`
- 🔴 Hardcoded API key / secret
- 🟠 Weak MD5 hashing algorithm
- 🟡 Unused variables (`password_hash`, `items`, `API_KEY`)
- 🟡 Anti-pattern `range(len())` instead of direct iteration
- 🟡 Undefined variables (`db`, `user_input`)
- 🟡 Missing docstrings and type hints

---

## 📤 Output

The bot produces a structured markdown PR review containing:

- **Summary table** of all issues found
- **BLOCKING** issues (must fix before merge)
- **NON-BLOCKING** issues (suggested improvements)
- **Final verdict**: `APPROVE` or `REQUEST CHANGES`
- **Prioritized action items**

Output is printed to console and saved to `review_output.md`.

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
cd pr-review-bot
pip install -r requirements.txt
```

### 2. Configure your `.env` file

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# LLM Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

> **Tip:** If you're using a compatible OpenAI API provider (e.g., Azure, local LLM, or other OpenAI-compatible services), just change the `OPENAI_API_BASE` URL accordingly.

### 3. Run the bot

```bash
python main.py
```

---

## ⚙️ Configuration

All LLM settings are managed via the `.env` file:

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key | — |
| `OPENAI_API_BASE` | API base URL (change for Azure, local LLM, etc.) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model to use | `gpt-4o-mini` |

To review your own code, edit the `CODE_SNIPPET` variable in `config/settings.py`.

---

## 📦 Dependencies

- [`crewai`](https://github.com/crewAIInc/crewAI) — Multi-agent orchestration framework
- [`langchain-openai`](https://github.com/langchain-ai/langchain) — OpenAI LLM integration for LangChain
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — Load environment variables from `.env` file

---

## 📌 Constraints

- ❌ No GitHub integration — input is hardcoded, output is local
- ❌ No over-engineering — minimal, readable, single-purpose modules
- ✅ Simple and runnable with just an OpenAI API key

---

## 📄 License

MIT