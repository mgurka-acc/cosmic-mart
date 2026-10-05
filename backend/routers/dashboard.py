from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from backend.config import settings
from backend.database import get_session
from backend.models import Signal, Forecast, Conversation

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(session: Session = Depends(get_session)):
    if settings.use_mock:
        from backend.agents.mock_agents import get_mock_summary
        return get_mock_summary(session)

    # ── Live Claude summary ──
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key)

    signals = session.exec(select(Signal).order_by(Signal.extracted_at.desc()).limit(100)).all()
    forecasts = session.exec(select(Forecast).order_by(Forecast.generated_at.desc()).limit(50)).all()
    total_conversations = session.exec(select(Conversation)).all()

    neg_count = sum(1 for s in signals if s.sentiment == "negative")
    pos_count = sum(1 for s in signals if s.sentiment == "positive")
    total_signals = len(signals)
    sentiment_pct = round(neg_count / total_signals * 100, 1) if total_signals else 0
    critical = [f for f in forecasts if f.risk_level in ("critical_understock", "critical_overstock")]

    top_issues = [f"{f.product_name} ({f.market}): {f.risk_level} - {f.recommendation}" for f in critical[:5]]
    signal_breakdown = {}
    for s in signals:
        signal_breakdown[s.signal_type] = signal_breakdown.get(s.signal_type, 0) + 1

    prompt = f"""Generate a concise executive summary for Cosmic Mart leadership.

KEY METRICS:
- Total conversations analyzed: {len(total_conversations)}
- Demand signals extracted: {total_signals}
- Negative sentiment rate: {sentiment_pct}% (peer benchmark: 19.5%)
- Positive signals: {pos_count}
- Critical inventory issues: {len(critical)}

SIGNAL BREAKDOWN:
{signal_breakdown}

TOP CRITICAL ISSUES:
{chr(10).join(top_issues) if top_issues else "No critical issues detected"}

Write a 3-4 sentence executive summary highlighting: (1) current customer sentiment trend, (2) top inventory risk, (3) recommended immediate action. Be direct and data-driven."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return {
        "summary": response.content[0].text,
        "metrics": {
            "total_conversations": len(total_conversations),
            "total_signals": total_signals,
            "negative_sentiment_pct": sentiment_pct,
            "positive_signals": pos_count,
            "critical_issues": len(critical),
            "peer_benchmark_pct": 19.5
        }
    }


@router.get("/sentiment")
def get_sentiment(session: Session = Depends(get_session)):
    signals = session.exec(select(Signal)).all()
    breakdown = {"positive": 0, "neutral": 0, "negative": 0}
    by_market: dict = {}
    for s in signals:
        breakdown[s.sentiment] = breakdown.get(s.sentiment, 0) + 1
        if s.market not in by_market:
            by_market[s.market] = {"positive": 0, "neutral": 0, "negative": 0}
        by_market[s.market][s.sentiment] = by_market[s.market].get(s.sentiment, 0) + 1
    total = sum(breakdown.values())
    return {
        "breakdown": breakdown,
        "negative_pct": round(breakdown["negative"] / total * 100, 1) if total else 0,
        "by_market": by_market,
        "total_signals": total
    }


@router.get("/heatmap")
def get_heatmap(session: Session = Depends(get_session)):
    forecasts = session.exec(select(Forecast).order_by(Forecast.generated_at.desc())).all()
    seen: set = set()
    heatmap = []
    for f in forecasts:
        key = (f.product_id, f.market)
        if key not in seen:
            seen.add(key)
            heatmap.append({
                "product_id": f.product_id,
                "product_name": f.product_name,
                "market": f.market,
                "risk_level": f.risk_level,
                "risk_score": f.risk_score,
                "current_stock": f.current_stock,
                "signal_count": f.signal_count,
                "recommendation": f.recommendation,
                "ai_reasoning": f.ai_reasoning
            })
    return {"heatmap": heatmap, "count": len(heatmap)}
