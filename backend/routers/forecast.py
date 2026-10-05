from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import Forecast
from backend.agents.forecast_agent import generate_forecasts

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
def get_forecasts(market: str = None, session: Session = Depends(get_session)):
    query = select(Forecast).order_by(Forecast.generated_at.desc())

    # Get only most recent forecast per product x market
    all_forecasts = session.exec(query).all()
    seen = set()
    unique = []
    for f in all_forecasts:
        key = (f.product_id, f.market)
        if key not in seen:
            if market is None or f.market == market:
                seen.add(key)
                unique.append(f)

    return {"forecasts": [f.model_dump() for f in unique], "count": len(unique)}


@router.post("/generate")
def generate(market: str = None, session: Session = Depends(get_session)):
    forecasts = generate_forecasts(session, market)
    return {"generated": len(forecasts), "forecasts": forecasts}
