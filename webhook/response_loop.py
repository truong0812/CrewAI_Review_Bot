"""Classify developer comment intent and respond accordingly."""

import re
import threading

from github_utils.client import GitHubClient
from webhook.conversation import ResponseResult
from webhook.state import state_store

import config.settings as cfg

LLM_TIMEOUT_SECONDS = 60


def _call_llm_with_timeout(llm, prompt: str, timeout: int = LLM_TIMEOUT_SECONDS) -> str:
    """Call LLM with a timeout to avoid blocking the thread."""
    result = [None]
    exc = [None]

    def _worker():
        try:
            result[0] = llm.call(prompt)
        except Exception as e:
            exc[0] = e

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"LLM call timed out after {timeout}s")
    if exc[0]:
        raise exc[0]
    return result[0]


def classify_intent(comment_body: str) -> str:
    """Classify the intent of a developer's comment using keyword heuristics.

    Returns one of: "question", "fixed", "pushback", "other".
    """
    text = comment_body.lower().strip()

    # Fixed patterns
    fixed_patterns = [
        r"\b(fixed?|done|resolved?|updated?|pushed)\b",
        r"\bshould be (fixed|good|resolved|done)\b",
        r"\baddressed\b",
        r"đã\s*(sửa|fix|xử lý|xong)",
        r"đã\s*update",
    ]
    for pattern in fixed_patterns:
        if re.search(pattern, text):
            return "fixed"

    # Question patterns
    question_patterns = [
        r"\?",
        r"\b(why|what|how|where|when|which|can you|could you)\b",
        r"\b(tại sao|như thế nào|ở đâu|khi nào|cái gì|làm sao)\b",
    ]
    for pattern in question_patterns:
        if re.search(pattern, text):
            return "question"

    # Pushback patterns
    pushback_patterns = [
        r"\b(disagree|wrong|incorrect|not a? ?bug|false positive|intended|by design)\b",
        r"\b(i think|in my opinion|imo|imho)\b",
        r"\b(không đồng ý|sai|mục đích|theo tôi)\b",
    ]
    for pattern in pushback_patterns:
        if re.search(pattern, text):
            return "pushback"

    return "other"


def handle_response(
    gh: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    comment_body: str,
    comment_author: str,
    comment_id: int,
    review_body: str,
) -> ResponseResult:
    """Process a developer comment and respond if appropriate.

    Returns ResponseResult with action, intent, and reply_text.
    """
    if not cfg.RESPONSE_LOOP_ENABLED:
        return ResponseResult(action="ignored", intent="other", reply_text="")

    intent = classify_intent(comment_body)

    if intent == "question":
        return _answer_question(gh, owner, repo, pr_number, comment_body, comment_author, review_body, intent)
    elif intent == "fixed":
        return _acknowledge_fix(gh, owner, repo, pr_number, comment_author, intent)
    elif intent == "pushback":
        return _evaluate_pushback(gh, owner, repo, pr_number, comment_body, comment_author, review_body, intent)

    return ResponseResult(action="ignored", intent=intent, reply_text="")


def _answer_question(
    gh: GitHubClient,
    owner: str, repo: str, pr_number: int,
    question: str, author: str, review_body: str,
    intent: str,
) -> ResponseResult:
    """Answer a developer's question using LLM."""
    from crewai import LLM

    llm = LLM(
        model="openai/gpt-4",
        base_url=cfg.OPENAI_API_BASE,
        api_key=cfg.OPENAI_API_KEY,
    )
    llm.model = cfg.LLM_MODEL

    prompt = (
        f"A developer (@{author}) asked a question about a PR review:\n\n"
        f"**Question:** {question}\n\n"
        f"**Review context:**\n{review_body[:2000]}\n\n"
        f"Provide a concise, helpful answer. Be direct and friendly. "
        f"Use markdown formatting. Address @{author}."
    )

    try:
        answer = _call_llm_with_timeout(llm, prompt)
        reply = f"**@{author}** — {answer}"
        gh.post_comment(owner, repo, pr_number, reply)
        return ResponseResult(action="answered", intent=intent, reply_text=reply)
    except Exception:
        return ResponseResult(action="ignored", intent=intent, reply_text="")


def _acknowledge_fix(
    gh: GitHubClient,
    owner: str, repo: str, pr_number: int,
    author: str,
    intent: str,
) -> ResponseResult:
    """Acknowledge a fix — the actual re-review happens on synchronize event."""
    reply = (
        f"Thanks @{author}! I see you've addressed the feedback. "
        f"I'll automatically re-review when the new commits are pushed."
    )
    try:
        gh.post_comment(owner, repo, pr_number, reply)
        return ResponseResult(action="acknowledged", intent=intent, reply_text=reply)
    except Exception:
        return ResponseResult(action="ignored", intent=intent, reply_text="")


def _evaluate_pushback(
    gh: GitHubClient,
    owner: str, repo: str, pr_number: int,
    comment: str, author: str, review_body: str,
    intent: str,
) -> ResponseResult:
    """Evaluate developer pushback using LLM."""
    from crewai import LLM

    llm = LLM(
        model="openai/gpt-4",
        base_url=cfg.OPENAI_API_BASE,
        api_key=cfg.OPENAI_API_KEY,
    )
    llm.model = cfg.LLM_MODEL

    prompt = (
        f"A developer (@{author}) is pushing back on a PR review finding:\n\n"
        f"**Developer's comment:** {comment}\n\n"
        f"**Review context:**\n{review_body[:2000]}\n\n"
        f"First line must be exactly ACCEPTED or REJECTED. Then your reply.\n"
        f"ACCEPTED means you agree with the developer's pushback and retract the finding.\n"
        f"REJECTED means the finding stands.\n"
        f"Be concise (2-4 sentences). Address @{author}."
    )

    try:
        response = _call_llm_with_timeout(llm, prompt)
        accepted = response.strip().lower().startswith("accepted")
        # Strip the verdict line for the reply
        reply_body = re.sub(r"^(?:accepted|rejected)\s*\n", "", response.strip(), flags=re.IGNORECASE)
        reply = f"**@{author}** — {reply_body}"
        gh.post_comment(owner, repo, pr_number, reply)
        return ResponseResult(action="evaluated", intent=intent, reply_text=reply, pushback_accepted=accepted)
    except Exception:
        return ResponseResult(action="ignored", intent=intent, reply_text="")
