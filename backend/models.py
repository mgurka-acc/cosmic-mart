from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
import json


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    market: str
    customer_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    status: str = "active"  # active | completed | escalated


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_calls: Optional[str] = None  # JSON blob


class Signal(SQLModel, table=True):
    __tablename__ = "signals"
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    product_id: Optional[str] = None
    product_name: str
    signal_type: str  # demand_expressed|availability_complaint|return_intent|price_concern|competitor_mention
    sentiment: str  # positive|neutral|negative
    complaint_category: Optional[str] = None
    return_reason: Optional[str] = None
    market: str
    urgency: int = 3  # 1-5
    raw_quote: Optional[str] = None
    confidence: float = 0.8


class Inventory(SQLModel, table=True):
    __tablename__ = "inventory"
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(index=True)
    market: str = Field(index=True)
    current_stock: int
    reorder_point: int
    safety_stock: int
    avg_daily_sales: float
    days_of_supply: float
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SalesHistory(SQLModel, table=True):
    __tablename__ = "sales_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(index=True)
    market: str
    sale_date: str  # YYYY-MM-DD
    units_sold: int
    revenue: float


class Forecast(SQLModel, table=True):
    __tablename__ = "forecasts"
    id: Optional[int] = Field(default=None, primary_key=True)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    product_id: str
    product_name: str
    market: str
    risk_level: str  # critical_understock|understock|normal|overstock|critical_overstock
    risk_score: float
    signal_count: int = 0
    avg_signal_sentiment: float = 0.0
    current_stock: int
    recommendation: str
    ai_reasoning: str
    data_sources: str  # JSON list
