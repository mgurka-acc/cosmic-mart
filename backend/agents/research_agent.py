import json
import random

def get_market_research(product_name: str, market: str) -> dict:
    """Return mock market intelligence data."""
    observations = [
        {
            "source": "Retail Intelligence Weekly",
            "type": "competitor_activity",
            "insight": f"Major competitors increasing {product_name} inventory by 20-30% ahead of holiday season in {market} market.",
            "relevance": "high",
            "date": "2026-09-28"
        },
        {
            "source": "Consumer Trends Report Q4 2026",
            "type": "demand_trend",
            "insight": f"Online searches for {product_name.split()[0]} products up 34% YoY in {market}. Consumers prioritizing value and durability.",
            "relevance": "high",
            "date": "2026-10-01"
        },
        {
            "source": "Supply Chain Monitor",
            "type": "supply_risk",
            "insight": "Component shortages affecting premium electronics segment. Lead times extending 3-4 weeks vs. historical average.",
            "relevance": "medium",
            "date": "2026-09-30"
        },
        {
            "source": "Social Commerce Analytics",
            "type": "sentiment_trend",
            "insight": f"Brand mentions for {product_name.split()[0]}-category items trending positive after influencer campaign launch in {market}.",
            "relevance": "medium",
            "date": "2026-10-02"
        },
        {
            "source": "Macroeconomic Outlook",
            "type": "macro_signal",
            "insight": f"Consumer confidence index in {market} at 6-month high. Discretionary spending expected to increase 8% QoQ.",
            "relevance": "low",
            "date": "2026-09-25"
        }
    ]

    return {
        "product": product_name,
        "market": market,
        "research_date": "2026-10-05",
        "source_label": "External Market Intelligence",
        "disclaimer": "Mock data for demo purposes",
        "observations": observations[:4],
        "demand_outlook": random.choice(["bullish", "neutral", "cautious"]),
        "competitive_pressure": random.choice(["low", "medium", "high"])
    }
