"""
FastAPI server — Benuron / paracetamol educational dose calculator.

Authentication: X-API-Key header (value set in .env as APP_API_KEY).

Endpoints:
  GET  /health         — liveness check
  POST /ask            — run the ReAct agent with a natural-language question
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from openai import OpenAI
from pydantic import BaseModel, Field

from agent import run_agent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in .env")
if not APP_API_KEY:
    raise RuntimeError("APP_API_KEY is not set in .env")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Benuron Dose Calculator",
    description=(
        "Educational tool that calculates paracetamol (Benuron) doses for children "
        "based on age and product concentration. NOT a substitute for medical advice."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    if not api_key or api_key != APP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide it in the X-API-Key header.",
        )
    return api_key


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        examples=[
            "My daughter is 2 years old. I have Benuron 40mg/ml. How much should I give her?",
            "Baby 6 meses, xarope benuron 40mg/ml, qual a dose?",
        ],
    )
    max_turns: int = Field(default=8, ge=1, le=15)


class StepDetail(BaseModel):
    role: str
    content: str | None = None
    action: str | None = None
    observation: str | None = None


class AskResponse(BaseModel):
    answer: str
    steps: list[StepDetail]
    disclaimer: str = (
        "⚠️  This is an educational tool only and does NOT constitute medical advice. "
        "Always consult a doctor or pharmacist before administering medication to a child."
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse, tags=["agent"])
def ask(body: AskRequest, _: str = Security(require_api_key)):
    """
    Submit a natural-language question to the Benuron ReAct agent.

    The agent will reason through the problem using:
    - `get_child_weight` — WHO-based weight estimate by age
    - `get_product_concentration` — mg/mL lookup for Benuron products
    - `calculate_dose` — final mL calculation with safety notes

    Requires `X-API-Key` header.
    """
    result = run_agent(
        question=body.question,
        client=openai_client,
        max_turns=body.max_turns,
    )
    return AskResponse(
        answer=result["answer"],
        steps=[StepDetail(**s) for s in result["steps"]],
    )
