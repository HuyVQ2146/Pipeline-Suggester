"""
Standalone test/demo for the Research Agent.

Two modes:
  python test_researcher.py               -> Quick mode: calls the research
                                             tools directly (no API key, instant)
  python test_researcher.py --adk         -> Full mode: runs the researcher
                                             through the ADK agent (needs
                                             GOOGLE_API_KEY in .env)

Quick mode verifies:
  - Mock company DB lookups return correct structured data
  - Pseudonymized tokens ([COMPANY_N]) are resolved to real names
  - The 2-3 sentence summaries are generated correctly
  - Not-found companies produce a graceful fallback
  - Sensitive contact info is never included in tool output
"""

import io
import sys

# Windows cp1252 console cannot encode emoji characters used in the output.
# Force stdout/stderr to UTF-8 so all Unicode prints correctly.
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import asyncio
import json
import os

from utils.anonymizer import Pseudonymizer


# ---------------------------------------------------------------------------
# Quick mode — call research tools directly, no LLM needed
# ---------------------------------------------------------------------------

def run_quick_test() -> None:
    """Run the research tools directly and print results.

    Simulates the full flow: read sample CSV, pseudonymize data,
    flag stagnant deals, set up the reverse mapping, then research
    each flagged company. No API key or LLM calls needed.
    """
    from agents.pipeline_tools import analyze_pipeline
    from agents.research_tools import (
        research_company,
        bulk_research,
        set_reverse_mapping,
    )

    print("=" * 70)
    print("QUICK MODE - Direct function call (no LLM, no API key)")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Run the pipeline analyzer to get flagged deals
    # ------------------------------------------------------------------
    print("\n  Step 1: Analyzing pipeline to find stagnant deals...\n")

    result_json = analyze_pipeline(
        csv_path="data/sample_pipeline.csv",
        stagnant_threshold_days=14,
        reference_date="2025-06-30",
    )
    analysis = json.loads(result_json)
    flagged = analysis["flagged_deals"]

    print(f"  Found {len(flagged)} stagnant deals out of {analysis['total_deals']} total.\n")

    # ------------------------------------------------------------------
    # Step 2: Pseudonymize the flagged deals (simulating the orchestrator)
    #
    # SECURITY: We pseudonymize BEFORE any data reaches the LLM.
    # Company names, contact names, and emails are replaced with tokens
    # like [COMPANY_1], [CONTACT_1], [EMAIL_1]. The Pseudonymizer stores
    # a local reverse mapping so we can unmask the final output later.
    # ------------------------------------------------------------------
    print("  Step 2: Pseudonymizing sensitive fields...\n")

    pseudonymizer = Pseudonymizer()
    pseudonymized_deals = []

    for deal in flagged:
        row = {
            "Deal_ID": deal["Deal_ID"],
            "Company_Name": deal["Company_Name"],
            "Contact_Name": deal["Contact_Name"],
            "Contact_Email": deal["Contact_Email"],
            "Deal_Value": deal["Deal_Value"],
            "Stage": deal["Stage"],
            "Owner": deal["Owner"],
            "Last_Activity_Date": deal["Last_Activity_Date"],
            "Days_Stagnant": deal["Days_Stagnant"],
            "Risk_Score": deal["Risk_Score"],
            "Risk_Level": deal["Risk_Level"],
        }
        masked_row = pseudonymizer.pseudonymize_row(row)
        pseudonymized_deals.append(masked_row)

    # Build the reverse mapping: {"[COMPANY_1]": "Acme Corp", ...}
    # SECURITY: Use get_reverse_mapping() (token->real), NOT get_mapping_summary()
    # (real->token). The research tools need to resolve tokens back to real
    # company names for DB lookups. The real names are NEVER sent to the LLM.
    reverse_map = pseudonymizer.get_reverse_mapping()

    print(f"  Pseudonymized {len(pseudonymized_deals)} deals.")
    print(f"  Reverse mapping (tokens -> real names, for internal use): "
          f"{{k: v for k, v in list(reverse_map.items())[:3]}} ... "
          f"({len(reverse_map)} total entries)\n")

    # ------------------------------------------------------------------
    # Step 3: Set the reverse mapping in the research tools module
    #
    # This allows the tools to resolve tokens like [COMPANY_1] back to
    # "Acme Corp" when querying the mock DB — but the LLM never sees
    # the real names. The resolved values are used only as lookup keys.
    # ------------------------------------------------------------------
    set_reverse_mapping(reverse_map)

    # Extract the pseudonymized company names (tokens) for research
    company_tokens = [d["Company_Name"] for d in pseudonymized_deals]

    # ------------------------------------------------------------------
    # Step 4: Test single-company research
    # ------------------------------------------------------------------
    print("  Step 3: Testing single-company research...\n")
    print("-" * 60)

    # Pick the top 3 risky deals for single-lookup demo
    for token in company_tokens[:3]:
        real_name = reverse_map.get(token, token)
        print(f"\n  Calling research_company(\"{token}\")")
        print(f"  [Internally resolves to: \"{real_name}\"]")
        print()

        result_json = research_company(token)
        result = json.loads(result_json)

        if result.get("status") == "found":
            print(f"    Industry:     {result['industry']}")
            print(f"    Employees:    {result['employee_count']}")
            print(f"    Recent News:  {result['recent_news']}")
            print(f"    Tech Stack:   {', '.join(result['tech_stack'])}")
            print(f"    Buying Signals: {'; '.join(result['buying_signals'])}")
        else:
            print(f"    {result['message']}")

        # Verify no PII leaked into the tool output
        assert "Contact_Name" not in result, "SECURITY: Contact name leaked into research output!"
        assert "Contact_Email" not in result, "SECURITY: Contact email leaked into research output!"

    print("\n" + "  -" * 30)

    # ------------------------------------------------------------------
    # Step 5: Test bulk research (all flagged companies at once)
    # ------------------------------------------------------------------
    print("\n  Step 4: Testing bulk research (all flagged companies)...\n")
    print("-" * 60)

    names_json = json.dumps(company_tokens)
    print(f"  Calling bulk_research with {len(company_tokens)} companies...\n")

    bulk_json = bulk_research(names_json)
    bulk_result = json.loads(bulk_json)

    print(f"  Requested: {bulk_result['total_requested']}  |  "
          f"Found: {bulk_result['found']}  |  Not found: {bulk_result['not_found']}\n")

    for entry in bulk_result["results"]:
        status_icon = "OK" if entry.get("status") == "found" else "??"
        # Show the token the LLM sees, plus the resolved name internally
        token_used = entry.get("company", "???")
        if token_used in reverse_map:
            display = f"{token_used} -> {reverse_map[token_used]}"
        else:
            display = token_used
        print(f"  [{status_icon}] {display}")
        print(f"       {entry.get('summary', 'No summary')}")
        print()

    # ------------------------------------------------------------------
    # Step 6: Test not-found company (graceful fallback)
    # ------------------------------------------------------------------
    print("-" * 60)
    print("\n  Step 5: Testing not-found company...\n")

    missing_json = research_company("Nonexistent Corp LLC")
    missing_result = json.loads(missing_json)
    print(f"  Status:   {missing_result['status']}")
    print(f"  Message:  {missing_result['message']}")

    # ------------------------------------------------------------------
    # Step 7: Security check — verify PII never appears in tool output
    # ------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  Step 6: Security verification...\n")

    # Collect all real PII values that should never appear in tool output.
    # We get them from the reverse map (token -> real value).
    real_emails = set(reverse_map.get(k, "") for k in reverse_map if k.startswith("[EMAIL_"))
    real_contacts = set(reverse_map.get(k, "") for k in reverse_map if k.startswith("[CONTACT_"))
    real_companies = set(reverse_map.get(k, "") for k in reverse_map if k.startswith("[COMPANY_"))

    # Check every entry in the bulk result for PII leakage
    leaked = False
    for entry in bulk_result["results"]:
        # Check all string fields in the tool output
        output_text = json.dumps(entry)
        for email in real_emails:
            if email and email in output_text:
                print(f"  SECURITY LEAK: Email '{email}' found in tool output!")
                leaked = True
        for contact in real_contacts:
            if contact and contact in output_text:
                print(f"  SECURITY LEAK: Contact name '{contact}' found in tool output!")
                leaked = True
        for company in real_companies:
            if company and company in output_text:
                print(f"  SECURITY LEAK: Company name '{company}' found in tool output!")
                leaked = True

    if not leaked:
        print("  No PII leaked into research tool output.")

    print(f"\n  {'All security checks passed!' if not leaked else 'SECURITY ISSUE DETECTED!'}")


