"""LLM classification helper: builds the prompt, calls the OpenAI-compatible
endpoint, and parses the JSON answer robustly."""
from openai import OpenAI

from config import BASE_URL, API_KEY, MODEL, PROMPT_PATH, NRC_EMOTIONS

if not API_KEY:
    raise RuntimeError(
        "MBAX_API_KEY is not set. Export it before running (see README):\n"
        "    export MBAX_API_KEY=\"<your key>\""
    )

_CLIENT = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Accepted sentiment labels per task setting.
TWO_CLASS = ["POSITIVE", "NEGATIVE"]
THREE_CLASS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]

_EXTRA_RULES = {
    # 2-class mode: only positive or negative is allowed.
    ("POSITIVE", "NEGATIVE"): (
        "Pick the closer of the two labels. A flat, neutral-sounding review should "
        "still be forced to POSITIVE or NEGATIVE based on overall tone."
    ),
    # 3-class mode adds NEUTRAL.
    ("POSITIVE", "NEUTRAL", "NEGATIVE"): (
        "NEUTRAL is reserved for reviews that are genuinely flat, factual, or mixed "
        "with no clear lean. Use it sparingly."
    ),
}

_SENT_LABELS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]


def build_prompt(title, text, sentiment_labels):
    """Render the reusable prompt template for one review."""
    labels_str = ", ".join(sentiment_labels)
    rules = _EXTRA_RULES.get(tuple(sentiment_labels), "")
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    return (
        template
        .replace("{sentiment_labels}", labels_str)
        .replace("{extra_rules}", rules)
        .replace("{title}", (title or "").replace("{", "(").replace("}", ")"))
        .replace("{text}", (text or "").replace("{", "(").replace("}", ")"))
    )


def _clean(content):
    """Strip common vLLM reasoning tags / fences to get at the JSON object."""
    if content is None:
        return ""
    # vLLM/DeepSeek often precede the answer with a reasoning block. Anything
    # after a "response" marker or the final JSON object is what we want.
    low = content.lower()
    for marker in (" response", "### response", "assistant"):
        if marker in low:
            idx = low.rfind(marker) + len(marker)
            content = content[idx:]
            break
    for fence in ("```json", "```"):
        content = content.replace(fence, "")
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return content[start:end + 1]
    return content.strip()


def _parse(content, sentiment_labels):
    """Extract a dict with sentiment + emotion + confidence from model text."""
    import json as _json
    raw = _clean(content)
    try:
        data = _json.loads(raw)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    sentiment = str(data.get("sentiment", "")).strip().upper()
    # Validate against allowed labels; fall back to scanning the text.
    if sentiment not in sentiment_labels:
        found = [s for s in sentiment_labels if s in raw.upper()]
        sentiment = found[0] if found else None

    emotion = str(data.get("emotion", "")).strip().lower()
    if emotion not in NRC_EMOTIONS and emotion != "none":
        emotion = next((e for e in NRC_EMOTIONS if e in raw.lower() and e not in sentiment_labels), None)

    try:
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = None

    return {"sentiment": sentiment, "emotion": emotion, "confidence": confidence,
            "raw": raw}


def classify(title, text, sentiment_labels=None, temperature=0.0, max_tokens=1000,
             retries=2):
    """Call the model once and return a parsed classification.

    retries: number of additional attempts after a malformed / missing answer.
    """
    if sentiment_labels is None:
        sentiment_labels = TWO_CLASS
    messages = [{
        "role": "user",
        "content": build_prompt(title, text, sentiment_labels),
    }]
    last = None
    for attempt in range(retries + 1):
        try:
            resp = _CLIENT.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
        except Exception as e:  # network / server error
            last = {"sentiment": None, "emotion": None, "confidence": None,
                    "error": f"llm_error: {e}", "raw": str(e)}
            continue
        parsed = _parse(content, sentiment_labels)
        parsed.setdefault("raw", content)
        if parsed["sentiment"] is not None:
            return parsed
        last = parsed
    return last
