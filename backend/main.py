from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import create_tables
from backend.routers import chat, signals, forecast, dashboard

app = FastAPI(title="Cosmic Mart AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(signals.router)
app.include_router(forecast.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def on_startup():
    create_tables()


@app.get("/health")
def health():
    return {"status": "ok", "service": "Cosmic Mart AI"}
