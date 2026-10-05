"""
Mock AI agents — no Claude API key required.
Used for demo/prototype mode (USE_MOCK=true in .env).
"""
import json
import asyncio
import random
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlmodel import Session, select

from backend.models import Conversation, Message, Signal, Inventory, SalesHistory, Forecast
from backend.tools.product_tools import search_product_catalog
from backend.tools.order_tools import get_order_status, submit_return_request
from backend.tools.escalation_tools import escalate_to_human

_PRODUCTS_FILE = Path(__file__).parent.parent / "data" / "products.json"

# Market currency symbols and approximate exchange rates relative to USD base prices
_MARKET_CURRENCY: dict[str, tuple[str, float]] = {
    "US": ("$",   1.00),
    "UK": ("£",   0.79),
    "DE": ("€",   0.92),
    "FR": ("€",   0.92),
    "JP": ("¥", 149.00),
    "AU": ("A$",  1.53),
    "CA": ("C$",  1.36),
    "BR": ("R$",  4.97),
    "IN": ("₹",  83.00),
    "SG": ("S$",  1.34),
}

def _format_price(usd_price: float, market: str) -> str:
    symbol, rate = _MARKET_CURRENCY.get(market, ("$", 1.0))
    local = usd_price * rate
    if market == "JP":
        return f"{symbol}{int(round(local)):,}"
    if market in ("IN", "BR"):
        return f"{symbol}{local:,.0f}"
    return f"{symbol}{local:.2f}"

def _load_products():
    with open(_PRODUCTS_FILE) as f:
        return json.load(f)


# ─────────────────────────────────────────────
# MOCK SUPPORT AGENT (streaming chat)
# ─────────────────────────────────────────────

