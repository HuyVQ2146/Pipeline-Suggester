# Demo Outputs — Quick Mode Tests (No API Key Required)

## Quick Start

```bash
# 1. Activate virtual environment
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. Run quick-mode tests (no API key needed)
python test_analyzer.py
python test_researcher.py
python demo_research.py
```

---

This document describes the expected output of the three quick-mode test scripts that run **without any LLM calls or API keys**. These tests exercise the deterministic Python logic directly.

---

## 1. `python test_analyzer.py`

**Purpose**: Tests the Pipeline Analyzer scoring logic directly — parses CSV, flags stagnant deals (≥14 days inactive), computes risk scores, and validates the scoring function.

### Output Structure

```
======================================================================
QUICK MODE — Direct function call (no LLM, no API key)
======================================================================

📂 Analyzing: data/sample_pipeline.csv
📅 Reference date: 2025-06-30
⏱  Stagnant threshold: 14 days

──────────────────────────────────────────────────
📊  SUMMARY
──────────────────────────────────────────────────
   Total deals in pipeline:  20
   Flagged as stagnant:      11
     ├─ CRITICAL (≥80):      4
     ├─ HIGH (50-79):        5
     └─ MODERATE (<50):      2
   Pipeline value at risk:   $1,390,000

──────────────────────────────────────────────────
🚨  FLAGGED DEALS (sorted by risk score, highest first)
──────────────────────────────────────────────────

  1. 🔴 D014 — Xi Constructors
     Contact:  Lisa Chen <lisa@xiconstructors.com>
     Stage:    Negotiation
     Value:    $250,000
     Idle:     90 days (since 2025-04-01)
     Owner:    Diana
     Risk:     100.0/100 → CRITICAL

  2. 🔴 D017 — Rho Chemicals
     Contact:  Victor Brown <victor@rhochemicals.com>
     Stage:    Negotiation
     Value:    $175,000
     Idle:     107 days (since 2025-03-15)
     Owner:    Bob
     Risk:     96.3/100 → CRITICAL

  3. 🔴 D004 — Delta Ltd
     Contact:  Carol White <carol@deltaltd.com>
     Stage:    Negotiation
     Value:    $200,000
     Idle:     81 days (since 2025-04-10)
     Owner:    Charlie
     Risk:     95.3/100 → CRITICAL

  4. 🔴 D008 — Theta Global
     Contact:  Grace Kim <grace@thetaglobal.com>
     Stage:    Negotiation
     Value:    $180,000
     Idle:     60 days (since 2025-05-01)
     Owner:    Alice
     Risk:     81.3/100 → CRITICAL

  5. 🟠 D006 — Zeta Analytics
     Contact:  Eve Davis <eve@zetaanalytics.com>
     Stage:    Proposal
     Value:    $95,000
     Idle:     94 days (since 2025-03-28)
     Owner:    Bob
     Risk:     79.6/100 → HIGH

  6. 🟠 D016 — Pi Logistics
     Contact:  Emma Wilson <emma@pilogistics.com>
     Stage:    Proposal
     Value:    $110,000
     Idle:     56 days (since 2025-05-05)
     Owner:    Charlie
     Risk:     63.9/100 → HIGH

  7. 🟠 D012 — Mu Dynamics
     Contact:  Sarah Lee <sarah@mudynamics.com>
     Stage:    Negotiation
     Value:    $88,000
     Idle:     46 days (since 2025-05-15)
     Owner:    Charlie
     Risk:     60.4/100 → HIGH

  8. 🟠 D002 — Beta LLC
     Contact:  Jane Doe <jane@betallc.com>
     Stage:    Proposal
     Value:    $85,000
     Idle:     41 days (since 2025-05-20)
     Owner:    Bob
     Risk:     52.3/100 → HIGH

  9. 🟠 D009 — Iota Solutions
     Contact:  Henry Park <henry@iotasolutions.com>
     Stage:    Qualification
     Value:    $60,000
     Idle:     76 days (since 2025-04-15)
     Owner:    Diana
     Risk:     52.0/100 → HIGH

  10. 🟡 D019 — Tau Energy
     Contact:  Nina Garcia <nina@tauenergy.com>
     Stage:    Proposal
     Value:    $92,000
     Idle:     33 days (since 2025-05-28)
     Owner:    Alice
     Risk:     49.1/100 → MODERATE

  11. 🟡 D015 — Omicron Media
     Contact:  Raj Patel <raj@omicronmedia.com>
     Stage:    Discovery
     Value:    $55,000
     Idle:     20 days (since 2025-06-10)
     Owner:    Alice
     Risk:     26.8/100 → MODERATE


──────────────────────────────────────────────────
🧪  SCORING SANITY CHECKS
──────────────────────────────────────────────────
  ✅  15d stagnant, $30,000, Qualification → score=15.5, level=MODERATE (expected MODERATE)
  ✅  45d stagnant, $100,000, Proposal → score=56.6, level=HIGH (expected HIGH)
  ✅  91d stagnant, $250,000, Negotiation → score=100.0, level=CRITICAL (expected CRITICAL)

All sanity checks passed! ✅
```

