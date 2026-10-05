"""Seed the database with synthetic data and run signal extraction on sample conversations."""
import sys
import os
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env before any backend imports that create API clients
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from sqlmodel import Session, select
from backend.database import engine, create_tables
from backend.models import Inventory, SalesHistory, Conversation, Message, Signal
from backend.agents.signal_agent import extract_signals_from_conversation

DATA_DIR = Path(__file__).parent.parent / "data"
MARKETS_FILE = DATA_DIR / "markets.json"
PRODUCTS_FILE = DATA_DIR / "products.json"
CONVS_FILE = DATA_DIR / "sample_conversations.json"

random.seed(42)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def seed_inventory(session: Session, products: list, markets: list):
    print("Seeding inventory...")
    existing = session.exec(select(Inventory)).all()
    if existing:
        print("  Inventory already seeded, skipping.")
        return

    for product in products:
        for market in markets:
            # Base daily sales varies by product category and market
            base_sales = random.uniform(2.0, 15.0)

            # Hardcoded demo scenarios
            if product["id"] == "PROD-011" and market["id"] == "UK":  # Graviton Mattress x UK
                days_of_supply = 4
                avg_daily = 12.0
                current_stock = int(days_of_supply * avg_daily)
            elif product["id"] == "PROD-001" and market["id"] == "JP":  # PulsarPhone x JP
                days_of_supply = 180
                avg_daily = 3.0
                current_stock = int(days_of_supply * avg_daily)
            elif product["id"] == "PROD-021" and market["id"] == "BR":  # NebulaFresh x BR
                days_of_supply = 6
                avg_daily = 18.0
                current_stock = int(days_of_supply * avg_daily)
            else:
                avg_daily = base_sales
                days_of_supply = random.uniform(20, 60)
                current_stock = int(days_of_supply * avg_daily)

            reorder_point = int(avg_daily * 14)
            safety_stock = int(avg_daily * 7)

            inv = Inventory(
                product_id=product["id"],
                market=market["id"],
                current_stock=current_stock,
                reorder_point=reorder_point,
                safety_stock=safety_stock,
                avg_daily_sales=avg_daily,
                days_of_supply=days_of_supply,
                last_updated=datetime.now(timezone.utc)
            )
            session.add(inv)
    session.commit()
    print(f"  Seeded inventory for {len(products)} products x {len(markets)} markets")


def seed_sales_history(session: Session, products: list, markets: list):
    print("Seeding sales history (90 days)...")
    existing = session.exec(select(SalesHistory)).all()
    if existing:
        print("  Sales history already seeded, skipping.")
        return

    today = datetime.now(timezone.utc).date()
    for product in products:
        for market in markets:
            inv = session.exec(
                select(Inventory).where(
                    Inventory.product_id == product["id"],
                    Inventory.market == market["id"]
                )
            ).first()
            avg_daily = inv.avg_daily_sales if inv else 5.0

            for days_back in range(90):
                sale_date = today - timedelta(days=days_back)
                units = max(0, int(random.gauss(avg_daily, avg_daily * 0.3)))
                revenue = units * product["price"] * random.uniform(0.9, 1.0)

                sale = SalesHistory(
                    product_id=product["id"],
                    market=market["id"],
                    sale_date=str(sale_date),
                    units_sold=units,
                    revenue=round(revenue, 2)
                )
                session.add(sale)
    session.commit()
    print("  Seeded 90 days of sales history")


def seed_conversations(session: Session, sample_convs: list):
    print("Seeding sample conversations...")
    existing = session.exec(select(Conversation)).all()
    if existing:
        print("  Conversations already seeded, skipping.")
        return

    today = datetime.now(timezone.utc)
    conv_ids = []

    for i, conv_data in enumerate(sample_convs):
        started_at = today - timedelta(days=random.randint(1, 7), hours=random.randint(0, 23))
        ended_at = started_at + timedelta(minutes=random.randint(5, 20))

        is_escalation = conv_data.get("scenario", "").startswith("escalation")
        conv = Conversation(
            session_id=f"seed-session-{i+1:03d}",
            market=conv_data["market"],
            customer_id=f"CUST-SEED-{i+1:04d}",
            started_at=started_at,
            ended_at=ended_at,
            escalated=is_escalation,
            escalation_reason="Customer requested human agent" if is_escalation else None,
            status="escalated" if is_escalation else "completed"
        )
        session.add(conv)
        session.commit()
        session.refresh(conv)

        # Add messages
        msg_time = started_at
        for msg_data in conv_data["messages"]:
            msg_time += timedelta(seconds=random.randint(15, 90))
            msg = Message(
                conversation_id=conv.id,
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=msg_time
            )
            session.add(msg)
        session.commit()
        conv_ids.append(conv.id)

    print(f"  Seeded {len(conv_ids)} conversations")
    return conv_ids


def extract_all_signals(session: Session, conv_ids: list):
    print(f"Extracting signals from {len(conv_ids)} conversations...")
    for i, conv_id in enumerate(conv_ids):
        try:
            result = extract_signals_from_conversation(conv_id, session)
            print(f"  [{i+1}/{len(conv_ids)}] Conv {conv_id}: {result.get('signals_extracted', 0)} signals extracted")
        except Exception as e:
            print(f"  [{i+1}/{len(conv_ids)}] Conv {conv_id}: ERROR - {e}")


def main():
    print("=== Cosmic Mart Database Seeder ===")
    create_tables()

    products = load_json(PRODUCTS_FILE)
    markets = load_json(MARKETS_FILE)
    sample_convs = load_json(CONVS_FILE)

    with Session(engine) as session:
        seed_inventory(session, products, markets)
        seed_sales_history(session, products, markets)
        conv_ids = seed_conversations(session, sample_convs)
        if conv_ids:
            extract_all_signals(session, conv_ids)

    print("\n=== Seeding complete! ===")


if __name__ == "__main__":
    main()