def _detect_intent(msg: str, history: list[dict]) -> str:
    m = msg.lower()
    if any(w in m for w in ["escalat", "human", "person", "agent", "manager", "supervisor", "speak to someone", "talk to someone", "real person"]):
        return "escalate"
    if re.search(r"\bord(?:er)?\s*[-#]?\s*\d+", m) or ("order" in m and any(w in m for w in ["status", "where", "track", "my order", "find"])):
        return "order_status"
    if any(w in m for w in ["return", "refund", "send back", "exchange"]):
        return "return"
    if any(w in m for w in ["available", "availability", "in stock", "stock", "have you got", "do you have", "can i get", "buy", "purchase"]):
        return "product_search"
    # Check if any product name appears in the message
    for p in _load_products():
        if any(part.lower() in m for part in p["name"].split() if len(part) > 3):
            return "product_search"
    if any(w in m for w in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
        return "greeting"
    if any(w in m for w in ["thank", "thanks", "great", "perfect", "awesome", "appreciate"]):
        return "thanks"
    if any(w in m for w in ["frustrat", "angry", "ridiculous", "terrible", "awful", "unacceptable", "disgust", "horrible", "worst"]):
        return "frustration"
    if any(w in m for w in ["bye", "goodbye", "that's all", "that is all", "nothing else", "no more"]):
        return "farewell"
    return "general"


def _find_product_in_message(msg: str) -> dict | None:
    m = msg.lower()
    products = _load_products()
    # Exact name match first
    for p in products:
        if p["name"].lower() in m:
            return p
    # Partial word match (longest match wins)
    best = None
    best_len = 0
    for p in products:
        parts = [w for w in p["name"].split() if len(w) > 3]
        hits = sum(1 for w in parts if w.lower() in m)
        if hits > 0 and hits >= best_len:
            best_len = hits
            best = p
    return best


def _find_order_id(msg: str) -> str | None:
    m = re.search(r"(?:ord(?:er)?[-\s#]*)?(\d{4,8})", msg, re.IGNORECASE)
    if m:
        return f"ORD-{m.group(1)}"
    return None


def _stock_description(days: float) -> str:
    if days < 4:
        return "critically low — less than 4 days of stock remaining"
    if days < 7:
        return f"very low — only about {int(days)} days of stock remaining"
    if days < 14:
        return f"limited — approximately {int(days)} days of supply"
    return f"good — {int(days)} days of supply available"


async def _stream_text(text: str):
    """Yield text in realistic word-sized chunks with small delays."""
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield chunk
        await asyncio.sleep(random.uniform(0.025, 0.055))


async def run_mock_support_agent_streaming(
    conversation_id: int,
    user_message: str,
    market: str,
    session: Session
):
    """Keyword-driven mock support agent. Calls real tool functions, streams realistic responses."""

    # Load history for context
    history = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    ).all()
    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    # Save user message
    session.add(Message(conversation_id=conversation_id, role="user", content=user_message))
    session.commit()

    intent = _detect_intent(user_message, history_dicts)
    escalated = False
    response_text = ""

    # ── GREETING ──
    if intent == "greeting":
        response_text = (
            "Hello. I'm Nova, Cosmic Mart's support assistant. "
            "I can help with product availability, order tracking, returns, and more. "
            "What can I do for you today?"
        )

    # ── PRODUCT SEARCH ──
    elif intent == "product_search":
        product = _find_product_in_message(user_message)
        query = product["name"] if product else user_message
        yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'search_product_catalog', 'input': {'query': query, 'market': market}})}\n\n"
        await asyncio.sleep(0.4)
        result = search_product_catalog(query, market, session)

        if not result.get("found") or not result.get("products"):
            response_text = (
                f"I searched our {market} catalog for **{query}** but couldn't find a match. "
                "Could you double-check the product name? You might also try browsing by category — "
                "we carry Electronics, Appliances, Furniture, Clothing, and Food & Grocery."
            )
        else:
            items = result["products"]
            if len(items) == 1:
                p = items[0]
                stock_desc = _stock_description(p.get("days_of_supply", 30))
                avail = "in stock" if p.get("available") else "currently out of stock"
                price_str = _format_price(p["price"], market)
                response_text = (
                    f"I found the **{p['name']}** in our {market} store. "
                    f"Price: **{price_str}**. "
                    f"Availability: {avail}. Stock level is {stock_desc}. "
                )
                if p.get("days_of_supply", 30) < 7:
                    response_text += (
                        "Note: stock is very limited — I would recommend acting soon if you are interested. "
                        "Is there anything else you would like to know, or can I help you with something else?"
                    )
                else:
                    response_text += "Would you like more details, or can I help you with anything else?"
            else:
                lines = []
                for p in items[:3]:
                    avail = "In stock" if p.get("available") else "Out of stock"
                    dos = p.get("days_of_supply", 0)
                    note = " — limited availability" if dos < 7 else ""
                    price_str = _format_price(p["price"], market)
                    lines.append(f"- **{p['name']}** — {price_str} — {avail}{note}")
                response_text = (
                    f"Here is what I found in our {market} store:\n\n" +
                    "\n".join(lines) +
                    "\n\nWould you like details on any of these?"
                )

    # ── ORDER STATUS ──
    elif intent == "order_status":
        order_id = _find_order_id(user_message)
        if not order_id:
            # Check history for a previously mentioned order ID
            for h in reversed(history_dicts):
                oid = _find_order_id(h.get("content", ""))
                if oid:
                    order_id = oid
                    break
        if not order_id:
            response_text = (
                "I'd be happy to look up your order! Could you share your order ID? "
                "It should look something like **ORD-12345** — you'll find it in your confirmation email."
            )
        else:
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'get_order_status', 'input': {'order_id': order_id}})}\n\n"
            await asyncio.sleep(0.4)
            o = get_order_status(order_id)
            status_msgs = {
                "delivered": f"Your order **{order_id}** has been **delivered** ({o['days_since_order']} days ago). "
                             f"Product: {o['product_name']}. "
                             + ("It's eligible for a return if needed." if o['can_return'] else "The return window has closed."),
                "shipped":   f"Your order **{order_id}** is **on its way**! "
                             f"Product: {o['product_name']}. Tracking: {o['tracking_number']}. "
                             f"Estimated delivery: {o['estimated_delivery']}.",
                "processing": f"Your order **{order_id}** is currently being **processed**. "
                              f"Product: {o['product_name']}. Expected to ship within 1-2 business days.",
                "cancelled": f"Order **{order_id}** was **cancelled**. "
                             "If you didn't request this cancellation, please let me know and I'll escalate immediately.",
            }
            response_text = status_msgs.get(o["status"], f"Order {order_id} status: {o['status']}.")
            response_text += " Is there anything else I can help you with?"

    # ── RETURN ──
    elif intent == "return":
        order_id = _find_order_id(user_message)
        if not order_id:
            for h in reversed(history_dicts):
                oid = _find_order_id(h.get("content", ""))
                if oid:
                    order_id = oid
                    break
        if not order_id:
            response_text = (
                "I can help with that return! Please share your order ID "
                "(e.g. **ORD-12345**) and the reason for the return."
            )
        else:
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'get_order_status', 'input': {'order_id': order_id}})}\n\n"
            await asyncio.sleep(0.35)
            o = get_order_status(order_id)
            if not o["can_return"]:
                response_text = (
                    f"Unfortunately, order **{order_id}** ({o['product_name']}) is not eligible for a return "
                    f"— {'it was ordered more than 30 days ago' if o['days_since_order'] > 30 else 'it has not been delivered yet'}. "
                    "Would you like me to escalate this to our team?"
                )
            else:
                reason = "Customer-initiated return"
                for phrase in ["broken", "damaged", "wrong", "defect", "doesn't work", "does not work", "not working"]:
                    if phrase in user_message.lower():
                        reason = f"Product issue: {phrase}"
                        break
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'submit_return_request', 'input': {'order_id': order_id, 'product_name': o['product_name'], 'reason': reason}})}\n\n"
                await asyncio.sleep(0.4)
                r = submit_return_request(order_id, o["product_name"], reason)
                response_text = (
                    f"Return submitted for **{o['product_name']}** (order {order_id}). "
                    f"Confirmation number: **{r['confirmation_number']}**. "
                    f"{r['message']} Refund timeline: {r['refund_timeline']}. "
                    "Is there anything else I can help you with?"
                )

    # ── ESCALATION ──
    elif intent == "escalate":
        reason = f"Customer requested human agent. Original query: {user_message[:120]}"
        yield f"data: {json.dumps({'type': 'tool_call', 'tool': 'escalate_to_human', 'input': {'reason': reason, 'priority': 'normal'}})}\n\n"
        await asyncio.sleep(0.4)
        r = escalate_to_human(reason, "normal")
        conv = session.get(Conversation, conversation_id)
        if conv:
            conv.escalated = True
            conv.escalation_reason = reason
            conv.status = "escalated"
            session.add(conv)
            session.commit()
        escalated = True
        response_text = (
            f"Of course — I've escalated your case to our support team. "
            f"Case reference: **{r['case_reference']}**. "
            f"Expected response: {r['estimated_response']}. "
            "You'll receive a confirmation email shortly. I hope we can resolve this for you quickly!"
        )

    # ── FRUSTRATION ──
    elif intent == "frustration":
        response_text = (
            "I completely understand your frustration, and I'm sorry for the trouble. "
            "Let me do everything I can to resolve this right now. "
            "Would you like me to escalate your case to a senior support agent, "
            "or can I try to help resolve it here first?"
        )

    # ── THANKS ──
    elif intent == "thanks":
        response_text = (
            "You're very welcome! It was my pleasure helping you. "
            "Is there anything else I can assist you with today?"
        )

    # ── FAREWELL ──
    elif intent == "farewell":
        response_text = (
            "Thank you for contacting Cosmic Mart. I hope I was able to help. "
            "Have a great day."
        )
        # Mark conversation completed
        conv = session.get(Conversation, conversation_id)
        if conv and conv.status == "active":
            conv.status = "completed"
            session.add(conv)
            session.commit()

    # ── GENERAL ──
    else:
        response_text = (
            "I'm here to help! I can assist you with:\n\n"
            "• **Product availability** — just mention the product name or category\n"
            "• **Order tracking** — share your order ID (e.g. ORD-12345)\n"
            "• **Returns & refunds** — I can process eligible returns\n"
            "• **Human support** — just ask and I'll escalate immediately\n\n"
            "What can I do for you?"
        )

    # Stream the response text
    async for chunk in _stream_text(response_text):
        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

    # Save assistant message
    session.add(Message(conversation_id=conversation_id, role="assistant", content=response_text))
    session.commit()

    yield f"data: {json.dumps({'type': 'done', 'escalated': escalated})}\n\n"


