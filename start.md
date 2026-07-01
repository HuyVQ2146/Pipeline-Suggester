# Pipeline Suggester — Getting Started Guide

> A multi-agent AI system that analyzes your sales pipeline, identifies stagnant deals, researches the accounts, and drafts personalized outreach emails.

---

## 1. Prerequisites

### 1.1 Python Version
- **Python 3.10 or higher** (tested on 3.11, 3.12)

### 1.2 Clone the Repository
```bash
git clone <your-repo-url>
cd pipeline-suggester
```

### 1.3 Install Dependencies

**Using pip (recommended):**
```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Using uv (faster):**
```bash
# Install uv if not present: pip install uv
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt
```

**Using Poetry:**
```bash
# This project uses pyproject.toml, so Poetry works natively
poetry install
poetry shell
```

### 1.4 Set Up Environment Variables

Copy `.env`

Copy the example and fill in your values:
```bash
cp .env.example .env
```

**Required variables in `.env`:**

| Variable | Placeholder | Description |
|----------|-------------|-------------|
| `GOOGLE_API_KEY` | `your_google_api_key_here` | **Required.** Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Used by ADK agents for LLM calls. |
| `STAGNANT_DAYS_THRESHOLD` | `14` | Optional. Days of inactivity before a deal is flagged as stagnant. Default: 14. |

**Example `.env`:**
```env
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
STAGNANT_DAYS_THRESHOLD=14
```

> **Security:** Never commit `.env` to git. It's already in `.gitignore`.

---

## 2. Run Locally (Terminal)

### 2.1 Full Pipeline (End-to-End)
Runs all 3 agents sequentially: **Pipeline Analyzer → Researcher → Action Suggester**

```bash
# Uses bundled sample data (data/sample_pipeline.csv)
python main.py

# Or with your own CRM CSV
python main.py --csv path/to/your_pipeline.csv
```

**Expected terminal output:**
```text
⚙️  Stagnant threshold: 14 days
📂 Reading pipeline data from: data/sample_pipeline.csv
🔒 Pseudonymized 20 rows. Tokens: {'Acme Corp': '[COMPANY_1]', 'John Smith': '[CONTACT_1]', ...}
🚀 Starting Pipeline Suggester agent workflow...

[Pipeline Analyzer output — flagged deals with risk scores]
[Researcher output — company summaries with buying signals]
[Action Suggester output — structured JSON with next-best-actions and draft emails]

🔓 Unmasking pseudonymized tokens in outreach emails...

======================================================================
FINAL ACTION PLAN (unmasked, structured)
======================================================================

📊 PIPELINE SUMMARY
   Total flagged deals:  11
   CRITICAL:             4
   HIGH:                 5
   MODERATE:             2
   Value at risk:        $1,390,000

🎯 RECOMMENDED ACTIONS (11 deals)
----------------------------------------------------------------------

1. 🔴 D014 — Xi Constructors (CRITICAL, Score: 100.0)
   📋 Next Best Action: Schedule a re-engagement call with Lisa Chen at Xi Constructors within 48 hours. Reference the $2B highway project bid and offer a project management case study for construction firms.
   📧 Draft Email:
   Subject: Reconnecting on your negotiation discussion
   Hi Lisa Chen,
   ...
```

### 2.2 Run Sub-Agents in Isolation (Debugging)

**Pipeline Analyzer only:**
```bash
# Quick mode (no LLM, instant) — tests scoring logic
python test_analyzer.py

# Full ADK mode (LLM calls the tool)
python test_analyzer.py --adk
```

**Researcher only:**
```bash
# Quick mode (no LLM, instant) — tests mock DB lookups
python test_researcher.py

# Full ADK mode
python test_researcher.py --adk
```

**Research Agent Demo (end-to-end with pseudonymization):**
```bash
python demo_research.py
```

**Expected output for quick modes:**
- `test_analyzer.py`: 11 flagged deals, risk scores, summary stats, scoring sanity checks
- `test_researcher.py`: Company research for each token, 2-3 sentence summaries, security verification
- `demo_research.py`: Full flow with pseudonymization + research + security checks

---

## 3. Run via Web API (Flask)

### 3.1 Start the Local API Server
```bash
python web_app.py
```
Server starts at **http://localhost:8080**

### 3.2 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI (drag-and-drop CSV upload) |
| `POST` | `/analyze` | Upload CSV, get JSON action plan |

### 3.3 Example: Analyze Pipeline via `curl`

```bash
# Analyze the sample CSV
curl -X POST http://localhost:8080/analyze \
  -F "csv=@data/sample_pipeline.csv"
