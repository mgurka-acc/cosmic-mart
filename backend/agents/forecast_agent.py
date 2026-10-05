import json
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from backend.config import settings
from backend.models import Signal, Inventory, SalesHistory, Forecast


def generate_forecasts(session: Session, market: str | None = None) -> list[dict]:
    if settings.use_mock:
        from backend.agents.mock_agents import generate_forecasts_mock
        return generate_forecasts_mock(session, market)

    # ── Live Claude forecasting ──
    from anthropic import Anthropic
    from pathlib import Path
    client = Anthropic(api_key=settings.anthropic_api_key)

    FORECAST_SYSTEM = """You are a demand forecasting AI for Cosmic Mart. Given product inventory and demand signal data, generate risk-based procurement recommendations.

Return ONLY a valid JSON array of forecast objects. No markdown, no explanation.

Each object must have:
{
  "product_id": "PROD-XXX",
  "product_name": "string",
  "market": "string",
  "risk_level": "critical_understock|understock|normal|overstock|critical_overstock",
  "risk_score": 0.85,
  "recommendation": "brief action recommendation",
  "ai_reasoning": "2-3 sentence reasoning"
}"""

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    sig_query = select(Signal).where(Signal.extracted_at >= cutoff)
    if market:
        sig_query = sig_query.where(Signal.market == market)
    signals = session.exec(sig_query).all()

    signal_groups: dict[tuple, list] = {}
    for sig in signals:
        key = (sig.product_id or sig.product_name, sig.market)
        signal_groups.setdefault(key, []).append(sig)

    inv_query = select(Inventory)
    if market:
        inv_query = inv_query.where(Inventory.market == market)
    inventories = session.exec(inv_query).all()

    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    sales = session.exec(select(SalesHistory)).all()

    import json as _json
    products_file = Path(__file__).parent.parent / "data" / "products.json"
    with open(products_file) as f:
        products_lookup = {p["id"]: p["name"] for p in _json.load(f)}

    def _sent(s: str) -> float:
        return {"positive": 1.0, "neutral": 0.5, "negative": 0.0}.get(s, 0.5)

    product_data = []
    for inv in inventories:
        key = (inv.product_id, inv.market)
        sigs = signal_groups.get(key, [])
        sales_7d = sum(s.units_sold for s in sales if s.product_id == inv.product_id and s.market == inv.market and s.sale_date >= seven_days_ago)
        sales_30d = sum(s.units_sold for s in sales if s.product_id == inv.product_id and s.market == inv.market and s.sale_date >= thirty_days_ago)
        sc = len(sigs)
        avg_s = sum(_sent(s.sentiment) for s in sigs) / sc if sc else 0.5
        product_data.append({
            "product_id": inv.product_id,
            "product_name": products_lookup.get(inv.product_id, inv.product_id),
            "market": inv.market,
            "current_stock": inv.current_stock,
            "days_of_supply": round(inv.days_of_supply, 1),
            "avg_daily_sales": inv.avg_daily_sales,
            "sales_last_7_days": sales_7d,
            "sales_last_30_days": sales_30d,
            "signal_count": sc,
            "avg_sentiment_score": round(avg_s, 2),
        })

    if not product_data:
        return []

    prompt = f"""Generate procurement risk forecasts for the following products.

PRODUCT INVENTORY AND DEMAND DATA:
{json.dumps(product_data, indent=2)}

Return a JSON array with one forecast per product that needs attention."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=FORECAST_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    forecasts_data = json.loads(raw)

    stored = []
    inv_map = {(i.product_id, i.market): i for i in inventories}
    pd_map = {(p["product_id"], p["market"]): p for p in product_data}

    for fc in forecasts_data:
        inv_row = inv_map.get((fc["product_id"], fc["market"]))
        stats = pd_map.get((fc["product_id"], fc["market"]), {})
        forecast = Forecast(
            generated_at=datetime.now(timezone.utc),
            product_id=fc["product_id"],
            product_name=fc.get("product_name", products_lookup.get(fc["product_id"], fc["product_id"])),
            market=fc["market"],
            risk_level=fc["risk_level"],
            risk_score=fc.get("risk_score", 0.5),
            signal_count=stats.get("signal_count", 0),
            avg_signal_sentiment=stats.get("avg_sentiment_score", 0.5),
            current_stock=inv_row.current_stock if inv_row else 0,
            recommendation=fc.get("recommendation", ""),
            ai_reasoning=fc.get("ai_reasoning", ""),
            data_sources=json.dumps(["inventory_db", "signals_db", "sales_history"])
        )
        session.add(forecast)
        stored.append(fc)

    session.commit()
    return stored