### Key Fields Explained

| Field | Description |
|-------|-------------|
| **Total deals** | All rows in the CSV (20 in sample) |
| **Flagged** | Deals with `Last_Activity_Date` ≥ 14 days before reference date |
| **Risk Score (0-100)** | Weighted formula: `days_stagnant * 0.5 + deal_value_weight + stage_weight` |
| **Risk Level** | CRITICAL ≥80, HIGH 50-79, MODERATE <50 |
| **Value at risk** | Sum of `Deal_Value` for all flagged deals |

### Scoring Formula (from `agents/pipeline_tools.py:_compute_risk_score`)

```python
# Base score from days stagnant (capped at 100)
days_score = min(days_stagnant * 0.8, 100)

# Deal value weight
if deal_value >= 200_000: value_score = 30
elif deal_value >= 100_000: value_score = 20
elif deal_value >= 50_000: value_score = 10
else: value_score = 5

# Stage weight
stage_weights = {"Negotiation": 25, "Proposal": 15, "Qualification": 10, "Discovery": 5}
stage_score = stage_weights.get(stage, 0)

risk_score = min(days_score + value_score + stage_score, 100)
```

---

## 2. `python test_researcher.py`

**Purpose**: Tests the Research Agent tools directly — pseudonymizes flagged deals, resolves tokens to real company names for mock DB lookups, runs single and bulk research, and verifies no PII leaks into tool output.

### Output Structure

```
======================================================================
QUICK MODE - Direct function call (no LLM, no API key)
======================================================================

  Step 1: Analyzing pipeline to find stagnant deals...

  Found 11 stagnant deals out of 20 total.

  Step 2: Pseudonymizing sensitive fields...

  Pseudonymized 11 deals.
  Reverse mapping (tokens -> real names, for internal use): {'[COMPANY_1]': 'Xi Constructors', '[CONTACT_1]': 'Lisa Chen', '[EMAIL_1]': 'lisa@xiconstructors.com'} ... (33 total entries)

  Step 3: Testing single-company research...

  ------------------------------------------------------------
  
  Calling research_company("[COMPANY_1]")
  [Internally resolves to: "Xi Constructors"]

    Industry:     Construction & Infrastructure
    Employees:    5000+
    Recent News:  [COMPANY_1] bid on a $2B highway project in the Southeast.
    Tech Stack:   Procore, SAP, Power BI
    Buying Signals: Need project management at scale; Legacy system migration underway

  ------------------------------------------------------------
  
  Calling research_company("[COMPANY_2]")
  [Internally resolves to: "Rho Chemicals"]

    Industry:     Chemical Manufacturing
    Employees:    5000+
    Recent News:  [COMPANY_2] faces an EPA compliance deadline in Q3 2025.
    Tech Stack:   SAP, OSIsoft PI, Azure
    Buying Signals: Compliance deadline driving spend; Modernizing safety reporting systems

  ------------------------------------------------------------
  
  Calling research_company("[COMPANY_3]")
  [Internally resolves to: "Delta Ltd"]

    Industry:     Retail
    Employees:    5000+
    Recent News:  [COMPANY_3] reported declining same-store sales for Q3.
    Tech Stack:   Shopify Plus, SAP, Snowflake
    Buying Signals: Digital transformation initiative; CDO hired 2 months ago

  ------------------------------------------------------------

  Step 4: Testing bulk research (all flagged companies)...

  ------------------------------------------------------------
  
  Calling bulk_research with 11 companies...

  Requested: 11  |  Found: 11  |  Not found: 0

  [OK] [COMPANY_1] -> Xi Constructors
       [COMPANY_1] is a Construction & Infrastructure company with 5000+ employees. [COMPANY_1] bid on a $2B highway project in the Southeast. Key buying signals: Need project management at scale; Legacy system migration underway.

  [OK] [COMPANY_2] -> Rho Chemicals
       [COMPANY_2] is a Chemical Manufacturing company with 5000+ employees. [COMPANY_2] faces an EPA compliance deadline in Q3 2025. Key buying signals: Compliance deadline driving spend; Modernizing safety reporting systems.

  [OK] [COMPANY_3] -> Delta Ltd
       [COMPANY_3] is a Retail company with 5000+ employees. [COMPANY_3] reported declining same-store sales for Q3. Key buying signals: Digital transformation initiative; CDO hired 2 months ago.

  [OK] [COMPANY_4] -> Theta Global
       [COMPANY_4] is a Logistics company with 1000-5000 employees. [COMPANY_4] expanded operations to Southeast Asia. Key buying signals: International expansion strain; Supply chain digitization.

  [OK] [COMPANY_5] -> Zeta Analytics
       [COMPANY_5] is a Data & Analytics company with 100-200 employees. [COMPANY_5] signed a deal with a Fortune 500 retailer. Key buying signals: Growing data infra needs; Seeking analytics partnerships.

  [OK] [COMPANY_6] -> Pi Logistics
       [COMPANY_6] is a Supply Chain & Logistics company with 1000-5000 employees. [COMPANY_6] lost its largest shipping contract to a competitor in May. Key buying signals: Urgent need to differentiate service; Exploring AI-driven route optimization.

  [OK] [COMPANY_7] -> Mu Dynamics
       [COMPANY_7] is a Aerospace & Defense company with 500-1000 employees. [COMPANY_7] won a DoD contract for drone navigation systems. Key buying signals: ITAR compliance overhaul; Expanding engineering data pipeline.

  [OK] [COMPANY_8] -> Beta LLC
       [COMPANY_8] is a Financial Services company with 200-500 employees. [COMPANY_8] announced a Series C funding round of $40M. Key buying signals: Post-funding growth phase; Replacing legacy ERP.

  [OK] [COMPANY_9] -> Iota Solutions
       [COMPANY_9] is a SaaS company with 50-100 employees. [COMPANY_9] raised a $15M Series A. Key buying signals: Post-raise hiring spree; Looking to upgrade CRM.

  [OK] [COMPANY_10] -> Tau Energy
       [COMPANY_10] is a Renewable Energy company with 200-500 employees. [COMPANY_10] secured a PPA for a 200MW solar farm in Nevada. Key buying signals: Scaling asset management platform; Evaluating SCADA monitoring tools.

  [OK] [COMPANY_11] -> Omicron Media
       [COMPANY_11] is a Digital Media company with 100-200 employees. [COMPANY_11] pivoted to AI-generated content, laying off 15% of editorial staff. Key buying signals: AI tooling spend increasing; Downsizing non-tech headcount.

  ------------------------------------------------------------

  Step 5: Testing not-found company...

  Status:   not_found
  Message:  No research data available for company: 'Nonexistent Corp LLC'

  ------------------------------------------------------------
  Step 6: Security verification...

  [OK] No PII leaked into research tool output.

  All security checks passed!
```

