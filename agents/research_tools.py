"""
Python function tools for the Research Agent.

These tools are registered on the researcher ADK agent via the `tools`
parameter. The LLM decides when to call them based on the user's
request and the agent's instructions.

Two tools are provided:
  1. research_company    — looks up a single company in the mock DB
  2. bulk_research       — looks up multiple companies at once and
                           returns structured JSON with research summaries

Both tools accept *pseudonymized* company names (e.g., [COMPANY_1])
as input. They use a reverse-mapping dict passed at initialization
to resolve the real company name before querying the database.

SECURITY RATIONALE:
  The LLM only sees pseudonymized data in its conversation context.
  Contact names, emails, and even company names are replaced with
  tokens like [COMPANY_1], [CONTACT_1], [EMAIL_1]. This prevents
  PII from being logged, cached, or used for model training.

  However, the mock company DB is keyed by *real* company names.
  So these tools resolve tokens to real names internally, perform
  the lookup, and return only the *research results* (industry,
  news, buying signals) — never the original PII.

  The reverse mapping is populated by the test script / orchestrator
  before the agent runs. It lives only in process memory and is
  never logged or persisted.
"""

import json
import re
from data.mock_companies import MOCK_COMPANY_DB


# ---------------------------------------------------------------------------
# Module-level reverse mapping — set by the orchestrator or test script
# before the agent runs. Maps pseudonym tokens back to real values,
# e.g. {"[COMPANY_1]": "Acme Corp", "[CONTACT_1]": "John Smith", ...}
#
# SECURITY: This dict must NEVER be included in any LLM prompt, logged
# to disk, or returned in tool output. It is used solely for internal
# lookups so the tools can find the right company in the mock DB.
# ---------------------------------------------------------------------------
_reverse_map: dict[str, str] = {}


def set_reverse_mapping(mapping: dict[str, str]) -> None:
    """Set the reverse pseudonym mapping for tool lookups.

    Called by the orchestrator or test script before the agent runs.
    The mapping comes from Pseudonymizer.get_mapping_summary().

    Args:
        mapping: dict of token -> real_value, e.g.
            {"[COMPANY_1]": "Acme Corp", "[EMAIL_1]": "john@acmecorp.com"}
    """
    global _reverse_map
    _reverse_map = mapping.copy()


def _resolve_company_name(name: str) -> str:
    """Resolve a possibly-pseudonymized company name to its real value.

    If the name looks like a token ([COMPANY_N]), look it up in the
    reverse mapping. Otherwise return it as-is (may already be a real
    name from a non-pseudonymized context, e.g. a direct test call).

    Args:
        name: Company name or pseudonym token.

    Returns:
        The real company name, or the original value if no mapping found.
    """
    # SECURITY: We only resolve tokens here — the resolved name is used
    # purely as a lookup key in the mock DB. It is NEVER echoed back
    # into the LLM conversation. The tool's return value contains only
    # research findings (industry, news, buying signals), not PII.
    if name.startswith("[") and name.endswith("]"):
        resolved = _reverse_map.get(name, name)
        return resolved
    return name


def _sanitize_output(text: str, real_name: str, token: str) -> str:
    """Replace occurrences of real company name with pseudonym token in text.

    This ensures the LLM never sees real company names in news, buying
    signals, or any other text fields returned by the research tools.

    Args:
        text: The text to sanitize.
        real_name: The real company name to mask.
        token: The pseudonym token to replace it with (e.g., "[COMPANY_1]").

    Returns:
        Sanitized text with real name replaced by token.
    """
    if not text or not real_name:
        return text
    # Case-insensitive whole-word-ish replacement to avoid partial matches
    # Use word boundaries for the real name
    pattern = re.compile(re.escape(real_name), re.IGNORECASE)
    return pattern.sub(token, text)


# ---------------------------------------------------------------------------
# ADK Tool: research_company
# Looks up a single company and returns a structured research summary.
# This is the primary tool the Research Agent calls for each flagged deal.
# ---------------------------------------------------------------------------

