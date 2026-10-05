"""Reset DB to clean demo state. Run before presentation."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from sqlmodel import Session, SQLModel
from backend.database import engine, create_tables
from backend.models import Conversation, Message, Signal, Inventory, SalesHistory, Forecast

def reset_database():
    print("=== Resetting Cosmic Mart Demo Database ===")

    # Drop and recreate all tables
    SQLModel.metadata.drop_all(engine)
    create_tables()
    print("  Tables reset.")

    # Run seeder
    from backend.scripts.seed_database import main as seed_main
    seed_main()

    # Generate forecasts
    print("Generating forecasts...")
    from backend.agents.forecast_agent import generate_forecasts
    with Session(engine) as session:
        forecasts = generate_forecasts(session)
        print(f"  Generated {len(forecasts)} forecasts")

    print("\n=== Demo database ready! ===")
    print("Run: uvicorn backend.main:app --reload")
    print("Then: cd frontend && npm run dev")

if __name__ == "__main__":
    reset_database()
