# 📋 Prompt 1 — Project scaffolding & architecture

I'm building a "Pipeline Suggester" AI agent for a hackathon (Google ADK + MCP based). 

Project goal: An agent system that analyzes a sales pipeline (CSV data), identifies stagnant deals (no activity for N+ days), researches the account for context, and suggests next-best-actions with a drafted outreach email.

Requirements:
- Multi-agent architecture using Google ADK with 3 sub-agents:
  1. Pipeline Analyzer Agent — reads CRM CSV data, flags stagnant deals, computes a risk score
  2. Research Agent — gathers extra context on flagged accounts (via an MCP tool, e.g. web search or mock company-info API)
  3. Action Suggester Agent — combines analyzer + research output, produces next-best-action and a draft outreach email
- An MCP server exposing at least one tool (e.g. read_pipeline_csv or search_company_info)
- A basic security measure: mask/anonymize sensitive customer data (names, emails) before sending to the LLM, and explain this in code comments
- Clean Python project structure, with meaningful comments throughout
- No hardcoded API keys — use environment variables / .env

Please:
1. Propose a clear project folder structure
2. Set up the base ADK agent orchestrator and the MCP server skeleton (no business logic yet, just working scaffolding)
3. Add a requirements.txt / pyproject.toml
4. Explain in 3-4 sentences how the agents will communicate

Ask me clarifying questions if anything about the data format or tool design is ambiguous before writing code.

---

# 📊 Prompt 2 — Mock data + Pipeline Analyzer Agent

Now let's build the first sub-agent: Pipeline Analyzer.

1. Generate a realistic mock CRM dataset (CSV) with ~20 deals: columns like deal_id, company_name, deal_value, stage, last_activity_date, contact_name, contact_email
2. Implement the Pipeline Analyzer Agent logic:
   - Reads the CSV (via the MCP tool we scaffolded)
   - Flags deals with no activity for more than 14 days as "stagnant"
   - Computes a simple risk score (e.g. based on days since last activity + deal stage + deal value)
   - Returns a structured list of flagged deals with risk scores
3. Add comments explaining the scoring logic
4. Write a small test/demo script so I can run this agent in isolation and see output in the terminal

---

# 🔍 Prompt 3 — Research Agent

Now build the Research Agent.

For each flagged deal from the Pipeline Analyzer, this agent should:
- Take the company_name as input
- Call an MCP tool to fetch extra context (use a mock/simulated company-info lookup if no real API is available — return believable fake info like recent news, company size, industry)
- Summarize findings in 2-3 sentences per company

Make sure:
- The MCP tool is properly registered and callable by the agent
- Sensitive contact info (email, contact_name) is masked/anonymized before being sent in any LLM prompt — show this clearly in code with a comment explaining the security rationale
- Add a demo script to test this agent on a few sample companies

---

# ⚡ Prompt 4 — Action Suggester Agent + orchestration

Now build the Action Suggester Agent and wire everything together.

This agent should:
- Take the output of Pipeline Analyzer (risk-scored deals) and Research Agent (company context)
- For each flagged deal, generate:
  1. A recommended next-best-action (e.g. "schedule a check-in call", "send pricing update")
  2. A short draft outreach email personalized using the research context
- Return results in a clean structured format (JSON or similar)

Then:
- Implement the main orchestrator that runs Pipeline Analyzer → Research Agent → Action Suggester in sequence (this is the multi-agent ADK flow)
- Add a single entry point script (main.py) that runs the full pipeline end-to-end on the mock CSV and prints a readable summary report to the terminal

---

# 🎨 Prompt 5 — Polish, README, deployment

Final polish pass:

1. Write a comprehensive README.md including:
   - Problem statement
   - Solution overview
   - Architecture diagram (describe it in Mermaid syntax)
   - Setup & run instructions (local)
   - Explanation of which course concepts are demonstrated (ADK multi-agent, MCP server, Security/data anonymization) and where to find them in the code
2. Add a simple CLI or minimal web UI (if time permits) to make the demo more visually appealing for a video recording
3. Suggest how I could deploy this (e.g. Cloud Run) for a public demo link, with step-by-step instructions
4. Double check: no API keys hardcoded anywhere, all secrets via .env, and .env is gitignored

Review the whole codebase for consistency and add any missing comments.

