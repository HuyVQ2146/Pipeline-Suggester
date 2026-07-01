"""
Python function tools for the Pipeline Analyzer Agent.

These tools are registered on the pipeline_analyzer ADK agent via the
`tools` parameter. The LLM decides when to call them based on the
user's request and the agent's instructions.

ADK auto-generates the tool schema from the function's type hints
and docstring, so keep both accurate and descriptive.

Risk scoring model (0-100 total):
  ┌───────────────────┬─────────┬──────────────────────────────────────┐
  │ Factor            │ Max pts │ Rationale                            │
  ├───────────────────┼─────────┼──────────────────────────────────────┤
  │ Days stagnant     │   40    │ Longer silence = higher chance of    │
  │                   │         │ deal death. Scales linearly from     │
  │                   │         │ 0 pts at 14 days to 40 pts at 90+.  │
  ├───────────────────┼─────────┼──────────────────────────────────────┤
  │ Deal value        │   30    │ Bigger deals = more revenue at risk.│
  │                   │         │ $30k → 5 pts, $200k+ → 30 pts,      │
  │                   │         │ linearly interpolated between.      │
  ├───────────────────┼─────────┼──────────────────────────────────────┤
  │ Stage latency     │   30    │ Stuck in late stage (Negotiation,   │
  │                   │         │ Proposal) means more sunk effort     │
  │                   │         │ and higher probability of collapse.  │
  │                   │         │ Early stage stagnation is less       │
  │                   │         │ alarming (Qualification = 10,        │
  │                   │         │ Discovery = 15, Proposal = 25,      │
  │                   │         │ Negotiation = 30).                   │
  └───────────────────┴─────────┴──────────────────────────────────────┘

  Classification:  ≥80 = CRITICAL, 50-79 = HIGH, <50 = MODERATE
"""

import json
from datetime import datetime, date
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Stage latency scoring — how "expensive" it is for a deal to stall
# at each pipeline stage. Late-stage stagnation is riskier because
# more sales effort has been invested and customer expectations are set.
# ---------------------------------------------------------------------------
STAGE_RISK_WEIGHTS: dict[str, int] = {
    "Negotiation": 30,   # Highest: deal is at the finish line, stalling here
                         # often signals buyer hesitation or competitor threat.
    "Proposal": 25,      # High: a proposal was submitted but no response —
                         # the prospect may be comparing vendors.
    "Discovery": 15,     # Moderate: still early, but silence means the
                         # prospect may have deprioritized the initiative.
    "Qualification": 10, # Lowest: early-stage deals naturally move slowly;
                         # stagnation here is less concerning.
}

# Scoring constants — used by _compute_risk_score()
DAYS_STAGNANT_MIN = 14    # Below this threshold → not flagged as stagnant
DAYS_STAGNANT_MAX = 90    # At or above this → max points for this factor
DAYS_STAGNANT_PTS = 40    # Maximum points for the days-stagnant factor

DEAL_VALUE_MIN = 30_000       # Deals at or below this value → minimum pts
DEAL_VALUE_MAX = 200_000      # Deals at or above this value → maximum pts
DEAL_VALUE_PTS_MIN = 5        # Minimum points for deal value factor
DEAL_VALUE_PTS_MAX = 30       # Maximum points for deal value factor


def _compute_risk_score(
    days_stagnant: int,
    deal_value: float,
    stage: str,
) -> tuple[float, str]:
    """Compute a risk score (0-100) and classification for a stagnant deal.

    This is a private helper — not exposed as an ADK tool directly.
    The score is the sum of three weighted factors:
      1. Days stagnant   (0-40 pts) — how long the deal has been idle
      2. Deal value       (5-30 pts) — revenue at risk
      3. Stage latency    (10-30 pts) — which pipeline stage is stalled

    Args:
        days_stagnant: Calendar days since the last activity on this deal.
        deal_value:    Dollar value of the deal.
        stage:         Pipeline stage name (case-insensitive).

    Returns:
        A tuple of (score: float, level: str) where level is
        "CRITICAL" (≥80), "HIGH" (50-79), or "MODERATE" (<50).
    """
    # --- Factor 1: Days stagnant (0-40 pts) ---
    # Linear scale: 14 days = 0 pts, 90+ days = 40 pts.
    # A deal barely past the threshold gets minimal points; a deal
    # silent for 3 months gets the maximum.
    if days_stagnant <= DAYS_STAGNANT_MIN:
        days_pts = 0.0
    elif days_stagnant >= DAYS_STAGNANT_MAX:
        days_pts = float(DAYS_STAGNANT_PTS)
    else:
        days_pts = (days_stagnant - DAYS_STAGNANT_MIN) / (
            DAYS_STAGNANT_MAX - DAYS_STAGNANT_MIN
        ) * DAYS_STAGNANT_PTS

    # --- Factor 2: Deal value (5-30 pts) ---
    # Larger deals represent more revenue at risk. We use a linear
    # interpolation between $30k (5 pts) and $200k (30 pts).
    if deal_value <= DEAL_VALUE_MIN:
        value_pts = float(DEAL_VALUE_PTS_MIN)
    elif deal_value >= DEAL_VALUE_MAX:
        value_pts = float(DEAL_VALUE_PTS_MAX)
    else:
        value_pts = DEAL_VALUE_PTS_MIN + (
            (deal_value - DEAL_VALUE_MIN)
            / (DEAL_VALUE_MAX - DEAL_VALUE_MIN)
            * (DEAL_VALUE_PTS_MAX - DEAL_VALUE_PTS_MIN)
        )

    # --- Factor 3: Stage latency (10-30 pts) ---
    # A deal stuck in Negotiation is far more alarming than one stuck
    # in Qualification — more effort invested, more expectations set.
    stage_pts = float(STAGE_RISK_WEIGHTS.get(stage, 15))
    # Default to Discovery weight (15) for unrecognized stages.

    # --- Aggregate score & classification ---
    total = round(days_pts + value_pts + stage_pts, 1)

    if total >= 80:
        level = "CRITICAL"
    elif total >= 50:
        level = "HIGH"
    else:
        level = "MODERATE"

    return total, level