### Key Security Features Demonstrated

| Check | Description |
|-------|-------------|
| **Pseudonymization** | Real company/contact/email → tokens (`[COMPANY_N]`, `[CONTACT_N]`, `[EMAIL_N]`) |
| **Reverse mapping** | Used internally for DB lookups only — never sent to LLM |
| **Output sanitization** | Company names in `recent_news` and `summary` fields show tokens, not real names |
| **PII verification** | Asserts no real emails, contact names, or company names appear in tool JSON output |
| **Not-found handling** | Graceful fallback for unknown companies |

### Mock Company DB Fields (from `data/mock_companies.py`)

Each company entry contains:
- `industry` — e.g., "Construction & Infrastructure"
- `employee_count` — e.g., "5000+", "1000-5000", "200-500", etc.
- `recent_news` — One sentence with pseudonymized company token
- `tech_stack` — List of technologies
- `buying_signals` — List of 2-3 signals relevant to sales outreach

---

## 3. `python demo_research.py`

**Purpose**: End-to-end demo of the Research Agent flow — combines pipeline analysis, pseudonymization, bulk research, and security verification in a single readable output. This is the most complete "quick mode" test.

### Output Structure

```
======================================================================
RESEARCH AGENT — END-TO-END DEMO
======================================================================

[Step 1] Analyzing pipeline for stagnant deals...

   Total deals in pipeline: 20
   Stagnant threshold: 14 days
   Reference date: 2025-06-30
   [!] Flagged stagnant deals: 11
   [*] Pipeline value at risk: $1,390,000
      CRITICAL: 4  |  HIGH: 5  |  MODERATE: 2

[Step 2] Pseudonymizing sensitive fields (Company, Contact, Email)...

   Pseudonymized 11 deals
   Token count: 33 (tokens -> real values for internal lookup)
   Example mappings:
      [COMPANY_1] → Xi Constructors
      [CONTACT_1] → Lisa Chen
      [EMAIL_1] → lisa@xiconstructors.com
      [COMPANY_2] → Rho Chemicals
      [CONTACT_2] → Victor Brown
      ... and 28 more

[Step 3] Configuring research tools with reverse mapping...

[Step 4] Researching 11 flagged companies...

   Calling bulk_research()...
   [OK] Requested: 11  |  Found: 11  |  Not found: 0

======================================================================
RESEARCH FINDINGS — 2-3 Sentence Summaries Per Company
======================================================================

1. [COMPANY_1]  (→ Xi Constructors)
   Risk Level: CRITICAL  |  Score: 100.0  |  Days Stagnant: 90
   Industry:     Construction & Infrastructure
   Employees:    5000+
   Recent News:  [COMPANY_1] bid on a $2B highway project in the Southeast.
   Tech Stack:   Procore, SAP, Power BI
   Buying Signals: Need project management at scale; Legacy system migration underway

   [SUMMARY] [COMPANY_1] is a Construction & Infrastructure company with 5000+ employees. [COMPANY_1] bid on a $2B highway project in the Southeast. Key buying signals: Need project management at scale; Legacy system migration underway.

2. [COMPANY_2]  (→ Rho Chemicals)
   Risk Level: CRITICAL  |  Score: 96.3  |  Days Stagnant: 107
   Industry:     Chemical Manufacturing
   Employees:    5000+
   Recent News:  [COMPANY_2] faces an EPA compliance deadline in Q3 2025.
   Tech Stack:   SAP, OSIsoft PI, Azure
   Buying Signals: Compliance deadline driving spend; Modernizing safety reporting systems

   [SUMMARY] [COMPANY_2] is a Chemical Manufacturing company with 5000+ employees. [COMPANY_2] faces an EPA compliance deadline in Q3 2025. Key buying signals: Compliance deadline driving spend; Modernizing safety reporting systems.

3. [COMPANY_3]  (→ Delta Ltd)
   Risk Level: CRITICAL  |  Score: 95.3  |  Days Stagnant: 81
   Industry:     Retail
   Employees:    5000+
   Recent News:  [COMPANY_3] reported declining same-store sales for Q3.
   Tech Stack:   Shopify Plus, SAP, Snowflake
   Buying Signals: Digital transformation initiative; CDO hired 2 months ago

   [SUMMARY] [COMPANY_3] is a Retail company with 5000+ employees. [COMPANY_3] reported declining same-store sales for Q3. Key buying signals: Digital transformation initiative; CDO hired 2 months ago.

... (continues for all 11 companies)

======================================================================
SECURITY VERIFICATION
======================================================================
  [OK] No PII leaked into research tool output.
  [OK] Company names in news/signals sanitized to tokens.
  [OK] Contact names and emails never reach the LLM.
  [OK] Reverse mapping used only for internal DB lookups.

======================================================================
DEMO COMPLETE — Research Agent ready for production use
======================================================================
```