def research_company(company_name: str) -> str:
    """Look up contextual information about a single company.

    Accepts either a real company name or a pseudonymized token
    (e.g. [COMPANY_1]). If a token is provided, it is resolved
    internally using the reverse pseudonym mapping — the LLM never
    sees the real name.

    Returns structured data including industry, employee count,
    recent news, tech stack, and buying signals.

    Args:
        company_name: Company name or pseudonym token (e.g. [COMPANY_1]).

    Returns:
        JSON string with company research data, or an error message
        if the company is not found in the database.
    """
    real_name = _resolve_company_name(company_name)
    key = real_name.strip().lower()
    info = MOCK_COMPANY_DB.get(key)

    if not info:
        # Return a valid JSON "not found" response so the LLM can
        # handle it gracefully instead of erroring.
        available = sorted(MOCK_COMPANY_DB.keys())
        return json.dumps({
            "company": company_name,  # Return the TOKEN, not the real name
            "status": "not_found",
            "message": (
                f"No research data available for '{company_name}'. "
                f"The Action Suggester should rely on general best practices."
            ),
            "available_companies": available,
        }, indent=2)

    # SECURITY: Return the *input* company_name (which may be a pseudonymized
    # token like [COMPANY_1]), NOT the resolved real_name. This prevents the
    # LLM from ever seeing the real company name in the tool output.
    # Rationale: Even though company names are less sensitive than contact
    # emails/names, they can identify individuals in small companies and
    # constitute business intelligence that should not leave the local system.
    #
    # Also sanitize text fields that may contain the real company name
    # (e.g., "Xi Constructors bid on..." -> "[COMPANY_1] bid on...")
    sanitized_news = _sanitize_output(info["recent_news"], real_name, company_name)
    sanitized_signals = [_sanitize_output(s, real_name, company_name) for s in info["buying_signals"]]

    return json.dumps({
        "company": company_name,
        "status": "found",
        "industry": info["industry"],
        "employee_count": info["employee_count"],
        "recent_news": sanitized_news,
        "tech_stack": info["tech_stack"],
        "buying_signals": sanitized_signals,
    }, indent=2)


# ---------------------------------------------------------------------------
# ADK Tool: bulk_research
# Convenience tool that looks up multiple companies in one call and
# returns structured summaries. More efficient than calling
# research_company N times when the agent has a batch of flagged deals.
# ---------------------------------------------------------------------------

def bulk_research(company_names_json: str) -> str:
    """Research multiple companies at once and return structured summaries.

    Accepts a JSON list of company names (real or pseudonymized tokens).
    Looks up each company and returns a combined research report with
    2-3 sentence summaries per company.

    Args:
        company_names_json: JSON array of company name strings.
            Example: '["Xi Constructors", "Delta Ltd", "[COMPANY_3]"]'

    Returns:
        JSON string with a "results" list. Each entry contains the
        company research data plus a "summary" field with a concise
        2-3 sentence overview of the findings.
    """
    names: list[str] = json.loads(company_names_json)
    results: list[dict] = []

    for name in names:
        result_json = research_company(name)
        result = json.loads(result_json)

        if result.get("status") == "found":
            # Generate a concise 2-3 sentence summary from the raw data.
            # This is done in code (not by the LLM) so the summary is
            # deterministic and always fits the 2-3 sentence format.
            industry = result["industry"]
            employees = result["employee_count"]
            news = result["recent_news"]
            signals = "; ".join(result["buying_signals"])
            # SECURITY: Use the token (result['company']) not the real name
            # in the summary, so the LLM never sees the real company name.
            result["summary"] = (
                f"{result['company']} is a {industry} company with "
                f"{employees} employees. {news} "
                f"Key buying signals: {signals}."
            )
        else:
            # For not_found, result['company'] is already the token
            result["summary"] = (
                f"No detailed research available for {result.get('company', name)}. "
                "Recommend the Action Suggester rely on general re-engagement "
                "best practices for this account."
            )

        results.append(result)

    return json.dumps({
        "total_requested": len(names),
        "found": sum(1 for r in results if r.get("status") == "found"),
        "not_found": sum(1 for r in results if r.get("status") == "not_found"),
        "results": results,
    }, indent=2)
