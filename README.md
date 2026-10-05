# Cosmic Mart AI Agent System

Three-stage pipeline: **Listen → Extract → Act**

```
Customer Chat  →  Signal Extraction Agent  →  Forecasting Agent  →  Leadership Dashboard
```

## Setup

### 1. Add your Anthropic API key

Edit `.env` in the project root:
```
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

### 2. Backend

```bash
# From project root
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

pip install -r backend/requirements.txt

# Seed database (runs Claude API for signal extraction — takes ~2 min)
python backend/scripts/seed_database.py

# Start API server
uvicorn backend.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:
- **Customer view:** http://localhost:5173
- **Leadership dashboard:** http://localhost:5173/dashboard

## Demo reset (before presentation)

```bash
python backend/scripts/generate_demo_data.py
```

This drops and re-seeds all tables, then generates fresh forecasts.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/start` | Start a conversation |
| POST | `/api/chat/message` | Send message (SSE streaming) |
| GET | `/api/chat/{id}/history` | Get conversation history |
| GET | `/api/signals` | List demand signals |
| POST | `/api/signals/extract/{id}` | Extract signals from conversation |
| GET | `/api/forecast` | Get latest forecasts |
| POST | `/api/forecast/generate` | Generate new forecasts |
| GET | `/api/dashboard/summary` | AI executive summary |
| GET | `/api/dashboard/sentiment` | Sentiment breakdown |
| GET | `/api/dashboard/heatmap` | Heatmap data |

## Architecture

| Agent | Model | Role |
|-------|-------|------|
| Nova (Support) | claude-sonnet-4-6 | Multi-turn chat with tools (streaming) |
| Signal Extraction | claude-haiku-4-5-20251001 | Batch transcript analysis |
| Demand Forecasting | claude-sonnet-4-6 | Multi-source risk reasoning |
| Dashboard Summary | claude-haiku-4-5-20251001 | Executive summary generation |
