"""
Pipeline Suggester — Entry Point

Sets up the ADK agent runner with the orchestrator agent,
loads environment variables, pseudonymizes pipeline data,
and runs the full analysis workflow.

Usage:
    python main.py                          # Uses sample_pipeline.csv
    python main.py --csv path/to/data.csv  # Uses a custom CSV file

The orchestrator delegates to 3 sub-agents:
  1. Pipeline Analyzer  — flags stagnant deals, computes risk scores
  2. Researcher          — gathers company context via MCP tools
  3. Action Suggester    — produces next-best-actions + draft emails

After the agents finish, the pseudonymized tokens in draft emails
are unmasked so the output contains real names and addresses.
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file (API keys, config).
# Must happen before any ADK imports that read GOOGLE_API_KEY.
load_dotenv()

from agents.orchestrator import orchestrator_agent
from agents.research_tools import set_reverse_mapping
from utils.anonymizer import Pseudonymizer


def check_env() -> None:
    """Validate that required environment variables are set.

    Exits with a helpful message if GOOGLE_API_KEY is missing,
    preventing a cryptic auth error later in the agent runner.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        print(
            "ERROR: GOOGLE_API_KEY not set.\n"
            "Copy .env.example to .env and add your key:\n"
            "  copy .env.example .env\n"
            "  Then edit .env with your actual API key from https://aistudio.google.com/apikey"
        )
        sys.exit(1)


async def run_pipeline(csv_path: str) -> None:
    """Main workflow: pseudonymize CSV → run agents → unmask results."""
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    import pandas as pd

    # -----------------------------------------------------------------
    # Step 0: Read CSV, pseudonymize sensitive fields
    # -----------------------------------------------------------------
    print(f"📂 Reading pipeline data from: {csv_path}")
    df = pd.read_csv(csv_path)

    pseudonymizer = Pseudonymizer()

    # Pseudonymize each row — this ensures no PII reaches the LLM.
    # Fields like Deal_ID, Deal_Value, Stage, etc. are safe and pass through.
    masked_rows = [
        pseudonymizer.pseudonymize_row(row.to_dict())
        for _, row in df.iterrows()
    ]

    # Build a text representation of the pseudonymized data.
    # In a more advanced version, this could be a structured JSON payload
    # or the agents could use MCP's read_pipeline_csv tool directly.
    headers = list(df.columns)
    lines = [" | ".join(headers), "-" * 60]
    for row in masked_rows:
        lines.append(" | ".join(str(row.get(h, "")) for h in headers))
    masked_csv_text = "\n".join(lines)

    print(
        f"🔒 Pseudonymized {len(masked_rows)} rows. "
        f"Tokens: {pseudonymizer.get_mapping_summary()}"
    )

    # -----------------------------------------------------------------
    # Step 0b: Pass the reverse mapping (token -> real value) to the
    # research tools so they can resolve [COMPANY_1] etc. back to
    # real company names for mock-DB lookups.
    #
    # SECURITY NOTE: The reverse mapping contains PII (real names,
    # emails). It must NEVER be sent to the LLM, logged persistently,
    # or included in any tool output. It is used solely as process-
    # local lookup keys within the research tools. The LLM context
    # only ever sees pseudonymized tokens.
    #
    # Also set REVERSE_MAP_JSON env var for the MCP server subprocess,
    # which needs it to resolve pseudonym tokens to real company names
    # for its search_company_info tool. The MCP server sanitizes output
    # back to tokens (see mcp_server/server.py).
    # -----------------------------------------------------------------
    reverse_map = pseudonymizer.get_reverse_mapping()
    set_reverse_mapping(reverse_map)
    os.environ["REVERSE_MAP_JSON"] = json.dumps(reverse_map)

    # -----------------------------------------------------------------
    # Step 1: Run the orchestrator agent (delegates to 3 sub-agents)
    # -----------------------------------------------------------------
    print("🚀 Starting Pipeline Suggester agent workflow...\n")

    runner = Runner(
        agent=orchestrator_agent,
        app_name="pipeline_suggester",
        session_service=InMemorySessionService(),
    )

    # Build the initial prompt with pseudonymized pipeline data.
    # The orchestrator's instruction tells it to sequentially delegate
    # to the three sub-agents (analyze → research → suggest).
    prompt = (
        "Here is the current CRM pipeline data (pseudonymized for privacy):\n\n"
        f"{masked_csv_text}\n\n"
        "Please analyze this pipeline, identify stagnant deals, "
        "research the companies, and suggest next-best-actions with "
        "draft outreach emails."
    )

    # Stream agent events for real-time feedback.
    # Each event may contain partial text from a sub-agent's response.
    final_response = ""
    async for event in runner.run_async(
        user_id="sales_user",
        session_id="pipeline_session_1",
        message=prompt,
    ):
        # ADK events have a .text attribute when they carry content
        if hasattr(event, "text") and event.text:
            print(event.text, end="", flush=True)
            final_response += event.text

    # -----------------------------------------------------------------
    # Step 2: Unmask pseudonymized tokens in the final output
    # -----------------------------------------------------------------
    print("\n\n🔓 Unmasking pseudonymized tokens in outreach emails...")
    unmasked_response = pseudonymizer.unmask(final_response)

    # -----------------------------------------------------------------
    # Step 3: Parse and display structured action plan
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL ACTION PLAN (unmasked, structured)")
    print("=" * 70)

    # Try to parse the response as JSON for structured display
    try:
        action_plan = json.loads(unmasked_response)
        _display_action_plan(action_plan)
    except json.JSONDecodeError:
        # Fallback: print raw response if not valid JSON
        print(unmasked_response)