# ─────────────────────────────────────────────
# MOCK SIGNAL EXTRACTION
# ─────────────────────────────────────────────

_AVAILABILITY_WORDS = ["available", "in stock", "stock", "have you got", "do you have", "can i get", "out of stock", "sold out", "when will"]
_RETURN_WORDS = ["return", "refund", "send back", "exchange", "broken", "defective", "damaged", "doesn't work"]
_PRICE_WORDS = ["expensive", "cheap", "price", "cost", "afford", "discount", "sale", "overpriced"]
_COMPETITOR_WORDS = ["amazon", "ebay", "walmart", "other store", "competitor", "elsewhere", "found it cheaper"]
_DEMAND_WORDS = ["need", "want", "looking for", "buy", "purchase", "order", "get one", "interested in"]
_NEGATIVE_WORDS = ["frustrat", "angry", "terrible", "awful", "horrible", "worst", "disappoint", "ridiculous", "unacceptable", "poor", "bad"]
_POSITIVE_WORDS = ["great", "excellent", "amazing", "wonderful", "perfect", "love", "happy", "thank", "appreciate", "good"]


def _text_sentiment(text: str) -> str:
    t = text.lower()
    neg = sum(1 for w in _NEGATIVE_WORDS if w in t)
    pos = sum(1 for w in _POSITIVE_WORDS if w in t)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def _urgency_score(text: str) -> int:
    t = text.lower()
    score = 3
    if t.count("!") >= 2 or any(w in t for w in ["urgent", "immediately", "asap", "right now", "today", "emergency"]):
        score = 5
    elif t.count("!") == 1 or any(w in t for w in ["soon", "quickly", "quick", "need it"]):
        score = 4
    elif any(w in t for w in ["whenever", "no rush", "just checking"]):
        score = 1
    return score


