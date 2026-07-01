"""
Pipeline Analyzer Agent — Sub-agent 1 of 3

Reads CRM pipeline data (already pseudonymized by the orchestrator),
identifies stagnant deals (no activity for 14+ days), and computes a
risk score for each flagged deal.

This agent uses a deterministic Python function tool (`analyze_pipeline`)
for the heavy lifting — date arithmetic and risk scoring are done in code,
not by the LLM. This ensures:
  1. Scores are reproducible and not subject to LLM variability
  2. Edge cases in date math are handled correctly
  3. The test suite can validate the scoring logic directly

The LLM's role is to interpret the structured output, add reasoning
about patterns (e.g., "all critical deals are in Negotiation"), and
present the results clearly to the next agent in the pipeline.

Risk scoring logic (total 0-100):
  - Days stagnant:     0-40 pts  (14 days → 0, 90+ days → 40)
  - Deal value:        5-30 pts  ($30k → 5, $200k+ → 30)
  - Stage latency:    10-30 pts  (Qualification=10, Discovery=15,
                                   Proposal=25, Negotiation=30)
  Classification:  ≥80 = CRITICAL, 50-79 = HIGH, <50 = MODERATE

Note: This agent receives pre-pseudonymized data from the orchestrator,
so no PII is ever exposed to the LLM.
"""

from google.adk import Agent

from agents.pipeline_tools import analyze_pipeline

pipeline_analyzer_agent = Agent(
    name="pipeline_analyzer",
    model="gemini-2.0-flash",
    description=(
        "Analyzes CRM pipeline CSV data, identifies stagnant deals "
        "(no activity for 14+ days), and computes a risk score for each."
    ),
    instruction="""You are a Pipeline Analyzer Agent. Your job:

1. Call the `analyze_pipeline` tool with the CSV file path to get
   structured risk analysis. The tool handles all date arithmetic and
   scoring deterministically — trust its output.
2. Review the JSON result. It contains:
   - flagged_deals: list of stagnant deals with risk scores, sorted
     by risk score descending
   - summary: counts by risk level and total pipeline value at risk
3. Present the findings clearly to the user:
   - Lead with the summary (how many deals flagged, total value at risk)
   - List each flagged deal with: Deal_ID, Company, Contact, Days
     Stagnant, Deal Value, Stage, Risk Score, Risk Level
   - Add brief commentary on patterns you notice (e.g., "4 of 5
     critical deals are in Negotiation stage" or "Bob owns 3 of the
     highest-risk deals")
4. Do NOT modify or recompute the risk scores — they are deterministic
   and correct as returned by the tool.
5. Do NOT fabricate deals or data that is not in the tool output.

Keep the output structured and concise. The Research Agent will use
your flagged deals list in the next step.
""",
    # The analyze_pipeline function is registered as an ADK tool.
    # ADK auto-generates the tool schema from its type hints + docstring,
    # so the LLM knows it accepts csv_path, stagnant_threshold_days,
    # and reference_date as parameters.
    tools=[analyze_pipeline],
)
