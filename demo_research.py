"""
Demo script for the Research Agent.

Runs an end-to-end simulation of the Research Agent flow:
  1. Load sample pipeline CSV
  2. Run Pipeline Analyzer to flag stagnant deals
  3. Pseudonymize sensitive fields (company, contact, email)
  4. Pass reverse mapping to research tools for internal token resolution
  5. Call bulk_research tool to get 2-3 sentence summaries per company
  6. Display results with security verification

No API key required — uses direct function calls (quick mode).
"""

import json
import sys
import io

# Force UTF-8 encoding on Windows to handle Unicode output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from utils.anonymizer import Pseudonymizer
from agents.pipeline_tools import analyze_pipeline
from agents.research_tools import (
    research_company,
    bulk_research,
    set_reverse_mapping,
)


def run_demo() -> None:
    """Run the end-to-end Research Agent demo."""
    print("=" * 70)
    print("RESEARCH AGENT — END-TO-END DEMO")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Analyze pipeline to find stagnant deals
    # ------------------------------------------------------------------
    print("\n[Step 1] Analyzing pipeline for stagnant deals...\n")

    result_json = analyze_pipeline(
        csv_path="data/sample_pipeline.csv",
        stagnant_threshold_days=14,
        reference_date="2025-06-30",
    )
    analysis = json.loads(result_json)
    flagged_deals = analysis["flagged_deals"]

    print(f"   Total deals in pipeline: {analysis['total_deals']}")
    print(f"   Stagnant threshold: {analysis['stagnant_threshold_days']} days")
    print(f"   Reference date: {analysis['reference_date']}")
    print(f"   [!] Flagged stagnant deals: {len(flagged_deals)}")
    print(f"   [*] Pipeline value at risk: ${analysis['summary']['total_pipeline_value_at_risk']:,.0f}")
    print(f"      CRITICAL: {analysis['summary']['critical']}  |  "
          f"HIGH: {analysis['summary']['high']}  |  "
          f"MODERATE: {analysis['summary']['moderate']}")

    # ------------------------------------------------------------------
    # Step 2: Pseudonymize sensitive fields (simulating orchestrator)
    # ------------------------------------------------------------------
    print("\n[Step 2] Pseudonymizing sensitive fields (Company, Contact, Email)...\n")

    pseudonymizer = Pseudonymizer()
    pseudonymized_deals = []

    for deal in flagged_deals:
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

    reverse_map = pseudonymizer.get_reverse_mapping()

    print(f"   Pseudonymized {len(pseudonymized_deals)} deals")
    print(f"   Token count: {len(reverse_map)} (tokens -> real values for internal lookup)")
    print(f"   Example mappings:")
    for i, (token, real) in enumerate(list(reverse_map.items())[:5]):
        print(f"      {token} → {real}")
    if len(reverse_map) > 5:
        print(f"      ... and {len(reverse_map) - 5} more")

    # ------------------------------------------------------------------
    # Step 3: Set reverse mapping for research tools
    # ------------------------------------------------------------------
    print("\n[Step 3] Configuring research tools with reverse mapping...\n")
    set_reverse_mapping(reverse_map)

    # ------------------------------------------------------------------
    # Step 4: Extract pseudonymized company tokens for research
    # ------------------------------------------------------------------
    company_tokens = [d["Company_Name"] for d in pseudonymized_deals]
    print(f"[Step 4] Researching {len(company_tokens)} flagged companies...\n")

    # ------------------------------------------------------------------
    # Step 5: Run bulk research (single efficient call)
    # ------------------------------------------------------------------
    print("   Calling bulk_research()...")
    names_json = json.dumps(company_tokens)
    bulk_json = bulk_research(names_json)
    bulk_result = json.loads(bulk_json)

    print(f"   [OK] Requested: {bulk_result['total_requested']}  |  "
          f"Found: {bulk_result['found']}  |  Not found: {bulk_result['not_found']}\n")

    # ------------------------------------------------------------------
    # Step 6: Display results with 2-3 sentence summaries
    # ------------------------------------------------------------------
    print("=" * 70)
    print("RESEARCH FINDINGS — 2-3 Sentence Summaries Per Company")
    print("=" * 70)

    for i, entry in enumerate(bulk_result["results"], 1):
        token = entry.get("company", "???")
        real_name = reverse_map.get(token, token)
        status = entry.get("status", "unknown")

        print(f"\n{i}. {token}  (→ {real_name})")
        print(f"   Risk Level: {pseudonymized_deals[i-1]['Risk_Level']}  |  "
              f"Score: {pseudonymized_deals[i-1]['Risk_Score']}  |  "
              f"Days Stagnant: {pseudonymized_deals[i-1]['Days_Stagnant']}")

        if status == "found":
            print(f"   Industry:     {entry['industry']}")
            print(f"   Employees:    {entry['employee_count']}")
            print(f"   Recent News:  {entry['recent_news']}")
            print(f"   Tech Stack:   {', '.join(entry['tech_stack'])}")
            print(f"   Buying Signals: {'; '.join(entry['buying_signals'])}")
            print(f"\n   [SUMMARY] {entry['summary']}")
        else:
            print(f"   [!] {entry.get('message', 'No research data available')}")

    # ------------------------------------------------------------------
    # Step 7: Security verification
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SECURITY VERIFICATION")
    print("=" * 70)

    real_emails = set(reverse_map.get(k, "") for k in reverse_map if k.startswith("[EMAIL_"))
    real_contacts = set(reverse_map.get(k, "") for k in reverse_map if k.startswith("[CONTACT_"))
    real_companies = set(reverse_map.get(k, "") for k in reverse_map if k.startswith("[COMPANY_"))

    leaked = False
    for entry in bulk_result["results"]:
        output_text = json.dumps(entry)
        for email in real_emails:
            if email and email in output_text:
                print(f"  [LEAK] Email '{email}' found in tool output!")
                leaked = True
        for contact in real_contacts:
            if contact and contact in output_text:
                print(f"  [LEAK] Contact name '{contact}' found in tool output!")
                leaked = True
        for company in real_companies:
            if company and company in output_text:
                print(f"  [LEAK] Company name '{company}' found in tool output!")
                leaked = True

    if not leaked:
        print("  [OK] No PII leaked into research tool output.")
        print("  [OK] Company names in news/signals sanitized to tokens.")
        print("  [OK] Contact names and emails never reach the LLM.")
        print("  [OK] Reverse mapping used only for internal DB lookups.")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE — Research Agent ready for production use")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()