def extract_signals_mock(conversation_id: int, session: Session) -> dict:
    """Extract demand signals using keyword analysis — no Claude API."""
    conv = session.get(Conversation, conversation_id)
    if not conv:
        return {"error": "Conversation not found"}

    messages_db = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    ).all()

    if not messages_db:
        return {"signals": [], "message": "No messages"}

    products = _load_products()
    signals_stored = []
    overall_texts = []

    user_messages = [m for m in messages_db if m.role == "user"]

    for msg in user_messages:
        text = msg.content
        text_lower = text.lower()
        overall_texts.append(text_lower)

        # Find mentioned product
        matched = None
        for p in products:
            if p["name"].lower() in text_lower:
                matched = p
                break
        if not matched:
            for p in products:
                parts = [w for w in p["name"].split() if len(w) > 3]
                if any(w.lower() in text_lower for w in parts):
                    matched = p
                    break

        if matched is None:
            continue

        # Determine signal type
        if any(w in text_lower for w in _RETURN_WORDS):
            signal_type = "return_intent"
            return_reason = next((w for w in ["broken", "defective", "damaged", "wrong size", "doesn't work"] if w in text_lower), "customer preference")
        elif any(w in text_lower for w in _COMPETITOR_WORDS):
            signal_type = "competitor_mention"
            return_reason = None
        elif any(w in text_lower for w in _PRICE_WORDS):
            signal_type = "price_concern"
            return_reason = None
        elif any(w in text_lower for w in _AVAILABILITY_WORDS):
            signal_type = "availability_complaint" if any(w in text_lower for w in ["out of stock", "not available", "sold out", "don't have"]) else "demand_expressed"
            return_reason = None
        elif any(w in text_lower for w in _DEMAND_WORDS):
            signal_type = "demand_expressed"
            return_reason = None
        else:
            continue

        sentiment = _text_sentiment(text)
        urgency = _urgency_score(text)

        # Extract a raw quote (first sentence mentioning the product or signal)
        sentences = re.split(r'[.!?]', text)
        raw_quote = next(
            (s.strip() for s in sentences if matched["name"].split()[0].lower() in s.lower() and len(s.strip()) > 10),
            text[:100]
        )

        sig = Signal(
            conversation_id=conversation_id,
            extracted_at=datetime.now(timezone.utc),
            product_id=matched["id"],
            product_name=matched["name"],
            signal_type=signal_type,
            sentiment=sentiment,
            complaint_category="availability" if signal_type == "availability_complaint" else None,
            return_reason=return_reason if signal_type == "return_intent" else None,
            market=conv.market,
            urgency=urgency,
            raw_quote=raw_quote,
            confidence=0.75,
        )
        session.add(sig)
        signals_stored.append(sig)

    session.commit()

    all_text = " ".join(overall_texts)
    overall_sentiment = _text_sentiment(all_text)

    return {
        "signals_extracted": len(signals_stored),
        "overall_sentiment": overall_sentiment,
        "escalation_detected": conv.escalated,
        "summary": f"Mock extraction: {len(signals_stored)} signals from {len(user_messages)} customer messages."
    }


