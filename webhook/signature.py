"""GitHub webhook HMAC-SHA256 signature verification."""

import hashlib
import hmac


def verify_signature(body: bytes, header: str, secret: str) -> bool:
    """Verify the GitHub webhook signature.

    Args:
        body: Raw request body bytes.
        header: Value of the X-Hub-Signature-256 header.
        secret: The webhook secret configured on GitHub.

    Returns:
        True if signature is valid, False otherwise.

    Raises:
        ValueError: If secret is empty (webhook misconfigured).
    """
    if not secret:
        raise ValueError(
            "WEBHOOK_SECRET is not set. "
            "Configure it in .env or use WEBHOOK_DEV_MODE=true for local testing."
        )

    if not header:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, header)