### What Makes This Demo Special

1. **Single command** runs the full flow: analyze → pseudonymize → research → verify
2. **Readable format** with aligned columns and clear section headers
3. **Risk context** — each research entry shows the deal's risk level, score, and days stagnant
4. **Security audit** — explicit verification that no PII leaks into tool output
5. **Token transparency** — shows both the pseudonymized token (`[COMPANY_1]`) and the real name (`→ Xi Constructors`) for debugging

---

## Comparison Table

| Aspect | `test_analyzer.py` | `test_researcher.py` | `demo_research.py` |
|--------|-------------------|---------------------|-------------------|
| **Focus** | Scoring logic | Research tools + security | End-to-end flow |
| **Pipeline analysis** | ✅ Full | ✅ Full | ✅ Full |
| **Pseudonymization** | ❌ (raw data shown) | ✅ Full demo | ✅ Full demo |
| **Single research** | ❌ | ✅ 3 companies | ❌ |
| **Bulk research** | ❌ | ✅ All 11 | ✅ All 11 |
| **Security verification** | ❌ | ✅ Comprehensive | ✅ Summary |
| **Not-found test** | ❌ | ✅ | ❌ |
| **Output format** | Structured table | Step-by-step log | Aligned columns + summary |
| **Best for** | Debugging scoring | Debugging research tools | Quick overview / demo |

---

## Running the Tests

```bash
# Activate venv first
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Run any quick-mode test (no API key needed)
python test_analyzer.py
python test_researcher.py
python demo_research.py

# Run with ADK agent (requires GOOGLE_API_KEY in .env)
python test_analyzer.py --adk
python test_researcher.py --adk

# Full pipeline with LLM (requires GOOGLE_API_KEY)
python main.py
```

---

## Sample Data

The tests use `data/sample_pipeline.csv` with 20 deals across various stages, owners, and activity dates. The reference date is fixed at `2025-06-30` for reproducible results.

Key sample companies in the mock DB (`data/mock_companies.py`):
- Xi Constructors (Construction)
- Rho Chemicals (Chemical Manufacturing)
- Delta Ltd (Retail)
- Theta Global (Logistics)
- Zeta Analytics (Data & Analytics)
- Pi Logistics (Supply Chain)
- Mu Dynamics (Aerospace & Defense)
- Beta LLC (Financial Services)
- Iota Solutions (SaaS)
- Tau Energy (Renewable Energy)
- Omicron Media (Digital Media)