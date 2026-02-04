import os
import re

# Optional OpenAI
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def _sanitize_ascii(text: str) -> str:
    if not text:
        return ""
    # Replace smart quotes/dashes with ascii
    text = (text
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2014", "-")
        .replace("\u2013", "-")
    )
    # Remove any remaining non-ascii chars (production safe for WhatsApp basic replies)
    text = text.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
    # normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def run_agent(message_text: str, contact_name: str | None = None) -> tuple[str, str]:
    """
    Returns: (reply, stage)
    Stage: new|qualified|order|closed
    """
    message_text = message_text or ""
    lower = message_text.lower()

    # Fallback rule-based (works without OpenAI)
    stage = "new"
    if any(k in lower for k in ["price", "cost", "rate", "kitna", "suit", "order", "cod", "delivery"]):
        stage = "qualified"

    default_reply = "Share your city + budget and I'll finalize the order."

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    if not api_key or OpenAI is None:
        return (_sanitize_ascii(default_reply), stage)

    try:
        client = OpenAI(api_key=api_key)
        system = (
            "You are a sales assistant for a Pakistani fashion brand. "
            "Keep replies short, polite, and in simple English. Use only ASCII punctuation."
        )
        user = f"Customer: {message_text}\nName: {contact_name or ''}\nReply in one line."
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        reply = resp.choices[0].message.content or default_reply
        return (_sanitize_ascii(reply), stage)
    except Exception:
        return (_sanitize_ascii(default_reply), stage)
