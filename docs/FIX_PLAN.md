# 🔧 Plan Fix Issues — PR Review Bot

> Dựa trên review từ Qwen3 Coder 480B trên PR #3

## Phân Tách Issues: Valid vs Invalid

### ✅ VALID — Cần Fix

| # | Issue | File | Line | Severity | Đánh giá |
|---|-------|------|------|----------|----------|
| 1 | **KB JSON Schema Validation** | `kb_loader.py` | 37 | BLOCKING | `json.load()` không validate structure. Nên check schema cơ bản. |
| 2 | **KB_MAX_CHARS crash** | `config/settings.py` | 19 | BLOCKING | `int(os.getenv("KB_MAX_CHARS", "8000"))` sẽ crash nếu env var không phải số. |
| 3 | **KB Truncation off-by-one** | `kb_loader.py` | 78 | NON-BLOCKING | Append warning message làm result vượt quá `max_chars`. |
| 4 | **Verdict Regex robustness** | `main.py` | 38 | NON-BLOCKING | Regex chỉ match "REQUEST CHANGES" (space), không match "REQUEST_CHANGES" (underscore). Fallback keyword search xử lý được nhưng regex nên cover cả hai. |
| 5 | **Fallback chain logging** | `main.py` | 179-191 | NON-BLOCKING | Error messages cơ bản, thiếu chi tiết để debug. |

### ❌ INVALID / WON'T FIX — False Positives

| # | Issue | Lý do không fix |
|---|-------|-----------------|
| 6 | **IDOR in GitHub client** (`client.py` lines 98, 119) | **False positive.** `owner`, `repo`, `pr_number` đến từ CLI args, không phải untrusted user input. GitHub token scopes đã kiểm soát authorization. |
| 7 | **Insecure Deserialization** (`kb_loader.py` line 27) | **False positive.** `json.load()` KHÔNG phải insecure deserialization (đó là `pickle`). JSON parser an toàn, không execute code. |
| 8 | **Hardcoded strings** (`main.py` line 40) | Style preference, không phải bug. Regex là constant de facto. |
| 9 | **Missing type hints** (`main.py`) | Style preference, project không dùng type checking. |
| 10 | **Emoji in error messages** (`kb_loader.py`) | Intentional — CLI output cho người dùng. |
| 11 | **String concatenation efficiency** (`tasks/tasks.py`) | Micro-optimization, negligible impact. |
| 12 | **Missing newline EOF** (`kb_loader.py`) | Trivial. |

---

## Chi Tiết Fix

### Fix 1: KB JSON Schema Validation (`kb_loader.py`)

**Vấn đề:** `json.load()` không kiểm tra data structure. Nếu file JSON bị corrupt hoặc sai format, code sẽ crash ở các dòng sau khi access `data.get("files", [])`.

**Fix:** Thêm validate function sau khi load JSON:

```python
def _validate_kb_schema(data: dict) -> bool:
    """Basic schema validation for KB data."""
    if not isinstance(data, dict):
        return False
    # Must have at least 'files' key
    if "files" not in data:
        return False
    # files must be a list
    if not isinstance(data.get("files"), list):
        return False
    return True
```

**Location:** Sau line 37, trước khi build maps.

---

### Fix 2: KB_MAX_CHARS Safe Parsing (`config/settings.py`)

**Vấn đề:** `int(os.getenv("KB_MAX_CHARS", "8000"))` sẽ throw `ValueError` nếu env var không phải integer.

**Fix:**

```python
try:
    KB_MAX_CHARS = int(os.getenv("KB_MAX_CHARS", "8000"))
except (ValueError, TypeError):
    KB_MAX_CHARS = 8000
```

---

### Fix 3: KB Truncation Off-By-One (`kb_loader.py`)

**Vấn đề:** `result[:max_chars] + "\n\n... (KB truncated)"` làm result dài hơn `max_chars`.

**Fix:**

```python
if len(result) > max_chars:
    warning = "\n\n... (KB truncated to fit context limit)"
    result = result[:max_chars - len(warning)] + warning
```

---

### Fix 4: Verdict Regex Robustness (`main.py`)

**Vấn đề:** Regex `REQUEST\s+CHANGES` chỉ match "REQUEST CHANGES" (space), không match "REQUEST_CHANGES" (underscore). Dù fallback keyword search xử lý được, regex nên cover cả hai format.

**Fix:**

```python
match = re.search(r"VERDICT:\s*(APPROVE|REQUEST[\s_]+CHANGES)", review_text, re.IGNORECASE)
```

---

### Fix 5: Fallback Chain Logging (`main.py`)

**Vấn đề:** Error messages trong fallback chain thiếu chi tiết.

**Fix:** Thêm `logging` module hoặc cải thiện error messages:

```python
except Exception as e:
    print(f"⚠️ Formal review failed: {type(e).__name__}: {e}")
    print("   Falling back to issue comment...")
```

---

## Thứ Tự Thực Hiện

1. ✅ **Fix 2** (config/settings.py) — Dễ nhất, 1 dòng
2. ✅ **Fix 3** (kb_loader.py truncation) — 1 dòng
3. ✅ **Fix 4** (main.py regex) — 1 dòng  
4. ✅ **Fix 5** (main.py logging) — 2-3 dòng
5. ✅ **Fix 1** (kb_loader.py schema validation) — Thêm function mới

---

## Files Cần Sửa

| File | Fixes | Lines thay đổi |
|------|-------|---------------|
| `config/settings.py` | Fix 2 | ~3 lines |
| `kb_loader.py` | Fix 1, Fix 3 | ~15 lines |
| `main.py` | Fix 4, Fix 5 | ~5 lines |