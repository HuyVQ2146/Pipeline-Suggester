#!/usr/bin/env python3
"""
Pipeline Suggester — Web UI for Demo

A simple Flask web interface to upload a CRM CSV and get AI-powered
re-engagement actions and draft emails.

Run locally:
    python web_app.py

Then open http://localhost:8080 in your browser.
"""

import os
import json
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify, render_template_string

# Import the pipeline logic
from utils.anonymizer import Pseudonymizer
from agents.pipeline_tools import analyze_pipeline
from agents.research_tools import bulk_research, set_reverse_mapping
import pandas as pd


app = Flask(__name__)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Suggester — AI Pipeline Analysis</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 30px 20px;
            background: #fafafa;
            color: #212121;
            line-height: 1.6;
        }
        .container { background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        h1 {
            color: #1976d2;
            margin-bottom: 8px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 16px; }

        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s;
            cursor: pointer;
        }
        .upload-area:hover, .upload-area.dragover {
            border-color: #1976d2;
            background: #e3f2fd;
        }
        .upload-icon { font-size: 48px; margin-bottom: 16px; }
        .upload-text { font-size: 16px; color: #666; }
        .upload-hint { font-size: 13px; color: #999; margin-top: 8px; }

        button#analyzeBtn {
            background: #1976d2;
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            width: 100%;
            transition: background 0.2s;
        }
        button#analyzeBtn:hover:not(:disabled) { background: #1565c0; }
        button#analyzeBtn:disabled { background: #bdbdbd; cursor: not-allowed; }

        .loader {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #e0e0e0;
            border-top-color: #1976d2;
            border-radius: 50%;
            width: 48px;
            height: 48px;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text { color: #666; font-size: 15px; }

        .error {
            background: #ffebee;
            color: #c62828;
            padding: 16px;
            border-radius: 8px;
            margin-top: 20px;
        }

        .results { margin-top: 30px; }
        .summary-card {
            background: #e3f2fd;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }
        .summary-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            margin-top: 12px;
        }
        .stat {
            background: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            min-width: 140px;
        }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
        .stat-value { font-size: 24px; font-weight: 600; color: #1976d2; margin-top: 4px; }
        .stat-value.critical { color: #d32f2f; }
        .stat-value.high { color: #f57c00; }
        .stat-value.moderate { color: #388e3c; }
        .stat-value.value { color: #1976d2; }

        .deal-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 24px;
            .
            margin-bottom: 20px;
            transition: box-shadow 0.2s;
        }
        .deal-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .deal-card.critical { border-left: 5px solid #d32f2f; }
        .deal-card.high { border-left: 5px solid #f57c00; }
        .deal-card.moderate { border-left: 5px solid #388e3c; }

        .deal-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .deal-title { font-size: 18px; font-weight: 600; color: #212121; }
        .risk-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }
        .risk-critical { background: #ffebee; color: #c62828; }
        .risk-high { background: #fff3e0; color: #e65100; }
        .risk-moderate { background: #e8f5e9; color: #2e7d32; }

        .deal-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 16px;
            font-size: 14px;
            color: #555;
        }
        .meta-item { display: flex; align-items: center; gap: 6px; }
        .meta-label { color: #888; font-size: 12px; }
        .meta-value { font-weight: 500; }

        .section-title {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #666;
            margin: 20px 0 8px;
        }

        .action-text, .email-text {
            background: #f5f5f5;
            padding: 16px;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.7;
        }
        .email-text {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace;
            font-size: 13px;
            white-space: pre-wrap;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #999;
            font-size: 13px;
        }

        @media (max-width: 600px) {
            .deal-meta { flex-direction: column; gap: 8px; }
            .summary-stats { justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 Pipeline Suggester</h1>
        <p class="subtitle">Upload your CRM pipeline CSV to get AI-powered re-engagement actions and draft outreach emails.</p>

        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📁</div>
            <div class="upload-text">Drag & drop your pipeline CSV here<br>or click to browse</div>
            <div class="upload-hint">Required columns: Deal_ID, Company_Name, Contact_Name, Contact_Email, Deal_Value, Stage, Last_Activity_Date, Owner</div>
            <input type="file" id="csvInput" name="csv" accept=".csv" style="display:none;">
        </div>

        <button id="analyzeBtn" disabled>Analyze Pipeline</button>

        <div class="loader" id="loader">
            <div class="spinner"></div>
            <div class="loader-text">🤖 Running multi-agent pipeline analysis...<br><span style="font-size:13px;color:#999;">This takes ~30-60 seconds</span></div>
        </div>

        <div class="error" id="errorMsg" style="display:none;"></div>

        <div class="results" id="results" style="display:none;"></div>
    </div>

    <div class="footer">
        Built with Google ADK (Agent Development Kit) + MCP (Model Context Protocol) + FastMCP
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const csvInput = document.getElementById('csvInput');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const loader = document.getElementById('loader');
        const errorMsg = document.getElementById('errorMsg');
        const results = document.getElementById('results');

        let selectedFile = null;

        // Drag and drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
        });

        uploadArea.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file && file.name.endsWith('.csv')) handleFile(file);
        }, false);

        uploadArea.addEventListener('click', () => csvInput.click());
        csvInput.addEventListener('change', (e) => {
            if (e.target.files[0]) handleFile(e.target.files[0]);
        });

        function handleFile(file) {
            if (!file.name.endsWith('.csv')) {
                showError('Please select a CSV file');
                return;
            }
            selectedFile = file;
            uploadArea.innerHTML = `
                <div class="upload-icon">✅</div>
                <div class="upload-text"><strong>${file.name}</strong></div>
                <div class="upload-hint">${(file.size/1024).toFixed(1)} KB</div>
            `;
            analyzeBtn.disabled = false;
            errorMsg.style.display = 'none';
        }

        analyzeBtn.addEventListener('click', async () => {
            if (!selectedFile) return;

            analyzeBtn.disabled = true;
            loader.style.display = 'block';
            results.style.display = 'none';
            errorMsg.style.display = 'none';

            const formData = new FormData();
            formData.append('csv', selectedFile);

            try {
                const res = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await res.json();
                loader.style.display = 'none';

                if (data.error) {
                    showError(data.error);
                    analyzeBtn.disabled = false;
                    return;
                }

                renderResults(data);
                results.style.display = 'block';
            } catch (err) {
                loader.style.display = 'none';
                showError('Network error: ' + err.message);
                analyzeBtn.disabled = false;
            }
        });

        function showError(msg) {
            errorMsg.textContent = msg;
            errorMsg.style.display = 'block';
        }

        function renderResults(data) {
            const riskClass = (level) => level.toLowerCase();

            let html = `
                <div class="summary-card">
                    <h3 style="margin:0 0 12px;color:#1976d2;">📊 Pipeline Summary</h3>
                    <div class="summary-stats">
                        <div class="stat">
                            <div class="stat-label">Flagged Deals</div>
                            <div class="stat-value">${data.summary.flagged_count}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">CRITICAL</div>
                            <div class="stat-value critical">${data.summary.critical}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">HIGH</div>
                            <div class="stat-value high">${data.summary.high}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">MODERATE</div>
                            <div class="stat-value moderate">${data.summary.moderate}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Value at Risk</div>
                            <div class="stat-value value">$${data.summary.total_pipeline_value_at_risk.toLocaleString()}</div>
                        </div>
                    </div>
                </div>
            `;

            data.actions.forEach((action, i) => {
                const rc = riskClass(action.risk_level);
                html += `
                    <div class="deal-card ${rc}">
                        <div class="deal-header">
                            <span class="deal-title">${action.deal_id} — ${action.company}</span>
                            <span class="risk-badge risk-${rc}">${action.risk_level} (${action.risk_score})</span>
                        </div>
                        <div class="deal-meta">
                            <div class="meta-item"><span class="meta-label">Days Stagnant:</span> <span class="meta-value">${action.days_stagnant}</span></div>
                            <div class="meta-item"><span class="meta-label">Stage:</span> <span class="meta-value">${action.stage}</span></div>
                            <div class="meta-item"><span class="meta-label">Deal Value:</span> <span class="meta-value">$${action.deal_value.toLocaleString()}</span></div>
                        </div>
                        <div class="section-title">📋 Next Best Action</div>
                        <div class="action-text">${action.next_best_action}</div>
                        <div class="section-title">📧 Draft Email</div>
                        <div class="email-text">${escapeHtml(action.draft_email)}</div>
                    </div>
                `;
            });

            results.innerHTML = html;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""


async def analyze_pipeline_async(csv_path: str) -> dict:
    """Run the full pipeline analysis: analyze -> research -> suggest actions."""

    # Step 1: Read CSV
    df = pd.read_csv(csv_path)

    # Step 2: Pseudonymize sensitive fields
    pseudo = Pseudonymizer()
    masked_rows = [
        pseudo.pseudonymize_row(row.to_dict())
        for _, row in df.iterrows()
    ]

    # Build reverse mapping for research tools
    reverse_map = pseudo.get_reverse_mapping()
    set_reverse_mapping(reverse_map)

    # Step 3: Analyze pipeline
    result = analyze_pipeline(
        csv_path=csv_path,
        stagnant_threshold_days=14,
        reference_date="2025-06-30",
    )
    analysis = json.loads(result)
    flagged_deals = analysis["flagged_deals"]

    # Step 4: Research companies
    company_tokens = [d["Company_Name"] for d in flagged_deals]
    research_json = bulk_research(json.dumps(company_tokens))
    research = json.loads(research_json)

    # Build company info map by token
    company_info = {}
    for r in research["results"]:
        company_info[r["company"]] = r

    # Step 5: Generate action plans
    actions = []
    for deal in flagged_deals:
        token = deal["Company_Name"]
        info = company_info.get(token, {})
        summary = info.get("summary", "No research available")

        # Determine urgency based on risk level
        urgency_map = {"CRITICAL": "48 hours", "HIGH": "1 week", "MODERATE": "2 weeks"}
        urgency = urgency_map.get(deal["Risk_Level"], "2 weeks")

        next_action = (
            f"Schedule re-engagement call within {urgency}. "
            f"Reference: {summary}"
        )

        draft_email = (
            f"Subject: Reconnecting on your {deal['Stage'].lower()} discussion\n\n"
            f"Hi {pseudo.unmask(deal['Contact_Name'])},\n\n"
            f"It's been {deal['Days_Stagnant']} days since we last connected "
            f"about the {deal['Stage']} with {pseudo.unmask(token)} "
            f"(${deal['Deal_Value']:,.0f}).\n\n"
            f"Based on recent intelligence: {summary}\n\n"
            f"I'd love to schedule a brief call to discuss how we can help. "
            f"Would {urgency} work?\n\n"
            f"Best regards,\n"
            f"{pseudo.unmask(deal['Contact_Name'])}\n"
            f"{pseudo.unmask(deal['Contact_Email'])}"
        )

        actions.append({
            "deal_id": deal["Deal_ID"],
            "company": pseudo.unmask(token),
            "risk_level": deal["Risk_Level"],
            "risk_score": deal["Risk_Score"],
            "days_stagnant": deal["Days_Stagnant"],
            "stage": deal["Stage"],
            "deal_value": deal["Deal_Value"],
            "next_best_action": next_action,
            "draft_email": draft_email,
        })

    return {
        "summary": analysis["summary"],
        "actions": actions
    }


@app.route("/")
def index():
    return HTML_TEMPLATE


@app.route("/analyze", methods=["POST"])
def analyze():
    if 'csv' not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400

    file = request.files['csv']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400

    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
            file.save(tmp)
            tmp_path = tmp.name

        # Run async analysis
        result = asyncio.run(analyze_pipeline_async(tmp_path))

        # Cleanup
        os.unlink(tmp_path)

        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Pipeline Suggester web UI on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)