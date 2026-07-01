"""
Standalone test/demo for the Pipeline Analyzer.

Two modes:
  python test_analyzer.py               → Quick mode: runs the Python
                                           analysis functions directly
                                           (no API key needed, instant)
  python test_analyzer.py --adk         → Full mode: runs the pipeline
                                           analyzer through the ADK agent
                                           (needs GOOGLE_API_KEY in .env)

Quick mode is for development iteration — verify scoring logic,
check CSV parsing, and debug the output format without any LLM costs.
Full mode is for integration testing — confirms the ADK agent correctly
calls the tool and presents the results.
"""

import io
import sys

# ---------------------------------------------------------------------------
# Windows cp1252 console cannot encode emoji characters used in the output.
# Force stdout/stderr to UTF-8 so all Unicode (emoji, symbols) print
# correctly on any terminal. Safe on all platforms — UTF-8 is a superset.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import asyncio
import json
import os
import sys

# ---------------------------------------------------------------------------
# Quick mode — call analyze_pipeline() directly, no LLM needed
# ---------------------------------------------------------------------------

def run_quick_test(csv_path: str, reference_date: str) -> None:
    """Run the pipeline analysis functions directly and print results.

    This tests the deterministic scoring logic without needing an API key
    or any LLM calls. Useful for verifying the CSV is parsed correctly
    and the risk scoring math is right.
    """
    from agents.pipeline_tools import analyze_pipeline, _compute_risk_score

    print("=" * 70)
    print("QUICK MODE — Direct function call (no LLM, no API key)")
    print("=" * 70)

    # Run the full pipeline analysis
    print(f"\n📂 Analyzing: {csv_path}")
    print(f"📅 Reference date: {reference_date or 'today'}")
    print(f"⏱  Stagnant threshold: 14 days\n")

    result_json = analyze_pipeline(
        csv_path=csv_path,
        stagnant_threshold_days=14,
        reference_date=reference_date,
    )
    result = json.loads(result_json)

    # --- Print summary ---
    summary = result["summary"]
    print("─" * 50)
    print("📊  SUMMARY")
    print("─" * 50)
    print(f"   Total deals in pipeline:  {result['total_deals']}")
    print(f"   Flagged as stagnant:      {summary['flagged_count']}")
    print(f"     ├─ CRITICAL (≥80):      {summary['critical']}")
    print(f"     ├─ HIGH (50-79):        {summary['high']}")
    print(f"     └─ MODERATE (<50):      {summary['moderate']}")
    print(f"   Pipeline value at risk:   ${summary['total_pipeline_value_at_risk']:,.0f}")
    print()

    # --- Print each flagged deal ---
    print("─" * 50)
    print("🚨  FLAGGED DEALS (sorted by risk score, highest first)")
    print("─" * 50)
    deals = result["flagged_deals"]
    if not deals:
        print("   No stagnant deals found — pipeline looks healthy! ✅")
    else:
        for i, deal in enumerate(deals, 1):
            # Use an emoji indicator for risk level at a glance
            level_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MODERATE": "🟡"}[
                deal["Risk_Level"]
            ]
            print(f"\n  {i}. {level_icon} {deal['Deal_ID']} — {deal['Company_Name']}")
            print(f"     Contact:  {deal['Contact_Name']} <{deal['Contact_Email']}>")
            print(f"     Stage:    {deal['Stage']}")
            print(f"     Value:    ${deal['Deal_Value']:,.0f}")
            print(f"     Idle:     {deal['Days_Stagnant']} days (since {deal['Last_Activity_Date']})")
            print(f"     Owner:    {deal['Owner']}")
            print(f"     Risk:     {deal['Risk_Score']}/100 → {deal['Risk_Level']}")

    # --- Unit test the scoring function directly ---
    print("\n")
    print("─" * 50)
    print("🧪  SCORING SANITY CHECKS")
    print("─" * 50)
    test_cases = [
        # (days_stagnant, deal_value, stage, expected_range)
        (15, 30_000, "Qualification", "MODERATE"),
        (45, 100_000, "Proposal", "HIGH"),
        (91, 250_000, "Negotiation", "CRITICAL"),
    ]
    all_pass = True
    for days, value, stage, expected_level in test_cases:
        score, level = _compute_risk_score(days, value, stage)
        status = "✅" if level == expected_level else "❌"
        if level != expected_level:
            all_pass = False
        print(
            f"  {status}  {days}d stagnant, ${value:,}, {stage} → "
            f"score={score}, level={level} (expected {expected_level})"
        )

    print(f"\n{'All sanity checks passed! ✅' if all_pass else 'Some checks failed ❌'}")


# ---------------------------------------------------------------------------
# Full mode — run through the ADK agent (LLM calls the tool)
# ---------------------------------------------------------------------------

async def run_adk_test(csv_path: str, reference_date: str) -> None:
    """Run the pipeline_analyzer agent through the ADK Runner.

    This tests the full agent integration: the LLM reads the user
    prompt, decides to call the analyze_pipeline tool, and presents
    the results in natural language. Requires GOOGLE_API_KEY.
    """
    from dotenv import load_dotenv

    # Load .env before ADK imports
    load_dotenv()

    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from agents.pipeline_analyzer import pipeline_analyzer_agent

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        print("ERROR: GOOGLE_API_KEY not set. Create a .env file from .env.example.")
        sys.exit(1)

    print("=" * 70)
    print("FULL MODE — ADK Agent Runner (LLM + function tool)")
    print("=" * 70)

    runner = Runner(
        agent=pipeline_analyzer_agent,
        app_name="pipeline_analyzer_test",
        session_service=InMemorySessionService(),
    )

    prompt = (
        f"Analyze the pipeline CSV at: {csv_path}\n"
        f"Reference date: {reference_date or 'today'}\n"
        "Flag stagnant deals (14+ days inactive) and show risk scores."
    )

    print(f"\n📨 Prompt: {prompt}\n")
    print("─" * 50)
    print("🤖  Agent response:")
    print("─" * 50)

    async for event in runner.run_async(
        user_id="test_user",
        session_id="analyzer_test_session",
        message=prompt,
    ):
        if hasattr(event, "text") and event.text:
            print(event.text, end="", flush=True)

    print("\n\n✅ ADK agent run complete.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test the Pipeline Analyzer — quick (direct) or full (ADK agent)"
    )
    parser.add_argument(
        "--csv",
        default="data/sample_pipeline.csv",
        help="Path to the CRM pipeline CSV (default: data/sample_pipeline.csv)",
    )
    parser.add_argument(
        "--date",
        default="2025-06-30",
        help="Reference date for analysis in YYYY-MM-DD format (default: 2025-06-30)",
    )
    parser.add_argument(
        "--adk",
        action="store_true",
        help="Run full ADK agent test (needs GOOGLE_API_KEY). Default: quick mode (direct function call).",
    )
    args = parser.parse_args()

    if args.adk:
        asyncio.run(run_adk_test(args.csv, args.date))
    else:
        run_quick_test(args.csv, args.date)


if __name__ == "__main__":
    main()
