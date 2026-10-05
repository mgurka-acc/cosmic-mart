import json
from typing import AsyncIterator
from sqlmodel import Session, select
from backend.config import settings
from backend.models import Conversation, Message
from backend.tools.product_tools import search_product_catalog, PRODUCT_TOOL_DEF
from backend.tools.order_tools import get_order_status, submit_return_request, GET_ORDER_TOOL_DEF, SUBMIT_RETURN_TOOL_DEF
from backend.tools.escalation_tools import escalate_to_human, ESCALATE_TOOL_DEF

TOOLS = [PRODUCT_TOOL_DEF, GET_ORDER_TOOL_DEF, SUBMIT_RETURN_TOOL_DEF, ESCALATE_TOOL_DEF]

SYSTEM_PROMPT = """You are Nova, Cosmic Mart's friendly AI customer support assistant. Cosmic Mart is an interstellar retail brand selling space-themed electronics, appliances, furniture, clothing, and food.

Your role:
- Help customers with product availability and stock questions
- Look up order status and process returns
- Escalate to humans when appropriate or when the customer requests it
- Be warm, efficient, and solution-focused

Guidelines:
- Always check actual stock before making availability claims
- If stock is low (< 10 units or < 7 days of supply), proactively warn the customer
- For returns, always check order status first before submitting
- If a customer seems frustrated or explicitly asks for a human, escalate immediately
- Keep responses concise and helpful

When a conversation naturally concludes, say a brief farewell."""


def _execute_tool(tool_name: str, tool_input: dict, session: Session) -> str:
    if tool_name == "search_product_catalog":
        result = search_product_catalog(tool_input["query"], tool_input["market"], session)
    elif tool_name == "get_order_status":
        result = get_order_status(tool_input["order_id"])
    elif tool_name == "submit_return_request":
        result = submit_return_request(
            tool_input["order_id"],
            tool_input["product_name"],
            tool_input["reason"]
        )
    elif tool_name == "escalate_to_human":
        result = escalate_to_human(tool_input["reason"], tool_input.get("priority", "normal"))
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result)


async def run_support_agent_streaming(
    conversation_id: int,
    user_message: str,
    market: str,
    session: Session
) -> AsyncIterator[str]:
    """Route to mock or live Claude agent based on USE_MOCK setting."""
    if settings.use_mock:
        from backend.agents.mock_agents import run_mock_support_agent_streaming
        async for chunk in run_mock_support_agent_streaming(conversation_id, user_message, market, session):
            yield chunk
        return

    # ── Live Claude agent ──
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    messages_db = session.exec(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp)
    ).all()
    messages = [{"role": m.role, "content": m.content} for m in messages_db if m.role in ("user", "assistant")]
    messages.append({"role": "user", "content": user_message})

    session.add(Message(conversation_id=conversation_id, role="user", content=user_message))
    session.commit()

    escalated = False
    full_response = ""

    for _ in range(10):
        stream_text = ""
        tool_calls = []

        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOLS
        ) as stream:
            async for event in stream:
                event_type = type(event).__name__
                if event_type == "RawContentBlockDeltaEvent":
                    delta = event.delta
                    if hasattr(delta, "text"):
                        stream_text += delta.text
                        full_response += delta.text
                        yield f"data: {json.dumps({'type': 'text', 'content': delta.text})}\n\n"
            final_message = await stream.get_final_message()
            stop_reason = final_message.stop_reason
            for block in final_message.content:
                if block.type == "tool_use":
                    tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

        if stop_reason == "end_turn" or not tool_calls:
            session.add(Message(conversation_id=conversation_id, role="assistant", content=stream_text or full_response))
            session.commit()
            break

        assistant_content = []
        if stream_text:
            assistant_content.append({"type": "text", "text": stream_text})
        for tc in tool_calls:
            assistant_content.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]})
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tc in tool_calls:
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': tc['name'], 'input': tc['input']})}\n\n"
            result = _execute_tool(tc["name"], tc["input"], session)
            tool_results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": result})
            if tc["name"] == "escalate_to_human":
                escalated = True
                conv = session.get(Conversation, conversation_id)
                if conv:
                    conv.escalated = True
                    conv.escalation_reason = tc["input"].get("reason", "")
                    conv.status = "escalated"
                    session.add(conv)
                    session.commit()
        messages.append({"role": "user", "content": tool_results})
        stream_text = ""

    conv = session.get(Conversation, conversation_id)
    if conv and conv.status == "active":
        farewell_words = ["goodbye", "bye", "have a great", "take care", "farewell", "best wishes"]
        if any(word in full_response.lower() for word in farewell_words):
            conv.status = "completed"
            session.add(conv)
            session.commit()

    yield f"data: {json.dumps({'type': 'done', 'escalated': escalated})}\n\n"