# ─────────────────────────────────────────────
# MOCK FORECASTING
# ─────────────────────────────────────────────

_RISK_THRESHOLDS = [
    (7,   "critical_understock", 0.92),
    (14,  "understock",          0.70),
    (45,  "normal",              0.20),
    (90,  "overstock",           0.60),
    (999, "critical_overstock",  0.88),
]

_RECOMMENDATIONS = {
    "critical_understock": "Expedite replenishment immediately. Place emergency purchase order to avoid stockout.",
    "understock":          "Increase order quantity by 30-40% at next reorder cycle. Monitor daily.",
    "normal":              "Maintain current reorder cadence. No immediate action required.",
    "overstock":           "Pause next scheduled order. Consider promotional pricing to accelerate sell-through.",
    "critical_overstock":  "Suspend all purchase orders for this SKU. Launch clearance promotion immediately.",
}

_REASONING = {
    "critical_understock": (
        "Current days of supply is critically low, with stockout imminent within one week. "
        "Customer demand signals show high urgency and availability complaints. "
        "Immediate procurement action is required to avoid lost sales and reputational damage."
    ),
    "understock": (
        "Stock levels are below the recommended safety threshold. "
        "Recent demand signals indicate sustained customer interest. "
        "Increasing the next purchase order will prevent escalation to critical status."
    ),
    "normal": (
        "Inventory is within the healthy operating range. "
        "Demand signals are balanced with no significant anomalies. "
        "Routine reorder schedule is appropriate."
    ),
    "overstock": (
        "Current stock significantly exceeds the 45-day supply threshold. "
        "Demand signals are weak relative to inventory levels. "
        "Delaying the next order and reducing selling price will improve inventory turnover."
    ),
    "critical_overstock": (
        "Excess inventory is approaching a critical level, tying up capital and warehouse space. "
        "Demand signals show very low customer interest in this market. "
        "Aggressive clearance action is needed to reduce carrying costs."
    ),
}


