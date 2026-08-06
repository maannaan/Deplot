# Deplot AI

Autonomous Platform Engineer for the [Zerops Challenge](https://www.wemakedevs.org/hackathons/zerops#register).

**Platform Engineering → Observability → AIOps**

## Structure (extensible)

```
deplot/
├── backend/app/
│   ├── agents/          # BaseAgent + @register_agent — add agents without touching orchestrator
│   ├── api/v1/          # One router per domain — add routes as new modules
│   ├── core/registry.py # Service + agent plugin registry
│   ├── models/          # Pydantic schemas per domain
│   ├── services/        # Domain services (swap store → DB later)
│   └── bootstrap.py     # Wire everything at startup
├── frontend/src/
│   ├── config/wizard-steps.ts  # Add wizard steps without UI restructure
│   └── lib/api.ts
├── prompts/             # Agent system prompts (editable without code changes)
├── templates/zerops/    # Stack templates for yaml generation
├── zerops/              # Deplot's own Zerops Import YAML
└── docs/
```

## Quick start

### 1. Environment

```bash
cp deplot/.env.example deplot/.env
# Fill GEMINI_API_KEY, ZEROPS_API_TOKEN
```

### 2. Local data services

```bash
docker compose -f deplot/docker/docker-compose.yml up -d
```

### 3. Backend

```bash
cd deplot/backend
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd deplot/frontend
npm install
npm run dev
```

Open http://localhost:3000

## Day 0 checklist

See [docs/day0-zerops.md](deplot/docs/day0-zerops.md)

## Adding a new agent

1. Create prompt in `prompts/my_agent.md`
2. Subclass `BaseAgent` in `app/agents/implementations.py`
3. Decorate with `@register_agent`
4. Call via `AgentOrchestrator.run("my_agent", context)`

## Adding a new service

1. Subclass `BaseService` in `app/services/`
2. Register in `bootstrap.py`
3. Add route module in `app/api/v1/`
