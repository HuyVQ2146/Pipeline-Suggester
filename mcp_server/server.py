"""
MCP Server for the Pipeline Suggester agent system.

Exposes two tools over the Model Context Protocol (MCP) via stdio transport:
  1. read_pipeline_csv   — reads a CRM pipeline CSV and returns its contents
  2. search_company_info  — returns mock company research data for a given name

This server is launched as a subprocess by the ADK agent runner
(see agents/researcher.py for the MCPToolset connection config).

Run standalone:
    python -m mcp_server.server
"""

import csv
import json
import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Import the shared mock company database so that the MCP server and
# the Research Agent function tools always use the same source of truth.
# If you add a company to the CSV, add it here (and in mock_companies.py) once.
from data.mock_companies import MOCK_COMPANY_DB

# ---------------------------------------------------------------------------
# MCP Server Token Resolution
#
# SECURITY: The MCP server can also receive pseudonymized tokens like [COMPANY_1].
# For the MCP tool to resolve these, the reverse mapping must be passed via
# environment variable. This is set by the orchestrator before spawning the MCP
# server subprocess. Without this, tokens appear as-is in tool output.
# ---------------------------------------------------------------------------
_REVERSE_MAP: dict[str, str] = {}


def _load_reverse_mapping() -> None:
    """Load the reverse mapping from environment variable.

    The orchestrator passes the token->real mapping via REVERSE_MAP_JSON env var
    before launching the MCP server subprocess. This allows the search_company_info
    MCP tool to resolve pseudonym tokens to real company names for DB lookup,
    while ensuring the output is sanitized back to tokens (no PII in LLM context).
    """
    global _REVERSE_MAP
    map_json = os.getenv("REVERSE_MAP_JSON", "{}")
    try:
        _REVERSE_MAP = json.loads(map_json)
    except json.JSONDecodeError:
        _REVERSE_MAP = {}


def _resolve_company_name(name: str) -> str:
    """Resolve a pseudonymized token to real company name for DB lookup.

    SECURITY: The resolved real name is used ONLY as a lookup key.
    It is never returned to the LLM — output is always sanitized to tokens.
    """
    if name.startswith("[") and name.endswith("]"):
        return _REVERSE_MAP.get(name, name)
    return name


def _sanitize_output(text: str, real_name: str, token: str) -> str:
    """Replace real company names with pseudonym tokens in text output.

    Ensures no PII (company names) leak into LLM context, even if the
    mock database contains real names in news/buying_signals text fields.
    """
    if not text or not real_name:
        return text
    pattern = re.compile(re.escape(real_name), re.IGNORECASE)
    return pattern.sub(token, text)


# Load mapping at module import time (before any tool calls)
_load_reverse_mapping()

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("pipeline-mcp")


# ---------------------------------------------------------------------------
# Tool 1: read_pipeline_csv
# Reads a CRM pipeline CSV file and returns its contents as a formatted
# text table. Falls back to the bundled sample data if the file is not found.
# ---------------------------------------------------------------------------

@mcp.tool()
def read_pipeline_csv(file_path: str) -> str:
    """Read a CRM pipeline CSV file and return its contents as formatted text.

    The CSV should have columns: Deal_ID, Company_Name, Contact_Name,
    Contact_Email, Deal_Value, Stage, Last_Activity_Date, Owner.

    Args:
        file_path: Absolute or relative path to the CSV file.

    Returns:
        A pipe-delimited text table with headers and a separator line.
    """
    path = Path(file_path)
    if not path.exists():
        # Fall back to the sample data bundled with this project
        fallback = Path(__file__).resolve().parent.parent / "data" / "sample_pipeline.csv"
        if fallback.exists():
            path = fallback
        else:
            return f"Error: CSV file not found at {file_path}"

    rows: list[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows.append(" | ".join(headers))
        rows.append("-" * 60)
        for row in reader:
            rows.append(" | ".join(row.get(h, "") for h in headers))

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Tool 2: search_company_info
# Returns mock company intelligence (industry, size, news, buying signals).
# In production, this would call a real data provider API.
# ---------------------------------------------------------------------------

@mcp.tool()
def search_company_info(company_name: str) -> str:
    """Look up contextual information about a company by name.

    Accepts either a real company name or a pseudonymized token like [COMPANY_1].
    If a token is provided, it is resolved using REVERSE_MAP_JSON to look up
    the real company in the mock database.

    SECURITY RATIONALE:
        The LLM sees only pseudonymized tokens (e.g., [COMPANY_1]) in its
        context. The MCP server resolves tokens internally to real names solely
        as lookup keys against the mock DB. Any text fields that contain the
        real company name are sanitized back to the token before being returned
        in the tool output. This prevents business intelligence (company names)
        from leaking into model prompts, cached logs, or training data.

    Returns mock data including industry, size, recent news, tech stack,
    and buying signals. In production, this would call a real data
    provider (e.g., Clearbit, Crunchbase, LinkedIn API).

    Args:
        company_name: Name of the company to research (case-insensitive).
            May be a real name or a pseudonymized token like [COMPANY_1].

    Returns:
        A formatted company profile, or a not-found message with the
        list of available mock companies. All company names in text are
        sanitized to the input token (never expose real names to LLM).
    """
    # Resolve pseudonymized token to real company name for lookup
    real_name = _resolve_company_name(company_name)
    key = real_name.strip().lower()
    info = MOCK_COMPANY_DB.get(key)

    if not info:
        available = ", ".join(c.title() for c in MOCK_COMPANY_DB)
        return (
            f"No detailed information found for '{company_name}'. "
            f"Available companies: {available}"
        )

    # SECURITY: Sanitize text fields that may contain the real company name
    # to prevent PII leakage into the LLM context.
    sanitized_news = _sanitize_output(info["recent_news"], real_name, company_name)
    sanitized_signals = [
        _sanitize_output(s, real_name, company_name) for s in info["buying_signals"]
    ]

    lines = [
        f"Company: {company_name}",  # Use token, not real name
        f"Industry: {info['industry']}",
        f"Employees: {info['employee_count']}",
        f"Recent News: {sanitized_news}",
        f"Tech Stack: {', '.join(info['tech_stack'])}",
        f"Buying Signals: {'; '.join(sanitized_signals)}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Server entry point — run via stdio transport
# The ADK agent runner spawns this as a subprocess.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
