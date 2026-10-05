import json
import re
from anthropic import Anthropic
from datetime import datetime, timezone
from sqlmodel import Session, select
from backend.config import settings
from backend.models import Conversation, Message, Signal

EXTRACTION_SYSTEM = """You are a demand signal extraction engine. Given a customer support conversation transcript, extract structured demand signals.

Return ONLY valid JSON — no markdown fences, no explanation text. Return exactly this structure:
{
  "signals": [
    {
      "product_name": "string",
      "product_id": "string or null",
      "signal_type": "demand_expressed|availability_complaint|return_intent|price_concern|competitor_mention",
      "sentiment": "positive|neutral|negative",
      "complaint_category": "string or null",
      "return_reason": "string or null",
      "market": "string",
      "urgency": 1,
      "raw_quote": "string or null",
      "confidence": 0.9
    }
  ],
  "overall_sentiment": "positive|neutral|negative",
  "escalation_detected": false,
  "conversation_summary": "one sentence summary"
}

urgency is 1-5 (5 = most urgent). confidence is 0.0-1.0."""


def _strip_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def extract_signals_from_conversation(conversation_id: int, session: Session) -> dict:
    if settings.use_mock:
        from backend.agents.mock_agents import extract_signals_mock
        return extract_signals_mock(conversation_id, session)

    # ── Live Claude extraction ──
    client = Anthropic(api_key=settings.anthropic_api_key)
    conv = session.get(Conversation, conversation_id)
    if not conv:
        return {"error": "Conversation not found"}

    messages_db = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    ).all()

    if not messages_db:
        return {"signals": [], "message": "No messages found"}

    transcript_parts = []
    for msg in messages_db:
        role_label = "Customer" if msg.role == "user" else "Nova (Agent)"
        transcript_parts.append(f"{role_label}: {msg.content}")
    transcript = "\n\n".join(transcript_parts)

    prompt = f"""Extract demand signals from this customer support conversation.
Market: {conv.market}

CONVERSATION:
{transcript}

Return ONLY the JSON object as specified."""

    def _call_claude(extra: str = "") -> str:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt + extra}]
        )
        return response.content[0].text

    raw = _call_claude()
    try:
        data = json.loads(_strip_json(raw))
    except json.JSONDecodeError:
        raw = _call_claude("\n\nIMPORTANT: Return ONLY raw JSON. No markdown, no explanation.")
        try:
            data = json.loads(_strip_json(raw))
        except json.JSONDecodeError:
            return {"error": "Failed to parse signal extraction response"}

    signals_stored = []
    for sig in data.get("signals", []):
        signal = Signal(
            conversation_id=conversation_id,
            extracted_at=datetime.now(timezone.utc),
            product_id=sig.get("product_id"),
            product_name=sig.get("product_name", "Unknown"),
            signal_type=sig.get("signal_type", "demand_expressed"),
            sentiment=sig.get("sentiment", "neutral"),
            complaint_category=sig.get("complaint_category"),
            return_reason=sig.get("return_reason"),
            market=sig.get("market", conv.market),
            urgency=sig.get("urgency", 3),
            raw_quote=sig.get("raw_quote"),
            confidence=sig.get("confidence", 0.8)
        )
        session.add(signal)
        signals_stored.append(signal)

    session.commit()
    return {
        "signals_extracted": len(signals_stored),
        "overall_sentiment": data.get("overall_sentiment", "neutral"),
        "escalation_detected": data.get("escalation_detected", False),
        "summary": data.get("conversation_summary", "")
    }
