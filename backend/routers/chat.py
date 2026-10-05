import json
import uuid
import traceback
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from backend.database import get_session, engine
from backend.models import Conversation, Message
from backend.agents.support_agent import run_support_agent_streaming
from backend.agents.signal_agent import extract_signals_from_conversation

router = APIRouter(prefix="/api/chat", tags=["chat"])


class StartChatRequest(BaseModel):
    market: str = "US"
    customer_id: str | None = None


class MessageRequest(BaseModel):
    conversation_id: int
    message: str


@router.post("/start")
def start_chat(req: StartChatRequest, session: Session = Depends(get_session)):
    conv = Conversation(
        session_id=str(uuid.uuid4()),
        market=req.market,
        customer_id=req.customer_id or f"CUST-{uuid.uuid4().hex[:8].upper()}"
    )
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return {"conversation_id": conv.id, "session_id": conv.session_id, "market": conv.market}


@router.post("/message")
async def send_message(req: MessageRequest, background_tasks: BackgroundTasks):
    # Short-lived validation session — closes before streaming begins to avoid SQLite write-lock conflict
    with Session(engine) as check_session:
        conv = check_session.get(Conversation, req.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.status != "active":
            raise HTTPException(status_code=400, detail=f"Conversation is {conv.status}")
        market = conv.market

    conversation_id = req.conversation_id
    message = req.message

    async def stream_generator():
        try:
            with Session(engine) as stream_session:
                async for chunk in run_support_agent_streaming(
                    conversation_id, message, market, stream_session
                ):
                    yield chunk
        except Exception as exc:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        def _extract():
            with Session(engine) as bg_session:
                bg_conv = bg_session.get(Conversation, conversation_id)
                if bg_conv and bg_conv.status in ("completed", "escalated"):
                    extract_signals_from_conversation(conversation_id, bg_session)

        background_tasks.add_task(_extract)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@router.get("/{conversation_id}/history")
def get_history(conversation_id: int, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = session.exec(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp)
    ).all()
    return {
        "conversation_id": conversation_id,
        "market": conv.market,
        "status": conv.status,
        "messages": [{"role": m.role, "content": m.content, "timestamp": str(m.timestamp)} for m in messages]
    }