def _display_action_plan(plan: dict) -> None:
    """Pretty-print the structured action plan."""
    if "actions" not in plan:
        print(plan)
        return

    summary = plan.get("summary", {})
    print(f"\n📊 PIPELINE SUMMARY")
    print(f"   Total flagged deals:  {summary.get('total_deals', 0)}")
    print(f"   CRITICAL:             {summary.get('critical_count', 0)}")
    print(f"   HIGH:                 {summary.get('high_count', 0)}")
    print(f"   MODERATE:             {summary.get('moderate_count', 0)}")
    print(f"   Value at risk:        ${summary.get('pipeline_value_at_risk', 0):,.0f}")

    print(f"\n🎯 RECOMMENDED ACTIONS ({len(plan['actions'])} deals)")
    print("-" * 70)

    for i, action in enumerate(plan["actions"], 1):
        deal_id = action.get("Deal_ID", "?")
        risk = action.get("Risk_Level", "?")
        company = action.get("Company", "?")
        score = action.get("Risk_Score", 0)
        next_action = action.get("Next_Best_Action", "No action specified")
        email = action.get("Draft_Email", "No email drafted")

        risk_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MODERATE": "🟡"}.get(risk, "⚪")

        print(f"\n{i}. {risk_emoji} {deal_id} — {company} ({risk}, Score: {score})")
        print(f"   📋 Next Best Action: {next_action}")
        print(f"   📧 Draft Email:")
        print(f"   " + "\n   ".join(email.split("\n")))


def main() -> None:
    """CLI entry point — parse args, validate env, run workflow."""
    parser = argparse.ArgumentParser(
        description="Pipeline Suggester — AI agent that identifies stagnant deals and suggests actions."
    )
    parser.add_argument(
        "--csv",
        default="data/sample_pipeline.csv",
        help="Path to the CRM pipeline CSV file (default: data/sample_pipeline.csv)",
    )
    args = parser.parse_args()

    # Validate API key before doing any real work
    check_env()

    # Read stagnant-day threshold from env (default: 14 days).
    # The Pipeline Analyzer agent references this in its instructions.
    stagnant_days = int(os.getenv("STAGNANT_DAYS_THRESHOLD", "14"))
    print(f"⚙️  Stagnant threshold: {stagnant_days} days")
    os.environ["STAGNANT_DAYS_THRESHOLD"] = str(stagnant_days)

    asyncio.run(run_pipeline(args.csv))


if __name__ == "__main__":
    main()
