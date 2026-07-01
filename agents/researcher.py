"""
Research Agent — Sub-agent 2 of 3

Gathers contextual information about flagged accounts by calling the
research_company and bulk_research tools. These tools query the shared
mock company database (data/mock_companies.py) and return structured
research data: industry, employee count, recent news, tech stack,
and buying signals.

The MCP server (mcp_server/server.py) also exposes a search_company_info
tool for cross-tool interoperability, but the Research Agent primarily
uses the Python function tools below because they:
  1. Accept pseudonymized tokens and resolve them internally
  2. Return structured JSON (easier for the next agent to consume)
  3. Include auto-generated 2-3 sentence summaries

SECURITY DESIGN:
  This agent receives ONLY pseudonymized data — company names appear
  as tokens like [COMPANY_1], and contacts/emails are masked. The
  resolve step happens inside the tool implementation (see
  research_tools.py), which maps tokens to real names purely as
  lookup keys against the mock DB. The LLM context never contains
  real PII. Research results returned to the LLM contain industry
  info, news, and buying signals — but NOT the raw contact details.
"""

import os
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams

from agents.research_tools import research_company, bulk_research

# ---------------------------------------------------------------------------
# MCP toolset — connects to our stdio-based MCP server.
# Kept as a supplementary tool source; the primary tools are the
# Python function tools (research_company, bulk_research) which
# handle pseudonym resolution internally.
#
# SECURITY: The MCP server receives REVERSE_MAP_JSON env var to resolve
# pseudonym tokens to real company names for DB lookup, but sanitizes
# all output text back to tokens (see mcp_server/server.py).
# ---------------------------------------------------------------------------
from mcp.client.stdio import StdioServerParameters

mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=["mcp_server/server.py"],
            # Pass reverse mapping via environment so MCP server can resolve tokens
            # while still sanitizing output to tokens (no PII to LLM).
            # SECURITY: The mapping is injected at agent-definition load time;
            # it must be set before the agent runs. See main.py.
            env={
                "REVERSE_MAP_JSON": os.getenv("REVERSE_MAP_JSON", "{}"),
            },
        ),
    ),
    # Optional: prefix tool names to avoid conflicts
    tool_name_prefix="mcp",
)

researcher_agent = Agent(
    name="researcher",
    model="gemini-2.0-flash",
    description=(
        "Researches flagged accounts by looking up company information "
        "via research tools. Returns contextual data (industry, news, "
        "buying signals) with 2-3 sentence summaries per company."
    ),
    instruction="""You are a Research Agent. Your job:

1. You will receive a list of flagged (stagnant) deals from the
   Pipeline Analyzer. The company names may be pseudonymized as
   tokens like [COMPANY_1] — that is expected, pass them as-is
   to the research tools. The tools resolve tokens internally.

2. Use the `bulk_research` tool to look up all flagged companies
   at once. Pass the company names (or tokens) as a JSON array
   string. This is more efficient than calling `research_company`
   one at a time.

   Example call:
     bulk_research('["[COMPANY_1]", "[COMPANY_3]", "Delta Ltd"]')

3. Alternatively, if you prefer to research one company at a time,
   use `research_company` for each:
     research_company("[COMPANY_1]")
     research_company("Delta Ltd")

4. Review the JSON results. For each company you will get:
   - industry, employee_count, recent_news, tech_stack, buying_signals
   - A pre-generated 2-3 sentence summary

5. Present the research findings clearly for the next agent
   (Action Suggester). Format the output as:
   - Company name (or token if still pseudonymized)
   - Summary of research
   - Key buying signals that should inform outreach

6. If a company is "not_found", note it and suggest the Action
   Suggester use general re-engagement best practices.

7. Do NOT fabricate research data — only report what the tools return.
   Do NOT attempt to unmask pseudonym tokens yourself — that is the
   orchestrator's job after the final output is produced.
""",
    # Primary tools: Python function tools that resolve pseudonyms internally.
    # Supplementary: MCP toolset (search_company_info) for cross-tool compat.
    tools=[research_company, bulk_research, mcp_toolset],
)