def generate_forecasts_mock(session: Session, market: str | None = None) -> list[dict]:
    """Formula-based forecasting — no Claude API. Deterministic from inventory data."""
    products = _load_products()
    products_by_id = {p["id"]: p["name"] for p in products}

    inv_query = select(Inventory)
    if market:
        inv_query = inv_query.where(Inventory.market == market)
    inventories = session.exec(inv_query).all()

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    sig_query = select(Signal).where(Signal.extracted_at >= cutoff)
    if market:
        sig_query = sig_query.where(Signal.market == market)
    signals = session.exec(sig_query).all()

    sig_map: dict[tuple, list] = {}
    for s in signals:
        key = (s.product_id or s.product_name, s.market)
        sig_map.setdefault(key, []).append(s)

    stored: list[dict] = []

    for inv in inventories:
        dos = inv.days_of_supply
        risk_level = "normal"
        base_score = 0.2
        for threshold, level, score in _RISK_THRESHOLDS:
            if dos < threshold:
                risk_level, base_score = level, score
                break

        sigs = sig_map.get((inv.product_id, inv.market), [])
        signal_count = len(sigs)

        # Sentiment: negative signals push understock risk up, positive pushes overstock risk up
        if sigs:
            neg = sum(1 for s in sigs if s.sentiment == "negative")
            pos = sum(1 for s in sigs if s.sentiment == "positive")
            sentiment_score = (pos - neg) / signal_count  # -1 to +1
            avg_sentiment = (sum({"positive": 1.0, "neutral": 0.5, "negative": 0.0}[s.sentiment] for s in sigs)) / signal_count
        else:
            avg_sentiment = 0.5
            sentiment_score = 0.0

        # Adjust risk score with signals (capped 0–1)
        risk_score = min(1.0, max(0.0, base_score + signal_count * 0.02 - sentiment_score * 0.1))

        # Only store non-normal items, or items with signals
        if risk_level == "normal" and signal_count == 0:
            continue

        product_name = products_by_id.get(inv.product_id, inv.product_id)
        rec = _RECOMMENDATIONS[risk_level]
        reasoning = _REASONING[risk_level]

        fc = Forecast(
            generated_at=datetime.now(timezone.utc),
            product_id=inv.product_id,
            product_name=product_name,
            market=inv.market,
            risk_level=risk_level,
            risk_score=round(risk_score, 3),
            signal_count=signal_count,
            avg_signal_sentiment=round(avg_sentiment, 2),
            current_stock=inv.current_stock,
            recommendation=rec,
            ai_reasoning=reasoning,
            data_sources=json.dumps(["inventory_db", "signals_db", "sales_history"]),
        )
        session.add(fc)
        stored.append({
            "product_id": inv.product_id,
            "product_name": product_name,
            "market": inv.market,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "recommendation": rec,
        })

    session.commit()
    return stored


# ─────────────────────────────────────────────
# MOCK DASHBOARD SUMMARY
# ─────────────────────────────────────────────

def get_mock_summary(session: Session) -> dict:
    """Generate executive summary from DB stats — no Claude API."""
    signals = session.exec(select(Signal)).all()
    forecasts = session.exec(select(Forecast).order_by(Forecast.generated_at.desc())).all()
    conversations = session.exec(select(Conversation)).all()

    total_convs = len(conversations)
    total_sigs = len(signals)
    neg = sum(1 for s in signals if s.sentiment == "negative")
    pos = sum(1 for s in signals if s.sentiment == "positive")
    neg_pct = round(neg / total_sigs * 100, 1) if total_sigs else 0.0

    seen = set()
    unique_forecasts = []
    for f in forecasts:
        k = (f.product_id, f.market)
        if k not in seen:
            seen.add(k)
            unique_forecasts.append(f)

    critical = [f for f in unique_forecasts if f.risk_level in ("critical_understock", "critical_overstock")]
    top_critical = critical[0] if critical else None

    if top_critical:
        action = (
            f"Priority action: {top_critical.recommendation.split('.')[0]} "
            f"for {top_critical.product_name} in {top_critical.market}."
        )
    else:
        action = "No critical inventory issues detected. Maintain current procurement cadence."

    summary = (
        f"Cosmic Mart is currently tracking {total_convs} customer conversations, "
        f"generating {total_sigs} demand signals with a {neg_pct}% negative sentiment rate "
        f"(peer benchmark: 19.5%). "
        f"{'Negative sentiment is elevated — customer support capacity and stock availability should be reviewed.' if neg_pct > 19.5 else 'Sentiment is within peer benchmark range.'} "
        f"{len(critical)} critical inventory risk(s) identified across markets. "
        f"{action}"
    )

    return {
        "summary": summary,
        "metrics": {
            "total_conversations": total_convs,
            "total_signals": total_sigs,
            "negative_sentiment_pct": neg_pct,
            "positive_signals": pos,
            "critical_issues": len(critical),
            "peer_benchmark_pct": 19.5,
        },
    }