```

**Example JSON Response:**
```json
{
  "summary": {
    "flagged_count": 11,
    "critical": 4,
    "high": 5,
    "moderate": 2,
    "total_pipeline_value_at_risk": 1390000
  },
  "actions": [
    {
      "deal_id": "D014",
      "company": "Xi Constructors",
      "risk_level": "CRITICAL",
      "risk_score": 100.0,
      "days_stagnant": 90,
      "stage": "Negotiation",
      "deal_value": 250000,
      "next_best_action": "Schedule re-engagement call within 48 hours. Reference: Xi Constructors is a Construction & Infrastructure company with 5000+ employees. Xi Constructors bid on a $2B highway project in the Southeast. Key buying signals: Need project management at scale; Legacy system migration underway.",
      "draft_email": "Subject: Reconnecting on your negotiation discussion\n\nHi Lisa Chen,\n\nIt's been 90 days since we last connected about the negotiation with Xi Constructors ($250,000).\n\nBased on recent intelligence: Xi Constructors is a Construction & Infrastructure company with 5000+ employees. Xi Constructors bid on a $2B highway project in the Southeast. Key buying signals: Need project management at scale; Legacy system migration underway.\n\nI'd love to schedule a brief call to discuss how we can help. Would 48 hours work?\n\nBest regards,\nLisa Chen\nlisa@xiconstructors.com"
    }
    // ... 10 more actions
  ]
}
```

### 3.4 Use the Web UI
Open **http://localhost:8080** in your browser:
1. Drag & drop a CSV file (or click to browse)
2. Click **Analyze Pipeline**
3. Wait ~30–60 seconds
4. View results with risk badges, next-best-actions, and draft emails

---

## 4. Run with MCP Server

The MCP (Model Context Protocol) server runs as a **separate subprocess** — the ADK agent launches it automatically. You do not need to start it manually for normal operation.

### 4.1 Start MCP Server Manually (for debugging)
```bash
# Runs on stdio transport (no HTTP port)
python -m mcp_server.server
```

### 4.2 Connect Agents to MCP Server
This happens automatically in `agents/researcher.py`:
```python
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=["mcp_server/server.py"],
            env={"REVERSE_MAP_JSON": os.getenv("REVERSE_MAP_JSON", "{}")},
        ),
    ),
    tool_name_prefix="mcp",
)
```

### 4.3 MCP Tools Exposed
| Tool | Description |
|------|-------------|
| `read_pipeline_csv(file_path)` | Reads a CRM CSV and returns a formatted text table |
| `search_company_info(company_name)` | Returns mock company intel (industry, news, buying signals) |

### 4.4 Ports / Config
- **No network ports** — uses stdio transport (subprocess pipes)
- Requires `REVERSE_MAP_JSON` env var to resolve pseudonym tokens
- Output is sanitized (real company names → tokens) before returning to LLM

---

## 5. Cloud Deployment (Google Cloud Run)

### 5.1 Prerequisites
- Google Cloud project with **billing enabled**
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Docker installed (for local build) or use Cloud Build

### 5.2 Build & Deploy

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Deploy (uses Cloud Build — no local Docker needed)
gcloud run deploy pipeline-suggester \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=YOUR_ACTUAL_KEY_HERE" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300
```

### 5.3 Required Cloud Run Environment Variables
| Variable | Value |
|----------|-------|
| `GOOGLE_API_KEY` | Your actual Gemini API key |
| `STAGNANT_DAYS_THRESHOLD` | `14` (or your preferred value) |
| `PORT` | `8080` (set automatically by Cloud Run) |

### 5.4 Get Public URL & Test
After deployment, Cloud Run outputs a URL like:
```
https://pipeline-suggester-xyz123.us-central1.run.app
```

**Test the deployed API:**
```bash
curl -X POST https://pipeline-suggester-xyz123.us-central1.run.app/analyze \
  -F "csv=@data/sample_pipeline.csv"
```

**Open the Web UI:**
Visit the URL in your browser — upload a CSV and get results.

### 5.5 Cost Estimate
| Component | Estimated Cost (demo usage) |
|-----------|----------------------------|
| Cloud Run | ~$0.10–0.50/month (pay per request) |
| Cloud Build | Free tier: 120 build-minutes/day |
| Vertex AI / Gemini API | Pay per token (very cheap for demo volumes) |

---

## 6. Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ERROR: GOOGLE_API_KEY not set` | Missing or placeholder API key | Run `cp .env.example .env` and add your real key from [Google AI Studio](https://aistudio.google.com/apikey) |
| `ModuleNotFoundError: No module named 'google.adk'` | Dependencies not installed | Run `pip install -r requirements.txt` inside your activated venv |
| `FileNotFoundError: data/sample_pipeline.csv` | Running from wrong directory | Run commands from the project root (where `main.py` lives) |
| `Address already in use` (port 8080) | Another process on port 8080 | `lsof -i :8080` → kill it, or set `PORT=8081 python web_app.py` |
| `json.JSONDecodeError` in agent output | LLM returned malformed JSON | Re-run — intermittent. Check `GOOGLE_API_KEY` has quota. |
| `Permission denied` on `.venv` (Windows) | Execution policy blocks scripts | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell as Admin |
| MCP server fails to start | Python path or import issues | Ensure `mcp>=1.0.0` is installed; run `python -m mcp_server.server` manually to see errors |

---

## Quick Reference

| Task | Command |
|------|---------|
| Full pipeline (CLI) | `python main.py` |
| Full pipeline (custom CSV) | `python main.py --csv my_data.csv` |
| Web UI | `python web_app.py` → open localhost:8080 |
| Test analyzer (quick) | `python test_analyzer.py` |
| Test researcher (quick) | `python test_researcher.py` |
| Deploy to Cloud Run | `gcloud run deploy pipeline-suggester --source . --allow-unauthenticated --set-env-vars GOOGLE_API_KEY=xxx` |

---

**Need help?** Check the [README.md](README.md) for architecture details, CSV format, and extension ideas.