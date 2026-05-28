"""
ReAct agent (no framework) — Benuron / paracetamol dosage calculator.

Follows the Thought → Action → PAUSE → Observation loop from the
agent-from-scratch notebook, adapted for pediatric paracetamol dosing.
"""

import re
from openai import OpenAI
from tools import known_actions

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a pediatric fever medication calculator.

You help parents and caregivers understand the correct dose of paracetamol (Benuron)
or ibuprofen (Brufen/Nurofen) for their child based on age and product concentration.

⚠️  IMPORTANT DISCLAIMER ⚠️
You are an educational tool only. You must NOT provide medical advice.
Always recommend that users confirm dosing with a doctor or pharmacist.
Never recommend ibuprofen for children under 3 months or under 5 kg.
Never recommend any medication for infants under 1 month without medical supervision.

You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer.

Use Thought to describe your reasoning about the question you have been asked.
Use Action to run one of the actions available to you — then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

get_child_weight:
  e.g. get_child_weight: 18 months
  Returns estimated weight for a child of that age based on WHO growth charts.
  Also accepts: "2 years", "6 meses", "3 anos".

get_product_concentration:
  e.g. get_product_concentration: Benuron 40mg/ml
  Returns the concentration in mg/mL for a named product.
  Also accepts: "Brufen", "Nurofen", "syrup", "xarope", "20mg/ml", etc.

paracetamol_calculator:
  e.g. paracetamol_calculator: 11.0, 40
  Calculates the paracetamol (Benuron) dose in mL.
  Arguments: weight in kg, concentration in mg/mL (comma-separated).
  Standard dose: 15 mg/kg, every 6–8 h, max 4×/day.

ibuprofen_calculator:
  e.g. ibuprofen_calculator: 11.0, 20
  Calculates the ibuprofen (Brufen/Nurofen) dose in mL.
  Arguments: weight in kg, concentration in mg/mL (comma-separated).
  Standard dose: 10 mg/kg, every 6–8 h, max 3×/day. NOT for under 3 months / under 5 kg.
  Most common children's suspension: 20 mg/mL.

Example session — paracetamol:

Question: My son is 18 months old. I have Benuron 40mg/ml. How much do I give?
Thought: I need the child's estimated weight, then compute the paracetamol dose.
Action: get_child_weight: 18 months
PAUSE

Observation: Estimated weight for a child of 18 months: 11.0 kg ...

Thought: Weight ~11 kg, concentration 40 mg/mL. I'll run paracetamol_calculator.
Action: paracetamol_calculator: 11.0, 40
PAUSE

Observation: Paracetamol dose: 165.0 mg → 4.1 mL of 40 mg/mL ...

Answer: For an 18-month-old (~11 kg) using Benuron 40 mg/mL, give approximately 4.1 mL
per dose, every 6–8 hours (up to 4 times per day). ⚠️ Always confirm with your doctor or
pharmacist before administering medication.

Example session — ibuprofen:

Question: My daughter is 3 years old. I have Brufen suspension 20mg/ml. What dose?
Thought: I need the child's estimated weight, then compute the ibuprofen dose.
Action: get_child_weight: 3 years
PAUSE

Observation: Estimated weight for a child of 36 months: 14.0 kg ...

Thought: Weight ~14 kg, concentration 20 mg/mL. I'll run ibuprofen_calculator.
Action: ibuprofen_calculator: 14.0, 20
PAUSE

Observation: Ibuprofen dose: 140.0 mg → 7.0 mL of 20 mg/mL ...

Answer: For a 3-year-old (~14 kg) using Brufen 20 mg/mL, give approximately 7.0 mL
per dose, every 6–8 hours (up to 3 times per day). ⚠️ Do not give on an empty stomach.
Always confirm with your doctor or pharmacist.
""".strip()

# ---------------------------------------------------------------------------
# Agent class (identical pattern to the notebook)
# ---------------------------------------------------------------------------

_action_re = re.compile(r"^Action: (\w+): (.*)$")


class Agent:
    def __init__(self, client: OpenAI, system: str = SYSTEM_PROMPT):
        self.client = client
        self.messages: list[dict] = [{"role": "system", "content": system}]

    def __call__(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        result = self._execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def _execute(self) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=self.messages,
        )
        return completion.choices[0].message.content


# ---------------------------------------------------------------------------
# ReAct loop
# ---------------------------------------------------------------------------

def run_agent(question: str, client: OpenAI, max_turns: int = 8) -> dict:
    """
    Runs the full ReAct loop for a user question.

    Returns a dict with:
      - answer: final answer string
      - steps: list of intermediate steps (for transparency)
    """
    bot = Agent(client)
    next_prompt = question
    steps: list[dict] = []

    for _ in range(max_turns):
        result = bot(next_prompt)
        steps.append({"role": "assistant", "content": result})

        # Check for an action
        action_matches = [
            _action_re.match(line)
            for line in result.splitlines()
            if _action_re.match(line)
        ]

        if action_matches:
            action_name, action_input = action_matches[0].groups()

            if action_name not in known_actions:
                observation = f"Unknown action '{action_name}'. Available: {list(known_actions.keys())}"
            else:
                observation = known_actions[action_name](action_input)

            steps.append({"role": "tool", "action": action_name, "observation": observation})
            next_prompt = f"Observation: {observation}"

        else:
            # No action → the agent has produced a final Answer
            # Strip the "Answer: " prefix if present
            answer = result
            if answer.startswith("Answer:"):
                answer = answer[len("Answer:"):].strip()
            return {"answer": answer, "steps": steps}

    # If we exhaust max_turns, return whatever the last message was
    return {
        "answer": "Could not compute a complete answer within the allowed steps.",
        "steps": steps,
    }