# ---------------------------------------------------------------------------
# ADK Tool: analyze_pipeline
# This is the primary tool exposed to the pipeline_analyzer agent.
# It reads the CSV, computes days since last activity, flags stagnant
# deals, and returns a structured JSON result.
# ---------------------------------------------------------------------------

def analyze_pipeline(
    csv_path: str,
    stagnant_threshold_days: int = 14,
    reference_date: str = "",
) -> str:
    """Analyze a CRM pipeline CSV to flag stagnant deals and compute risk scores.

    Reads the pipeline CSV, identifies deals with no activity for more
    than the specified number of days, and computes a risk score (0-100)
    for each flagged deal based on days stagnant, deal value, and pipeline
    stage. Returns a structured JSON result with all flagged deals sorted
    by risk score descending, plus summary statistics.

    Risk score breakdown (0-100 total):
      - Days stagnant: 0-40 points (14 days = 0, 90+ days = 40)
      - Deal value:    5-30 points ($30k = 5, $200k+ = 30)
      - Stage latency: 10-30 points (Qualification=10, Discovery=15,
                        Proposal=25, Negotiation=30)
    Classification: >=80 CRITICAL, 50-79 HIGH, <50 MODERATE

    Args:
        csv_path: Path to the CRM pipeline CSV file. Expected columns:
            Deal_ID, Company_Name, Contact_Name, Contact_Email,
            Deal_Value, Stage, Last_Activity_Date, Owner.
        stagnant_threshold_days: Number of days with no activity before
            a deal is flagged as stagnant. Default: 14.
        reference_date: Reference date for the analysis in YYYY-MM-DD
            format. Defaults to today if empty or not provided.

    Returns:
        JSON string with keys:
          - reference_date: str — the date used as "today" for comparison
          - stagnant_threshold_days: int — the threshold applied
          - total_deals: int — number of deals in the CSV
          - flagged_deals: list[dict] — stagnant deals sorted by risk (desc)
          - summary: dict — counts by risk level + total pipeline value at risk
    """
    # Determine the reference date for "today" in the analysis.
    # Defaults to the actual current date; can be overridden for testing.
    if reference_date:
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
    else:
        ref_date = date.today()

    # Read the CSV — pandas handles quoting, encoding, and type coercion.
    df = pd.read_csv(csv_path)
    # Keep as datetime64 (not .dt.date) so vectorized subtraction yields
    # a Timedelta Series with a .dt.days accessor.
    df["Last_Activity_Date"] = pd.to_datetime(df["Last_Activity_Date"])
    df["Deal_Value"] = pd.to_numeric(df["Deal_Value"], errors="coerce").fillna(0)

    # Compute calendar days since last activity for every deal.
    # Convert ref_date to a pandas Timestamp so the subtraction is
    # vectorized and returns a Timedelta Series.
    ref_ts = pd.Timestamp(ref_date)
    df["Days_Since_Activity"] = (ref_ts - df["Last_Activity_Date"]).dt.days

    # Flag stagnant deals — those exceeding the inactivity threshold.
    stagnant = df[df["Days_Since_Activity"] > stagnant_threshold_days].copy()

    # Compute risk score and classification for each stagnant deal.
    flagged: list[dict] = []
    for _, row in stagnant.iterrows():
        score, level = _compute_risk_score(
            days_stagnant=int(row["Days_Since_Activity"]),
            deal_value=float(row["Deal_Value"]),
            stage=str(row["Stage"]),
        )
        flagged.append({
            "Deal_ID": str(row["Deal_ID"]),
            "Company_Name": str(row["Company_Name"]),
            "Contact_Name": str(row["Contact_Name"]),
            "Contact_Email": str(row["Contact_Email"]),
            "Deal_Value": float(row["Deal_Value"]),
            "Stage": str(row["Stage"]),
            "Owner": str(row["Owner"]),
            "Last_Activity_Date": str(row["Last_Activity_Date"].date()),
            "Days_Stagnant": int(row["Days_Since_Activity"]),
            "Risk_Score": score,
            "Risk_Level": level,
        })

    # Sort by risk score descending — most critical deals appear first.
    flagged.sort(key=lambda d: d["Risk_Score"], reverse=True)

    # Summary statistics for quick stakeholder overview.
    critical_count = sum(1 for d in flagged if d["Risk_Level"] == "CRITICAL")
    high_count = sum(1 for d in flagged if d["Risk_Level"] == "HIGH")
    moderate_count = sum(1 for d in flagged if d["Risk_Level"] == "MODERATE")
    total_value_at_risk = sum(d["Deal_Value"] for d in flagged)

    result = {
        "reference_date": str(ref_date),
        "stagnant_threshold_days": stagnant_threshold_days,
        "total_deals": len(df),
        "flagged_deals": flagged,
        "summary": {
            "flagged_count": len(flagged),
            "critical": critical_count,
            "high": high_count,
            "moderate": moderate_count,
            "total_pipeline_value_at_risk": total_value_at_risk,
        },
    }

    return json.dumps(result, indent=2)
