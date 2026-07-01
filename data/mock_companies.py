"""
Shared mock company intelligence database.

This module centralizes the mock company data so that both the MCP
server (mcp_server/server.py) and the Research Agent function tools
(agents/research_tools.py) use the same source of truth. No more
copy-pasting the same dict into two files.

In production, this would be replaced by an API client that calls
a real data provider (Crunchbase, Clearbit, LinkedIn, etc.).
Each company entry contains enough context for the Research Agent
to produce a meaningful 2-3 sentence summary and give the Action
Suggester buying signals to work with.
"""

MOCK_COMPANY_DB: dict[str, dict] = {
    "acme corp": {
        "industry": "Manufacturing",
        "employee_count": "500-1000",
        "recent_news": "Acme Corp opened a new distribution center in Texas last month.",
        "tech_stack": ["SAP", "Salesforce", "AWS"],
        "buying_signals": ["New COO hired Q1 2025", "Expanding to 3 new regions"],
    },
    "beta llc": {
        "industry": "Financial Services",
        "employee_count": "200-500",
        "recent_news": "Beta LLC announced a Series C funding round of $40M.",
        "tech_stack": ["Oracle", "HubSpot", "Azure"],
        "buying_signals": ["Post-funding growth phase", "Replacing legacy ERP"],
    },
    "gamma inc": {
        "industry": "Healthcare",
        "employee_count": "1000-5000",
        "recent_news": "Gamma Inc acquired a regional clinic network in April.",
        "tech_stack": ["Epic", "Salesforce", "GCP"],
        "buying_signals": ["Integrating acquired IT systems", "HIPAA compliance push"],
    },
    "delta ltd": {
        "industry": "Retail",
        "employee_count": "5000+",
        "recent_news": "Delta Ltd reported declining same-store sales for Q3.",
        "tech_stack": ["Shopify Plus", "SAP", "Snowflake"],
        "buying_signals": ["Digital transformation initiative", "CDO hired 2 months ago"],
    },
    "epsilon co": {
        "industry": "Technology",
        "employee_count": "50-200",
        "recent_news": "Epsilon Co launched a developer platform in beta.",
        "tech_stack": ["AWS", "Stripe", "Notion"],
        "buying_signals": ["Scaling engineering team", "Exploring enterprise sales motion"],
    },
    "zeta analytics": {
        "industry": "Data & Analytics",
        "employee_count": "100-200",
        "recent_news": "Zeta Analytics signed a deal with a Fortune 500 retailer.",
        "tech_stack": ["GCP", "BigQuery", "dbt"],
        "buying_signals": ["Growing data infra needs", "Seeking analytics partnerships"],
    },
    "eta systems": {
        "industry": "IT Services",
        "employee_count": "200-500",
        "recent_news": "Eta Systems won a government contract for IT modernization.",
        "tech_stack": ["Azure", "ServiceNow", "Jira"],
        "buying_signals": ["FedRAMP compliance required", "Scaling managed services"],
    },
    "theta global": {
        "industry": "Logistics",
        "employee_count": "1000-5000",
        "recent_news": "Theta Global expanded operations to Southeast Asia.",
        "tech_stack": ["SAP", "AWS", "Tableau"],
        "buying_signals": ["International expansion strain", "Supply chain digitization"],
    },
    "iota solutions": {
        "industry": "SaaS",
        "employee_count": "50-100",
        "recent_news": "Iota Solutions raised a $15M Series A.",
        "tech_stack": ["GCP", "Stripe", "HubSpot"],
        "buying_signals": ["Post-raise hiring spree", "Looking to upgrade CRM"],
    },
    "kappa retail": {
        "industry": "E-commerce",
        "employee_count": "10-50",
        "recent_news": "Kappa Retail launched a sustainable product line.",
        "tech_stack": ["Shopify", "Klaviyo", "Stripe"],
        "buying_signals": ["Small team, big growth plans", "Needs automation"],
    },
    "lambda health": {
        "industry": "Healthcare IT",
        "employee_count": "200-500",
        "recent_news": "Lambda Health secured a partnership with a hospital network in the Midwest.",
        "tech_stack": ["AWS", "Epic", "Terraform"],
        "buying_signals": ["Scaling cloud infrastructure", "New compliance requirements post-partnership"],
    },
    "mu dynamics": {
        "industry": "Aerospace & Defense",
        "employee_count": "500-1000",
        "recent_news": "Mu Dynamics won a DoD contract for drone navigation systems.",
        "tech_stack": ["Azure", "MATLAB", "Jira"],
        "buying_signals": ["ITAR compliance overhaul", "Expanding engineering data pipeline"],
    },
    "nu ventures": {
        "industry": "Venture Capital",
        "employee_count": "20-50",
        "recent_news": "Nu Ventures closed its third fund at $120M, focusing on B2B SaaS.",
        "tech_stack": ["Notion", "Airtable", "G Suite"],
        "buying_signals": ["Portfolio companies need shared tools", "Evaluating CRM for deal flow"],
    },
    "xi constructors": {
        "industry": "Construction & Infrastructure",
        "employee_count": "5000+",
        "recent_news": "Xi Constructors bid on a $2B highway project in the Southeast.",
        "tech_stack": ["Procore", "SAP", "Power BI"],
        "buying_signals": ["Need project management at scale", "Legacy system migration underway"],
    },
    "omicron media": {
        "industry": "Digital Media",
        "employee_count": "100-200",
        "recent_news": "Omicron Media pivoted to AI-generated content, laying off 15% of editorial staff.",
        "tech_stack": ["AWS", "WordPress", "Custom ML pipeline"],
        "buying_signals": ["AI tooling spend increasing", "Downsizing non-tech headcount"],
    },
    "pi logistics": {
        "industry": "Supply Chain & Logistics",
        "employee_count": "1000-5000",
        "recent_news": "Pi Logistics lost its largest shipping contract to a competitor in May.",
        "tech_stack": ["SAP", "Oracle TMS", "Snowflake"],
        "buying_signals": ["Urgent need to differentiate service", "Exploring AI-driven route optimization"],
    },
    "rho chemicals": {
        "industry": "Chemical Manufacturing",
        "employee_count": "5000+",
        "recent_news": "Rho Chemicals faces an EPA compliance deadline in Q3 2025.",
        "tech_stack": ["SAP", "OSIsoft PI", "Azure"],
        "buying_signals": ["Compliance deadline driving spend", "Modernizing safety reporting systems"],
    },
    "sigma retail": {
        "industry": "Retail Technology",
        "employee_count": "50-200",
        "recent_news": "Sigma Retail partnered with a POS provider to launch self-checkout kiosks.",
        "tech_stack": ["GCP", "Shopify", "Stripe"],
        "buying_signals": ["Scaling kiosk fleet management", "Needs real-time monitoring tools"],
    },
    "tau energy": {
        "industry": "Renewable Energy",
        "employee_count": "200-500",
        "recent_news": "Tau Energy secured a PPA for a 200MW solar farm in Nevada.",
        "tech_stack": ["Azure", "Python", "GIS tools"],
        "buying_signals": ["Scaling asset management platform", "Evaluating SCADA monitoring tools"],
    },
    "upsilon farm": {
        "industry": "AgriTech",
        "employee_count": "10-50",
        "recent_news": "Upsilon Farm raised a $5M seed round for precision agriculture sensors.",
        "tech_stack": ["AWS IoT", "Grafana", "PostgreSQL"],
        "buying_signals": ["Post-raise hiring", "Needs fleet management for sensor deployment"],
    },
}
