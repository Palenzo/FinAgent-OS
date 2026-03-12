# FinAgent OS

> **10-agent autonomous financial operations platform** — AI agents collaborate to handle P&L analysis, forecasting, anomaly detection, and month-end close with zero human intervention.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph State Machine                │
│                                                             │
│  START → Orchestrator → Data Ingestion                     │
│                              │                              │
│                         P&L Analyzer                       │
│                              │                              │
│                    Forecasting  Anomaly Detection           │
│                              │                              │
│                        Reconciliation                       │
│                              │                              │
│                       Report Generator                      │
│                         /    |    \                         │
│               Notification  Audit  Dashboard Agent         │
│                                         │                   │
│                                    END (WebSocket push)     │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | LangGraph (state machine orchestration) |
| LLM | Claude API (Anthropic) — Sonnet for analysis, Opus for report generation |
| Backend | FastAPI (Python 3.11) |
| Frontend | React + TypeScript, Vite, Tailwind CSS |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Task Queue | Celery + Redis Beat |
| Real-time | WebSockets |
| Email | SendGrid |
| DevOps | Docker Compose |
| Charts | Recharts |

## The 10 Agents

| # | Agent | Role | LLM |
|---|-------|------|-----|
| 1 | **Orchestrator** | Brain — routes pipeline based on context | Sonnet |
| 2 | **Data Ingestion** | Parses CSV/JSON, normalises transactions, writes to DB | — |
| 3 | **P&L Analyzer** | Calculates revenue/expenses/profit, writes narrative | Sonnet |
| 4 | **Forecasting** | 30/60/90-day cash flow projection with confidence levels | Sonnet |
| 5 | **Anomaly Detection** | Z-score + IQR flagging, Claude explains each anomaly | Sonnet |
| 6 | **Reconciliation** | Cross-checks transactions, identifies mismatches | Sonnet |
| 7 | **Report Generator** | Compiles executive report + recommendations | **Opus** |
| 8 | **Notification** | Sends SendGrid email on report completion / critical anomaly | — |
| 9 | **Audit** | Logs every agent action and Claude API call to PostgreSQL | — |
| 10 | **Dashboard** | Pushes real-time updates to frontend via WebSocket | — |

## Running Locally

### Prerequisites
- Docker & Docker Compose
- An Anthropic API key
- (Optional) SendGrid API key for email alerts

### Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/Palenzo/FinAgent-OS.git
cd FinAgent-OS
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and (optionally) SENDGRID_API_KEY

# 2. Start everything
docker compose up --build

# 3. Open the dashboard
open http://localhost:5173

# 4. Trigger a pipeline run
# Upload a CSV via the dashboard, or hit the API directly:
curl -X POST http://localhost:8000/api/v1/run \
  -F "file=@your_transactions.csv" \
  -F "file_type=csv"
```

### CSV Format

The Data Ingestion agent expects:

```csv
date,description,amount,category
2024-01-15,Monthly SaaS Revenue,12000,revenue
2024-01-15,AWS Infrastructure,-1200,expense
2024-01-16,Staff Salaries,-8500,expense
```

- `date` — any parseable date format
- `amount` — positive = revenue, negative = expense
- `category` — optional (auto-inferred if missing)

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/run` | Upload file + trigger full pipeline |
| `GET` | `/api/v1/runs` | List all pipeline runs |
| `GET` | `/api/v1/reports` | List all generated reports |
| `GET` | `/api/v1/reports/{id}` | Get full report with markdown |
| `GET` | `/api/v1/audit/{run_id}` | Get audit trail for a run |
| `WS` | `/ws` | WebSocket — live agent events |
| `GET` | `/health` | Health check |

## Agent Coordination — How It Works

Each agent reads from and writes to a shared **LangGraph `FinAgentState`** TypedDict passed between nodes. This means:

- Every agent has full access to what every previous agent produced
- If an agent fails, the Orchestrator catches it via a conditional edge and routes to Audit → Notification
- The Report Generator only runs after P&L, Forecasting, Anomaly, and Reconciliation have all completed
- The Dashboard Agent broadcasts the final state snapshot to all connected frontend clients

**Failure handling:**
```
Data Ingestion fails
  → conditional edge routes to Audit (logs failure)
  → Audit → Notification (sends critical alert email)
  → END
```

## Cost Controls

- Claude responses are cached in Redis with a 1-hour TTL — identical data re-runs use cache
- Analysis agents use `claude-sonnet-4-6`; only the Report Generator uses `claude-opus-4-6`
- Every Claude API call's token count is logged to the Audit table for cost tracking
- Top 10 anomalies sent to Claude (not all flagged transactions)

## Project Structure

```
FinAgent-OS/
├── backend/
│   ├── agents/          # All 10 agent implementations
│   ├── graph/           # LangGraph state machine
│   ├── api/             # FastAPI endpoints
│   ├── db/              # PostgreSQL models + Redis client
│   ├── queue/           # Celery scheduled tasks
│   ├── tools/           # Claude API wrapper
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/  # AgentActivityFeed, PnLChart, AnomalyTable, etc.
│       ├── pages/       # Dashboard, Reports, Settings
│       └── hooks/       # useWebSocket
├── docker-compose.yml
└── .env.example
```

## License

MIT
