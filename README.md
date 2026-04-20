# Benuron / Ibuprofen Dose Calculator Agent

Educational pediatric fever medication calculator built as a FastAPI service using a hand-rolled ReAct agent (no framework). Inspired by the `agent-from-scratch` notebook in this repo.

> **Disclaimer:** This tool is for educational purposes only. Always confirm dosing with a doctor or pharmacist before administering medication to a child.

## How it works

The agent follows the **ReAct** loop (Thought → Action → PAUSE → Observation) driven by an LLM:

```
User question
  └─ Thought: reason about what to do
  └─ Action: get_child_weight / paracetamol_calculator / ibuprofen_calculator
  └─ PAUSE
  └─ Observation: tool result fed back
  └─ ... repeat until ...
  └─ Answer
```

Tools are plain Python functions — no LangChain, no LangGraph.

## Project structure

```
.
├── main.py          # FastAPI app + X-API-Key auth
├── agent.py         # ReAct loop
├── tools.py         # get_child_weight, paracetamol_calculator, ibuprofen_calculator
├── pyproject.toml   # dependencies (managed by uv)
├── uv.lock
├── Dockerfile
├── .env.example
└── .dockerignore
```

## Setup

### Prerequisites

- [uv](https://github.com/astral-sh/uv) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An OpenAI API key

### Local

```bash
cp .env.example .env
# edit .env and fill in OPENAI_API_KEY and APP_API_KEY

uv sync
uv run uvicorn main:app --reload
```

Server starts at `http://127.0.0.1:8000`.

### Docker

```bash
docker build -t benuron-agent .

docker run -p 8000:8000 --env-file .env benuron-agent
```

## Environment variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `APP_API_KEY` | Secret passed in the `X-API-Key` request header |

## API

### `GET /health`

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

### `POST /ask`

Requires `X-API-Key` header.

**Paracetamol (Benuron):**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "My son is 18 months old. I have Benuron 40mg/ml. How much do I give?"}'
```

**Ibuprofen (Brufen/Nurofen):**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "My daughter is 3 years old. I have Brufen 20mg/ml. What dose?"}'
```

**Portuguese input works too:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "Bebe de 6 meses, xarope benuron 40mg/ml, qual a dose?"}'
```

**Response shape:**
```json
{
  "answer": "For an 18-month-old (~11 kg) using Benuron 40 mg/mL, give approximately 4.1 mL per dose...",
  "steps": [
    {"role": "assistant", "content": "Thought: ...\nAction: get_child_weight: 18 months\nPAUSE"},
    {"role": "tool", "action": "get_child_weight", "observation": "Estimated weight: 11.0 kg ..."},
    {"role": "assistant", "content": "Thought: ...\nAction: paracetamol_calculator: 11.0, 40\nPAUSE"},
    {"role": "tool", "action": "paracetamol_calculator", "observation": "Dose: 165.0 mg → 4.1 mL ..."},
    {"role": "assistant", "content": "Answer: ..."}
  ],
  "disclaimer": "⚠️  This is an educational tool only..."
}
```

Interactive docs available at `http://127.0.0.1:8000/docs`.

## Dosing reference

| Drug | Dose | Interval | Max doses/day | Single-dose cap |
|---|---|---|---|---|
| Paracetamol | 15 mg/kg | every 6–8 h | 4 | 1000 mg |
| Ibuprofen | 10 mg/kg | every 6–8 h | 3 | 400 mg |

Ibuprofen is **not recommended** for children under 3 months or under 5 kg.
