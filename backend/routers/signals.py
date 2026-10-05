from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import Signal
from backend.agents.signal_agent import extract_signals_from_conversation

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("")
def get_signals(market: str = None, limit: int = 50, session: Session = Depends(get_session)):
    query = select(Signal).order_by(Signal.extracted_at.desc()).limit(limit)
    if market:
        query = select(Signal).where(Signal.market == market).order_by(Signal.extracted_at.desc()).limit(limit)
    signals = session.exec(query).all()
    return {"signals": [s.model_dump() for s in signals], "count": len(signals)}


@router.post("/extract/{conversation_id}")
def extract_signals(conversation_id: int, session: Session = Depends(get_session)):
    result = extract_signals_from_conversation(conversation_id, session)
    return result
