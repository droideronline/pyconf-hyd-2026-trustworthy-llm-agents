# Support Swarm — PyConf Hyd 2026

Multi-agent customer support system built with **LangGraph**, **LangChain**, and **PostgreSQL + pgvector**. Workshop demo for *"Observability, Evals & Security Guardrails for LLM Agents"*.

## Architecture

```
User Query
    │
    ▼
┌──────────┐
│  Router  │  ← structured output intent detection (ProviderStrategy)
└──────────┘
    │
    ├─ general ────────► ShopAssist        (lookup_order, process_refund, send_email, search_knowledge_base)
    ├─ order_support ──► ShopAssist
    ├─ policy_inquiry ─► PolicyAdvisor     (search_knowledge_base)
    └─ escalation ─────► EscalationAgent   (search_knowledge_base, send_email)
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker & Docker Compose
- Node.js 18+ and npm
- An OpenAI API key (or Azure OpenAI credentials)

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/droideronline/pyconf-hyd-2026-trustworthy-llm-agents.git
cd pyconf-hyd-2026-trustworthy-llm-agents
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```dotenv
OPENAI_API_KEY=sk-your-key-here
```

For Azure OpenAI, set `LLM_PROVIDER=azure_openai` and fill in the Azure fields.

### 3. Start PostgreSQL + pgvector

```bash
docker compose up -d
```

### 4. Seed the database

Create tables and insert sample data (customers, orders, knowledge articles):

```bash
uv run python -m support_swarm.db.seed
```

### 5. Generate embeddings for the knowledge base

This step requires your `OPENAI_API_KEY` to be set:

```bash
uv run python -m support_swarm.db.seed --embeddings
```

### 6. Start the backend (LangGraph dev server)

```bash
uv run langgraph dev --no-browser
```

The server starts at **http://localhost:2024**. Verify with:

```bash
curl http://localhost:2024/ok
# {"ok": true}
```

### 7. Start the frontend (Agent Chat UI)

In a new terminal:

```bash
cd agent-chat-ui
npm install
npm run dev
```

The UI opens at **http://localhost:3000**.

## Project Structure

```
├── support_swarm/
│   ├── config/              # Settings, YAML config loader
│   ├── db/
│   │   ├── models/          # SQLAlchemy ORM (Customer, Order, Refund, EmailLog, KnowledgeArticle)
│   │   ├── engine.py        # DB engine + session management
│   │   └── seed.py          # Seed data + embedding generation
│   ├── declarative/
│   │   ├── agents/          # YAML agent specs (router, shop_assist, policy_advisor, escalation_agent)
│   │   ├── models.py        # AgentSpec Pydantic model
│   │   └── yaml_utils.py    # YAML loader
│   ├── tools/
│   │   ├── registry.py      # Tool registry with @register_tool decorator
│   │   ├── shop_assist_tools.py  # lookup_order, process_refund, send_email
│   │   └── shared.py        # search_knowledge_base (pgvector semantic search)
│   ├── enums.py             # Agent name enums
│   ├── model_client.py      # LLM + embedding client factory
│   └── workflow.py          # LangGraph multi-agent workflow with structured routing
├── agent-chat-ui/           # LangChain Agent Chat UI (Next.js)
├── langgraph.json           # LangGraph dev server config
├── settings.yaml            # App config (env var driven)
├── docker-compose.yml       # PostgreSQL 16 + pgvector
└── pyproject.toml           # Python dependencies (managed by uv)
```

## Seed Data

| Table              | Records | Notes                                               |
| ------------------ | ------- | --------------------------------------------------- |
| customers          | 4       | Alice, Bob, Charlie, Eve                            |
| orders             | 7       | ORD-1001 to ORD-1007 (various statuses and amounts) |
| knowledge_articles | 5       | Return, Refund, Shipping, Warranty, Escalation      |

> **ORD-1006** contains a prompt injection payload in the `notes` field for the security guardrails demo.