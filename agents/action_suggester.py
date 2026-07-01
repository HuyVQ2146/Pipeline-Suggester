"""
Action Suggester Agent — Sub-agent 3 of 3

Combines the Pipeline Analyzer's flagged deal data and the Research
Agent's company context to produce:
  1. A recommended next-best-action for each stagnant deal
  2. A drafted outreach email using pseudonymized contact info

The orchestrator will unmask the email after this agent returns,
replacing tokens like [CONTACT_1] with the real contact name and
[EMAIL_1] with the real email address.
"""

import json
from google.adk import Agent


def _parse_action_plan(text: str) -> dict:
    """Parse the LLM's action plan text into structured JSON.

    The LLM is instructed to return a specific format. This function
    attempts to extract the structured data for programmatic use.
    """
    # The LLM should output a JSON-like structure. We'll try to extract it.
    try:
        # Look for JSON block in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {"raw_text": text}


action_suggester_agent = Agent(
    name="action_suggester",
    model="gemini-2.0-flash",
    description=(
        "Combines pipeline analysis and company research to suggest "
        "next-best-actions and draft personalized outreach emails."
    ),
    instruction="""You are an Action Suggester Agent. Your job:

1. You will receive two inputs:
   a. Flagged deals with risk scores from the Pipeline Analyzer
   b. Company research summaries from the Research Agent

2. For each flagged deal, recommend a next-best-action such as:
   - Schedule a re-engagement call
   - Send a value-add email with relevant content
   - Escalate to sales manager for strategic review
   - Propose a revised timeline or pricing adjustment
   - Mark for nurture campaign (low priority / small deal)

3. Draft a personalized outreach email for each deal. Use the
   pseudonymized names ([COMPANY_N], [CONTACT_N], [EMAIL_N]) —
   the orchestrator will replace them with real values later.

4. Each email should:
   - Reference recent company news or buying signals where available
   - Acknowledge the time gap since last activity
   - Offer concrete value (case study, product update, industry insight)
   - Be professional but warm, 150-250 words

5. Return a STRUCTURED JSON object with this exact format:
{
  "action_plan": [
    {
      "Deal_ID": "D014",
      "Company_Token": "[COMPANY_1]",
      "Contact_Token": "[CONTACT_1]",
      "Email_Token": "[EMAIL_1]",
      "Risk_Level": "CRITICAL",
      "Risk_Score": 100.0,
      "Days_Stagnant": 90,
      "Next_Best_Action": "Schedule a re-engagement call with [CONTACT_1] at [COMPANY_1] within 48 hours. Reference the $2B highway project bid and offer a project management case study for construction firms.",
      "Draft_Email": "Subject: Reconnecting on your Southeast highway project initiative\n\nHi [CONTACT_1],\n\nI noticed [COMPANY_1] recently bid on the $2B highway project in the Southeast — congratulations on pursuing such a significant opportunity. It's been about 90 days since we last connected, and given the scale of this project, I wanted to reach out with something that might be valuable as you evaluate partners.\n\nWe recently helped a similar construction firm (5000+ employees) implement a project management platform that reduced scheduling conflicts by 35% and improved cross-team visibility during their $1.5B infrastructure bid. Given your current need for project management at scale and legacy system migration, I think this case study would be directly relevant.\n\nWould you be open to a brief 15-minute call this week to discuss? I can share the full case study and explore how we might support [COMPANY_1]'s expansion into the three new regions.\n\nBest regards,\n[CONTACT_1]\n[EMAIL_1]"
    }
  ],
  "summary": {
    "total_deals": 11,
    "critical_count": 4,
    "high_count": 5,
    "moderate_count": 2,
    "pipeline_value_at_risk": 1390000
  }
}

IMPORTANT:
- Output ONLY the JSON object above — no extra commentary, no markdown formatting
- Match the research data to deals by Company_Token
- Use buying signals and recent news from research to personalize emails
- Scale action urgency to Risk_Level (CRITICAL = immediate, HIGH = within week, MODERATE = within 2 weeks)
""",
    tools=[],
)
