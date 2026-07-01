"""
Orchestrator Agent — Root agent that coordinates the 3 sub-agents.

Data flow:
  1. Receive the user's request (with pseudonymized pipeline data)
  2. Delegate to pipeline_analyzer  → get flagged deals + risk scores
  3. Delegate to researcher          → get company context for each
  4. Delegate to action_suggester    → get next-best-actions + draft emails
  5. Return the full action plan to the user

The orchestrator uses ADK's built-in sub-agent delegation: sub-agents
are registered on the parent agent, and the LLM autonomously delegates
to them based on its instructions. Each sub-agent's output is added to
the conversation context so the next sub-agent can build on it.

Security: The orchestrator pseudonymizes all pipeline data BEFORE any
agent sees it (done in main.py). After the Action Suggester returns
draft emails, main.py unmasks them using the Pseudonymizer's reverse map.
"""

from google.adk import Agent

from agents.pipeline_analyzer import pipeline_analyzer_agent
from agents.researcher import researcher_agent
from agents.action_suggester import action_suggester_agent

orchestrator_agent = Agent(
    name="pipeline_orchestrator",
    model="gemini-2.0-flash",
    description=(
        "Orchestrates the pipeline analysis workflow: analyze → research → "
        "suggest actions. Delegates to three sub-agents in sequence."
    ),
    instruction="""You are the Pipeline Suggester Orchestrator. You coordinate
three specialist sub-agents to help a sales team re-engage stagnant deals.

Workflow — follow this exact order:

Step 1 — ANALYZE: Delegate to the pipeline_analyzer sub-agent.
  Pass the pseudonymized pipeline CSV data and ask it to flag
  stagnant deals and compute risk scores.

Step 2 — RESEARCH: Delegate to the researcher sub-agent.
  Pass the flagged deals from Step 1 and ask it to look up company
  context for each flagged account using the search_company_info tool.

Step 3 — SUGGEST: Delegate to the action_suggester sub-agent.
  Pass both the flagged deals (Step 1) and the company research
  (Step 2). Ask it to produce next-best-actions and draft outreach
  emails for each stagnant deal.

Step 4 — SUMMARIZE: Combine all outputs into a final, clean
  action plan. Present the results deal-by-deal, sorted by risk
  score (highest first). Include the draft emails verbatim.

Important:
- Do NOT skip steps or change the order.
- Pass ALL relevant context forward between steps — do not drop data.
- Keep the pseudonymized names ([COMPANY_N], [CONTACT_N], [EMAIL_N])
  intact in draft emails. The system will replace them with real values.
- If a sub-agent returns partial results, proceed with what you have.
""",
    sub_agents=[
        pipeline_analyzer_agent,
        researcher_agent,
        action_suggester_agent,
    ],
)