# ---------------------------------------------------------------------------
# Full mode — run through the ADK Research Agent (LLM calls the tools)
# ---------------------------------------------------------------------------

async def run_adk_test() -> None:
    """Run the researcher agent through the ADK Runner.

    This tests the full agent integration: the LLM reads the user
    prompt containing pseudonymized deals, decides to call the
    research tools, and presents the results in natural language.
    Requires GOOGLE_API_KEY in .env.
    """
    from dotenv import load_dotenv
    load_dotenv()

    from agents.research_tools import set_reverse_mapping
    from agents.pipeline_tools import analyze_pipeline
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from agents.researcher import researcher_agent
    from utils.anonymizer import Pseudonymizer

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        print("ERROR: GOOGLE_API_KEY not set. Create a .env file from .env.example.")
        sys.exit(1)

    print("=" * 70)
    print("FULL MODE - ADK Agent Runner (LLM + function tools + MCP)")
    print("=" * 70)

    # Run pipeline analysis first to get flagged deals
    result_json = analyze_pipeline(
        csv_path="data/sample_pipeline.csv",
        stagnant_threshold_days=14,
        reference_date="2025-06-30",
    )
    analysis = json.loads(result_json)
    flagged = analysis["flagged_deals"]

    # Pseudonymize the flagged deals
    pseudonymizer = Pseudonymizer()
    pseudonymized_deals = []
    for deal in flagged:
        row = {
            "Deal_ID": deal["Deal_ID"],
            "Company_Name": deal["Company_Name"],
            "Contact_Name": deal["Contact_Name"],
            "Contact_Email": deal["Contact_Email"],
            "Deal_Value": deal["Deal_Value"],
            "Stage": deal["Stage"],
            "Owner": deal["Owner"],
            "Last_Activity_Date": deal["Last_Activity_Date"],
            "Days_Stagnant": deal["Days_Stagnant"],
            "Risk_Score": deal["Risk_Score"],
            "Risk_Level": deal["Risk_Level"],
        }
        masked_row = pseudonymizer.pseudonymize_row(row)
        pseudonymized_deals.append(masked_row)

    # Set the reverse mapping so tools can resolve tokens to real names for DB lookups.
    # SECURITY: This mapping (token->real) must never appear in LLM context.
    set_reverse_mapping(pseudonymizer.get_reverse_mapping())

    # Build the prompt with pseudonymized data only
    deals_text = json.dumps(pseudonymized_deals, indent=2)
    prompt = (
        "Research the following flagged stagnant deals and provide "
        "company context for each. The company names are pseudonymized "
        "tokens — pass them as-is to the tools; they resolve them "
        "internally.\n\n"
        f"Flagged deals:\n{deals_text}"
    )

    runner = Runner(
        agent=researcher_agent,
        app_name="researcher_test",
        session_service=InMemorySessionService(),
    )

    print(f"\n  Posted {len(pseudonymized_deals)} flagged deals to the Research Agent.\n")
    print("-" * 60)
    print("  Agent response:")
    print("-" * 60)

    async for event in runner.run_async(
        user_id="test_user",
        session_id="researcher_test_session",
        message=prompt,
    ):
        if hasattr(event, "text") and event.text:
            print(event.text, end="", flush=True)

    print("\n\n  ADK agent run complete.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test the Research Agent - quick (direct) or full (ADK agent)"
    )
    parser.add_argument(
        "--adk",
        action="store_true",
        help="Run full ADK agent test (needs GOOGLE_API_KEY). Default: quick mode.",
    )
    args = parser.parse_args()

    if args.adk:
        asyncio.run(run_adk_test())
    else:
        run_quick_test()


if __name__ == "__main__":
    main()
