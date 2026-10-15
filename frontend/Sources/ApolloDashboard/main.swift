import Foundation
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

let defaultPort: UInt16 = 3000
let envPort = ProcessInfo.processInfo.environment["PORT"].flatMap { UInt16($0) }
let PORT: UInt16 = envPort ?? defaultPort

let dashboardHTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apollo — Financial Research Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0B0F19;
            --bg-surface: #111827;
            --bg-elevated: #1F2937;
            --border-subtle: #374151;
            --border-focus: #3B82F6;
            --text-primary: #F9FAFB;
            --text-secondary: #9CA3AF;
            --text-muted: #6B7280;
            --accent-blue: #3B82F6;
            --accent-cyan: #06B6D4;
            --accent-green: #10B981;
            --accent-amber: #F59E0B;
            --accent-red: #EF4444;
            --radius-md: 10px;
            --radius-lg: 14px;
            --shadow-card: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            padding: 2rem 1.5rem;
        }

        .container {
            max-width: 1280px;
            width: 100%;
            margin: 0 auto;
            min-width: 0;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 2rem;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-badge {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            color: white;
            font-weight: 700;
            font-size: 1.25rem;
            width: 42px;
            height: 42px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
        }

        .logo-title h1 {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .logo-title p {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .system-pill {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0.85rem;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 9999px;
            font-size: 0.85rem;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
            min-width: 0;
        }

        @media (max-width: 868px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            box-shadow: var(--shadow-card);
            transition: border-color 0.2s ease;
            max-width: 100%;
            min-width: 0;
            overflow: hidden;
        }

        .card:hover {
            border-color: #4B5563;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
        }

        .card-title {
            font-size: 1.15rem;
            font-weight: 600;
        }

        .form-group {
            margin-bottom: 1.25rem;
        }

        label {
            display: block;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        input[type="text"], textarea {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--bg-elevated);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-size: 0.95rem;
            font-family: inherit;
            outline: none;
            transition: all 0.2s ease;
        }

        input[type="text"]:focus, textarea:focus {
            border-color: var(--border-focus);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.75rem 1.5rem;
            font-size: 0.95rem;
            font-weight: 600;
            border-radius: var(--radius-md);
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
            gap: 0.5rem;
            text-decoration: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-blue), #2563EB);
            color: white;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45);
        }

        .btn-success {
            background: linear-gradient(135deg, var(--accent-green), #059669);
            color: white;
        }

        .btn-danger {
            background: linear-gradient(135deg, var(--accent-red), #DC2626);
            color: white;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-planning { background: rgba(59, 130, 246, 0.2); color: #60A5FA; }
        .status-awaiting { background: rgba(245, 158, 11, 0.2); color: #FBBF24; }
        .status-researching { background: rgba(6, 182, 212, 0.2); color: #22D3EE; }
        .status-synthesizing { background: rgba(168, 85, 247, 0.2); color: #C084FC; }
        .status-complete { background: rgba(16, 185, 129, 0.2); color: #34D399; }
        .status-incomplete { background: rgba(245, 158, 11, 0.2); color: #FBBF24; }
        .status-failed { background: rgba(239, 68, 68, 0.2); color: #F87171; }

        .log-box {
            background: #000;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #A7F3D0;
            height: 220px;
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.5;
        }

        .table-scroll-container {
            width: 100%;
            max-width: 100%;
            max-height: 480px;
            overflow-x: auto;
            overflow-y: auto;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            margin-top: 0.75rem;
            margin-bottom: 1.5rem;
            background: var(--bg-surface);
            scrollbar-width: thin;
            scrollbar-color: #4B5563 var(--bg-surface);
            position: relative;
            -webkit-overflow-scrolling: touch;
        }

        .table-scroll-container::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        .table-scroll-container::-webkit-scrollbar-track {
            background: var(--bg-surface);
            border-radius: 4px;
        }

        .table-scroll-container::-webkit-scrollbar-thumb {
            background: #374151;
            border-radius: 4px;
        }

        .table-scroll-container::-webkit-scrollbar-thumb:hover {
            background: #4B5563;
        }

        .data-table {
            width: 100%;
            min-width: 680px;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.85rem;
            table-layout: auto;
        }

        .data-table th, .data-table td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-subtle);
            vertical-align: top;
            word-break: break-word;
            overflow-wrap: anywhere;
            line-height: 1.5;
        }

        .data-table th {
            position: sticky;
            top: 0;
            z-index: 5;
            background: var(--bg-elevated);
            color: var(--text-secondary);
            font-weight: 600;
            border-bottom: 2px solid var(--border-subtle);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
        }

        .data-table tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .id-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--accent-cyan);
            background: rgba(6, 182, 212, 0.12);
            padding: 0.2rem 0.45rem;
            border-radius: 4px;
            display: inline-block;
            word-break: break-all;
        }

        a.sec-link {
            color: var(--accent-cyan);
            text-decoration: underline;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.2rem;
            word-break: break-word;
        }

        a.sec-link:hover {
            color: #67E8F9;
            text-decoration: underline;
        }

        .visual-analytics-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            min-width: 0;
            overflow: hidden;
        }

        .charts-flex-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
            margin-top: 0.75rem;
            min-width: 0;
        }

        .visual-chart-box {
            background: var(--bg-elevated);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 1rem;
            min-width: 0;
            overflow: hidden;
        }

        .cagr-badge {
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 20px;
            padding: 3px 10px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
        }

        .metric-pill {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-subtle);
            border-radius: 6px;
            padding: 0.35rem 0.65rem;
            font-size: 0.8rem;
            color: #E2E8F0;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            border-bottom: 2px solid transparent;
        }

        .tab-btn.active {
            color: var(--accent-blue);
            border-bottom-color: var(--accent-blue);
        }

        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-area">
                <div class="logo-badge">Α</div>
                <div class="logo-title">
                    <h1>Apollo Financial Research</h1>
                    <p>Plugin-Based Autonomous Research Agent · Swift Web Dashboard</p>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                <div class="user-pill" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.85rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 9999px; font-size: 0.82rem;">
                    <span style="color: var(--accent-cyan);">👤</span>
                    <span id="active-user-name" style="font-weight: 500;">Senior Financial Analyst (ANALYST)</span>
                    <span style="color: var(--text-muted); font-size: 0.75rem;">|</span>
                    <span style="color: var(--accent-amber);" id="active-workspace-badge">🏢 Default Workspace</span>
                </div>
                <div class="system-pill">
                    <div class="pulse-dot"></div>
                    <span id="api-status">Connecting to FastAPI (8000)...</span>
                </div>
            </div>
        </header>

        <div class="grid-2">
            <!-- Research Submission Card -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Initiate Company Research</h2>
                    <span class="status-badge status-planning" id="current-run-badge">READY</span>
                </div>
                <form id="research-form">
                    <div class="form-group">
                        <label for="ticker">Ticker Symbol or Company Name</label>
                        <input type="text" id="ticker" placeholder="e.g. MSFT, AAPL, NVDA" value="MSFT" required>
                    </div>
                    <div class="form-group">
                        <label for="objective">Research Scope & Objective</label>
                        <textarea id="objective" rows="3">Analyze annual financial results, revenue performance, liquidity, business segments, and principal risks.</textarea>
                    </div>
                    <button type="submit" class="btn btn-primary" id="start-btn">
                        <span>Launch Apollo Research</span>
                    </button>
                </form>
            </div>

            <!-- Execution Status & Approval Card -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Workflow Execution & Approval</h2>
                    <span id="run-id-display" style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted);">No active run</span>
                </div>

                <div id="approval-box" class="form-group hidden" style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--accent-amber); border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
                    <h3 style="color: var(--accent-amber); font-size: 0.95rem; margin-bottom: 0.5rem;">Human Approval Checkpoint</h3>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                        Apollo has resolved the issuer and generated the research itinerary. Review and authorize retrieval.
                    </p>
                    <div style="display: flex; gap: 0.5rem;">
                        <button type="button" class="btn btn-success" id="approve-btn" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Approve Itinerary</button>
                        <button type="button" class="btn btn-danger" id="reject-btn" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Reject Plan</button>
                    </div>
                </div>

                <div class="log-box" id="workflow-log">Ready. Submit an issuer ticker to begin research.</div>
            </div>
        </div>

        <!-- Research Details Card -->
        <div class="card" id="details-card">
            <div style="display: flex; gap: 1rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1rem; overflow-x: auto;">
                <button class="tab-btn active" onclick="switchTab('itinerary-tab', this)">Research Itinerary</button>
                <button class="tab-btn" onclick="switchTab('evidence-tab', this)">Evidence & Sources</button>
                <button class="tab-btn" onclick="switchTab('report-tab', this)">Report & PDF</button>
                <button class="tab-btn" onclick="switchTab('events-tab', this)">⚡ Corporate Events & Insiders</button>
            </div>

            <!-- Itinerary Tab -->
            <div id="itinerary-tab">
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">Proposed research sections and question-level coverage tracking:</p>
                <div id="itinerary-content" style="font-size: 0.9rem;">No itinerary planned yet.</div>
            </div>

            <!-- Evidence Tab -->
            <div id="evidence-tab" class="hidden">
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">Primary SEC EDGAR filings and extracted XBRL/narrative evidence:</p>
                <div id="evidence-content">No evidence retrieved yet.</div>
            </div>

            <!-- Report Tab -->
            <div id="report-tab" class="hidden">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h3 style="font-size: 1.1rem;">Generated Financial Research Report</h3>
                    <a id="download-pdf-btn" href="#" class="btn btn-primary hidden" download>
                        Download PDF Report
                    </a>
                </div>
                <div id="report-content" style="background: var(--bg-elevated); padding: 1.5rem; border-radius: 8px; line-height: 1.7; font-size: 0.9rem;">
                    Report generation pending.
                </div>
            </div>

            <!-- Events & Insiders Tab -->
            <div id="events-tab" class="hidden">
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">SEC Form 8-K material disclosures, Form 4 insider trading activity, and forward management guidance:</p>
                <div id="events-content" style="font-size: 0.9rem;">No material events or insider trades loaded yet.</div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = "http://localhost:8000";
        let activeRunId = null;
        let pollTimer = null;

        function log(msg) {
            const el = document.getElementById("workflow-log");
            const time = new Date().toLocaleTimeString();
            el.innerText += `[${time}] ${msg}\\n`;
            el.scrollTop = el.scrollHeight;
        }

        async function checkHealth() {
            try {
                const res = await fetch(`${API_BASE}/health`);
                if (res.ok) {
                    document.getElementById("api-status").innerText = "FastAPI Backend Connected";
                } else {
                    document.getElementById("api-status").innerText = "API Offline";
                }
            } catch (e) {
                document.getElementById("api-status").innerText = "API Disconnected";
            }
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll("#itinerary-tab, #evidence-tab, #report-tab, #events-tab").forEach(el => el.classList.add("hidden"));
            document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
            document.getElementById(tabId).classList.remove("hidden");
            btn.classList.add("active");
        }

        document.getElementById("research-form").addEventListener("submit", async (e) => {
            e.preventDefault();
            const ticker = document.getElementById("ticker").value.trim();
            const objective = document.getElementById("objective").value.trim();
            const btn = document.getElementById("start-btn");

            btn.disabled = true;
            log(`Initiating research request for "${ticker}"...`);

            try {
                const res = await fetch(`${API_BASE}/api/runs`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ ticker_or_name: ticker, objective: objective })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Failed to start run");
                }

                const data = await res.json();
                activeRunId = data.run.run_id;
                document.getElementById("run-id-display").innerText = `Run ID: ${activeRunId}`;
                updateRunStatus(data.run.status);

                log(`Run created: ${activeRunId}. Issuer resolved to CIK ${data.run.cik} (${data.run.company_name}).`);
                log(`Itinerary proposed: ${data.itinerary.sections.length} sections, ${data.itinerary.questions.length} questions.`);

                renderItinerary(data.itinerary);

                // Show approval prompt
                document.getElementById("approval-box").classList.remove("hidden");

                // Start SSE stream for real-time progress
                startEventStream(activeRunId);
            } catch (err) {
                log(`Error: ${err.message}`);
                alert(`Error: ${err.message}`);
            } finally {
                btn.disabled = false;
            }
        });

        let activeEventSource = null;

        function startEventStream(runId) {
            if (activeEventSource) {
                activeEventSource.close();
            }

            log(`[SSE] Connected to real-time event stream for ${runId}`);
            activeEventSource = new EventSource(`${API_BASE}/api/runs/${runId}/events`);

            activeEventSource.onmessage = async (e) => {
                try {
                    const event = JSON.parse(e.data);
                    log(`⚡ [${event.event_type}] ${event.message}`);

                    if (event.event_type === "PLAN_PROPOSED") {
                        updateRunStatus("AWAITING_APPROVAL");
                    } else if (event.event_type === "ATHENA_RETRIEVAL_STARTED" || event.event_type === "EVIDENCE_EXTRACTED") {
                        updateRunStatus("RESEARCHING");
                    } else if (event.event_type === "SYNTHESIS_STARTED") {
                        updateRunStatus("SYNTHESIZING");
                    } else if (event.event_type === "VALIDATION_COMPLETED") {
                        updateRunStatus("VALIDATING");
                    } else if (event.event_type === "RUN_COMPLETED") {
                        updateRunStatus(event.data.status || "COMPLETE");
                        log("🎉 Workflow finished. Populating evidence and final report...");
                        await loadEvidence(runId);
                        await loadReport(runId);
                        activeEventSource.close();
                    } else if (event.event_type === "RUN_FAILED" || event.event_type === "RUN_REJECTED") {
                        updateRunStatus("FAILED");
                        activeEventSource.close();
                    }
                } catch (err) {
                    console.error("SSE parse error", err);
                }
            };

            activeEventSource.onerror = (err) => {
                console.warn("SSE stream idle or disconnected", err);
            };
        }

        document.getElementById("approve-btn").addEventListener("click", async () => {
            if (!activeRunId) return;
            log("User approved research plan. Resuming execution...");
            document.getElementById("approval-box").classList.add("hidden");

            try {
                const res = await fetch(`${API_BASE}/api/runs/${activeRunId}/approvals`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ decision: "APPROVED", async_execution: true })
                });

                const run = await res.json();
                updateRunStatus(run.status);
                log(`Async execution started: current status is ${run.status}`);
            } catch (err) {
                log(`Execution failed: ${err.message}`);
            }
        });

        document.getElementById("reject-btn").addEventListener("click", async () => {
            if (!activeRunId) return;
            log("User rejected research plan.");
            document.getElementById("approval-box").classList.add("hidden");

            await fetch(`${API_BASE}/api/runs/${activeRunId}/approvals`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ decision: "REJECTED" })
            });
            updateRunStatus("FAILED");
        });

        function updateRunStatus(status) {
            const badge = document.getElementById("current-run-badge");
            badge.innerText = status;
            badge.className = `status-badge status-${status.toLowerCase()}`;
        }

        function renderItinerary(itin) {
            let html = "";
            itin.sections.forEach(sec => {
                html += `<div style="margin-bottom: 1rem; background: var(--bg-elevated); padding: 0.85rem; border-radius: 6px;">
                    <strong>${sec.title}</strong>
                    <p style="color: var(--text-secondary); font-size: 0.8rem; margin: 0.25rem 0;">${sec.description}</p>
                    <ul style="padding-left: 1.25rem; font-size: 0.85rem;">`;
                itin.questions.filter(q => q.section_id === sec.section_id).forEach(q => {
                    html += `<li style="margin-top: 0.25rem;">[${q.status}] ${q.question}</li>`;
                });
                html += `</ul></div>`;
            });
            document.getElementById("itinerary-content").innerHTML = html;
        }

        function formatMarkdownLinks(text) {
            if (!text) return "";
            // Replace markdown links [label](url) with clickable HTML links
            let res = text.replace(/\\[([^\\]]+)\\]\\(((?:https?:\\/\\/)[^\\s\\)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="sec-link"><u>$1</u></a>');
            // Format newlines
            return res.replace(/\\n/g, '<br>');
        }

        async function loadEvidence(runId) {
            try {
                const res = await fetch(`${API_BASE}/api/runs/${runId}/evidence`);
                if (!res.ok) return;
                const data = await res.json();

                let html = `<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; margin-bottom: 0.5rem;">
                    <h4 style="color: var(--accent-cyan); font-size: 1rem;">Primary SEC EDGAR Sources (${data.total_sources})</h4>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">Scroll horizontally / vertically as needed</span>
                </div>
                <div class="table-scroll-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width: 25%;">Source ID</th>
                                <th style="width: 12%;">Form</th>
                                <th style="width: 18%;">Filing Date</th>
                                <th style="width: 18%;">Period</th>
                                <th style="width: 27%;">Official SEC Link</th>
                            </tr>
                        </thead>
                        <tbody>`;
                data.sources.forEach(s => {
                    html += `<tr>
                        <td><span class="id-badge">${s.source_id}</span></td>
                        <td><strong style="color: var(--text-primary);">${s.form_type}</strong></td>
                        <td>${s.filed_at}</td>
                        <td>${s.period_of_report}</td>
                        <td><a class="sec-link" href="${s.source_url}" target="_blank" rel="noopener noreferrer">↗ Open SEC Filing</a></td>
                    </tr>`;
                });
                html += `</tbody></table></div>`;

                html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; margin-bottom: 0.5rem;">
                    <h4 style="color: var(--accent-blue); font-size: 1rem;">Verified Evidence Records (${data.total_evidence})</h4>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">Extracted facts, XBRL data & narrative disclosures</span>
                </div>
                <div class="table-scroll-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width: 24%;">Evidence ID</th>
                                <th style="width: 24%;">Locator & Source</th>
                                <th style="width: 38%;">Verified Excerpt / Value</th>
                                <th style="width: 14%;">Status</th>
                            </tr>
                        </thead>
                        <tbody>`;
                data.evidence.forEach(e => {
                    let text = "";
                    if (e.value !== null) {
                        text = `<strong>${e.fact_name}</strong>: ${Number(e.value).toLocaleString()} ${e.unit || ''} <span style="color: var(--text-muted); font-size: 0.8rem;">(${e.fiscal_period || e.period_end || ''})</span>`;
                    } else if (e.excerpt) {
                        text = e.excerpt.length > 250 ? e.excerpt.substring(0, 250) + '...' : e.excerpt;
                    } else {
                        text = "Disclosed";
                    }

                    const secLink = e.source_url 
                        ? `<br><a class="sec-link" href="${e.source_url}" target="_blank" rel="noopener noreferrer" style="font-size: 0.75rem; margin-top: 0.35rem;">↗ View in SEC Filing</a>`
                        : '';

                    html += `<tr>
                        <td><span class="id-badge">${e.evidence_id}</span></td>
                        <td><strong>${e.locator}</strong>${secLink}</td>
                        <td>${text}</td>
                        <td><span class="status-badge status-${(e.validation_status || 'valid').toLowerCase()}">${e.validation_status}</span></td>
                    </tr>`;
                });
                html += `</tbody></table></div>`;
                document.getElementById("evidence-content").innerHTML = html;
            } catch (e) {
                console.error(e);
            }
        }

        function renderRevenueChartSVG(chartData) {
            if (!chartData || !chartData.labels || !chartData.values_in_billions || chartData.labels.length === 0) return '';
            const labels = chartData.labels;
            const values = chartData.values_in_billions;
            const unit = chartData.unit || 'USD Billions';
            const cagr = chartData.cagr_formatted || '';
            const maxVal = Math.max(...values, 1);

            const svgWidth = 440;
            const svgHeight = 170;
            const padX = 35;
            const padTop = 28;
            const padBottom = 32;
            const chartH = svgHeight - padTop - padBottom;
            const chartW = svgWidth - (padX * 2);

            const n = labels.length;
            const barW = Math.min(48, chartW / (n * 1.8));
            const gap = (chartW - (n * barW)) / (n + 1);

            let barsSVG = '';
            labels.forEach((lbl, i) => {
                const val = values[i];
                const barH = Math.max(8, (val / maxVal) * chartH);
                const x = padX + gap + i * (barW + gap);
                const y = padTop + (chartH - barH);

                barsSVG += `
                    <g>
                        <rect x="${x}" y="${y}" width="${barW}" height="${barH}" rx="4" fill="url(#revGrad)" stroke="#38BDF8" stroke-width="1" />
                        <text x="${x + barW / 2}" y="${y - 6}" text-anchor="middle" fill="#F1F5F9" font-size="10" font-weight="600">$${val}B</text>
                        <text x="${x + barW / 2}" y="${padTop + chartH + 16}" text-anchor="middle" fill="#94A3B8" font-size="10">${lbl}</text>
                    </g>
                `;
            });

            return `
                <div class="visual-chart-box">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <h5 style="color: var(--text-primary); font-size: 0.95rem; margin: 0;">${chartData.title || 'Annual Revenue Trend'}</h5>
                        ${cagr ? `<span class="cagr-badge">CAGR: ${cagr}</span>` : ''}
                    </div>
                    <svg viewBox="0 0 ${svgWidth} ${svgHeight}" style="width: 100%; height: auto; max-height: 190px; overflow: visible;">
                        <defs>
                            <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.9" />
                                <stop offset="100%" stop-color="#1E40AF" stop-opacity="0.6" />
                            </linearGradient>
                        </defs>
                        <line x1="${padX - 5}" y1="${padTop + chartH}" x2="${svgWidth - padX + 5}" y2="${padTop + chartH}" stroke="#334155" stroke-width="1" />
                        ${barsSVG}
                    </svg>
                </div>
            `;
        }

        function renderMarginChartSVG(chartData) {
            if (!chartData || !chartData.labels || !chartData.operating_margins || chartData.labels.length === 0) return '';
            const labels = chartData.labels;
            const opMargins = chartData.operating_margins;
            const netMargins = chartData.net_margins || [];

            const allM = [...opMargins, ...netMargins].filter(v => v !== null && v !== undefined);
            const maxVal = Math.max(...allM, 50);

            const svgWidth = 440;
            const svgHeight = 170;
            const padX = 35;
            const padTop = 28;
            const padBottom = 32;
            const chartH = svgHeight - padTop - padBottom;
            const chartW = svgWidth - (padX * 2);

            const n = labels.length;
            const groupW = Math.min(65, chartW / (n * 1.5));
            const barW = groupW / 2.3;
            const gap = (chartW - (n * groupW)) / (n + 1);

            let barsSVG = '';
            labels.forEach((lbl, i) => {
                const gx = padX + gap + i * (groupW + gap);
                const opVal = opMargins[i];
                const netVal = netMargins[i];

                if (opVal !== null && opVal !== undefined) {
                    const opH = Math.max(5, (opVal / maxVal) * chartH);
                    const opY = padTop + (chartH - opH);
                    barsSVG += `
                        <rect x="${gx}" y="${opY}" width="${barW}" height="${opH}" rx="3" fill="#38BDF8" />
                        <text x="${gx + barW / 2}" y="${opY - 5}" text-anchor="middle" fill="#38BDF8" font-size="9" font-weight="600">${opVal}%</text>
                    `;
                }

                if (netVal !== null && netVal !== undefined) {
                    const netH = Math.max(5, (netVal / maxVal) * chartH);
                    const netY = padTop + (chartH - netH);
                    barsSVG += `
                        <rect x="${gx + barW + 3}" y="${netY}" width="${barW}" height="${netH}" rx="3" fill="#34D399" />
                        <text x="${gx + barW + 3 + barW / 2}" y="${netY - 5}" text-anchor="middle" fill="#34D399" font-size="9" font-weight="600">${netVal}%</text>
                    `;
                }

                barsSVG += `<text x="${gx + groupW / 2}" y="${padTop + chartH + 16}" text-anchor="middle" fill="#94A3B8" font-size="10">${lbl}</text>`;
            });

            return `
                <div class="visual-chart-box">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <h5 style="color: var(--text-primary); font-size: 0.95rem; margin: 0;">Profit Margin Trajectory</h5>
                        <div style="display: flex; gap: 0.75rem; font-size: 0.75rem;">
                            <span style="display: flex; align-items: center; gap: 4px; color: #38BDF8;"><span style="display:inline-block; width:8px; height:8px; background:#38BDF8; border-radius:2px;"></span> Operating</span>
                            <span style="display: flex; align-items: center; gap: 4px; color: #34D399;"><span style="display:inline-block; width:8px; height:8px; background:#34D399; border-radius:2px;"></span> Net Margin</span>
                        </div>
                    </div>
                    <svg viewBox="0 0 ${svgWidth} ${svgHeight}" style="width: 100%; height: auto; max-height: 190px; overflow: visible;">
                        <line x1="${padX - 5}" y1="${padTop + chartH}" x2="${svgWidth - padX + 5}" y2="${padTop + chartH}" stroke="#334155" stroke-width="1" />
                        ${barsSVG}
                    </svg>
                </div>
            `;
        }

        function renderCapitalStructureSVG(chartData, ratios) {
            if (!chartData || !chartData.labels || !chartData.values_in_billions || chartData.labels.length < 2) return '';
            const labels = chartData.labels;
            const values = chartData.values_in_billions;
            const maxVal = Math.max(...values, 1);

            const colors = ['#38BDF8', '#F87171', '#34D399'];
            let barsHTML = '';

            labels.forEach((lbl, i) => {
                const val = values[i];
                const pct = Math.min(100, Math.max(6, (val / maxVal) * 100));
                const color = colors[i % colors.length];
                barsHTML += `
                    <div style="margin-bottom: 0.65rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.25rem;">
                            <span style="color: var(--text-secondary);">${lbl}</span>
                            <strong style="color: #F1F5F9;">$${val}B</strong>
                        </div>
                        <div style="background: var(--bg-surface); border-radius: 4px; height: 9px; width: 100%; overflow: hidden;">
                            <div style="background: ${color}; width: ${pct}%; height: 100%; border-radius: 4px; transition: width 0.5s ease;"></div>
                        </div>
                    </div>
                `;
            });

            const debtAssets = ratios && ratios.debt_to_assets ? ratios.debt_to_assets.formatted : null;
            const cashLiab = ratios && ratios.cash_to_liabilities ? ratios.cash_to_liabilities.formatted : null;

            return `
                <div class="visual-chart-box">
                    <h5 style="color: var(--text-primary); font-size: 0.95rem; margin-bottom: 0.75rem;">Capital Structure & Liquidity</h5>
                    ${barsHTML}
                    <div style="display: flex; gap: 1rem; margin-top: 0.85rem; border-top: 1px solid var(--border-subtle); padding-top: 0.5rem; font-size: 0.8rem;">
                        ${debtAssets ? `<div><span style="color: var(--text-muted);">Debt-to-Assets:</span> <strong style="color: #38BDF8;">${debtAssets}</strong></div>` : ''}
                        ${cashLiab ? `<div><span style="color: var(--text-muted);">Cash Coverage:</span> <strong style="color: #34D399;">${cashLiab}</strong></div>` : ''}
                    </div>
                </div>
            `;
        }

        async function loadReport(runId) {
            try {
                const res = await fetch(`${API_BASE}/api/runs/${runId}/report`);
                if (!res.ok) return;
                const report = await res.json();

                let html = `<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
                    <h2>${report.company_name} (${report.ticker})</h2>
                    <span class="status-badge status-${report.status.toLowerCase()}">${report.status}</span>
                </div>
                <p style="color: var(--text-secondary); margin-bottom: 1.25rem; font-size: 0.85rem;">
                    CIK: <strong>${report.cik}</strong> &nbsp;|&nbsp; Generated: ${new Date(report.generated_at).toLocaleString()}
                </p>`;

                // Primary Sources & SEC Filings Cited Table
                if (report.bibliography && report.bibliography.length > 0) {
                    html += `<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 1.5rem;">
                        <h4 style="color: var(--accent-cyan); margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span>📑 Primary Sources & SEC Filings Cited (${report.bibliography.length})</span>
                        </h4>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                            All material factual claims trace directly to the following official SEC EDGAR filings:
                        </p>
                        <div class="table-scroll-container" style="max-height: 220px; margin-bottom: 0;">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Source ID</th>
                                        <th>Form</th>
                                        <th>Filing Date</th>
                                        <th>Period</th>
                                        <th>Official SEC EDGAR Link</th>
                                    </tr>
                                </thead>
                                <tbody>`;
                    report.bibliography.forEach(b => {
                        html += `<tr>
                            <td><span class="id-badge">${b.source_id}</span></td>
                            <td><strong>${b.form_type}</strong></td>
                            <td>${b.filed_at}</td>
                            <td>${b.period_of_report}</td>
                            <td><a class="sec-link" href="${b.source_url}" target="_blank" rel="noopener noreferrer">↗ Open SEC Filing (${b.accession_number})</a></td>
                        </tr>`;
                    });
                    html += `</tbody></table></div></div>`;
                }

                // Executive Summary
                html += `<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem;">
                    <h4 style="color: var(--text-primary); font-size: 1.05rem; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
                        Executive Summary
                    </h4>
                    <div style="font-size: 0.9rem; line-height: 1.7; color: #E5E7EB;">
                        ${formatMarkdownLinks(report.executive_summary)}
                    </div>
                </div>`;

                // Visual Analytics & Multi-Year Trends (Phase 2 Charts)
                if (report.financial_metrics && report.financial_metrics.charts) {
                    const fm = report.financial_metrics;
                    const ch = fm.charts || {};
                    const revChartHTML = renderRevenueChartSVG(ch.revenue_trend);
                    const marginChartHTML = renderMarginChartSVG(ch.margin_trend);
                    const capChartHTML = renderCapitalStructureSVG(ch.capital_structure, fm.ratios);

                    if (revChartHTML || marginChartHTML || capChartHTML) {
                        html += `<div class="visual-analytics-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
                                <h4 style="color: var(--accent-cyan); font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; margin: 0;">
                                    <span>📊 Financial Trends & Interactive Visual Analytics</span>
                                </h4>
                                <span style="font-size: 0.8rem; color: var(--text-muted);">Deterministic XBRL Multi-Period Modeling</span>
                            </div>`;

                        if (fm.summary_highlights && fm.summary_highlights.length > 0) {
                            html += `<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">`;
                            fm.summary_highlights.forEach(h => {
                                html += `<span class="metric-pill">📈 ${h}</span>`;
                            });
                            html += `</div>`;
                        }

                        html += `<div class="charts-flex-grid">
                            ${revChartHTML}
                            ${marginChartHTML}
                            ${capChartHTML}
                        </div>
                        </div>`;
                    }
                }

                // Sections
                report.sections.forEach((sec, idx) => {
                    html += `<div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem;">
                        <h3 style="color: var(--accent-blue); font-size: 1.15rem; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
                            ${sec.title}
                        </h3>
                        <div style="font-size: 0.9rem; line-height: 1.7; color: #E5E7EB; margin-bottom: 1rem;">
                            ${formatMarkdownLinks(sec.narrative)}
                        </div>`;

                    if (sec.claims && sec.claims.length > 0) {
                        html += `<details style="margin-top: 1rem; background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.6rem 0.85rem;">
                            <summary style="cursor: pointer; font-size: 0.85rem; color: var(--accent-cyan); font-weight: 600;">
                                🔍 View ${sec.claims.length} Verified Claims & Direct SEC Citations
                            </summary>
                            <div class="table-scroll-container" style="max-height: 250px; margin-top: 0.75rem; margin-bottom: 0.25rem;">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th style="width: 22%;">Claim ID</th>
                                            <th style="width: 48%;">Factual Claim Statement</th>
                                            <th style="width: 15%;">Type</th>
                                            <th style="width: 15%;">Direct SEC Citation</th>
                                        </tr>
                                    </thead>
                                    <tbody>`;
                        sec.claims.forEach(c => {
                            const link = (c.source_urls && c.source_urls.length > 0)
                                ? `<a class="sec-link" href="${c.source_urls[0]}" target="_blank" rel="noopener noreferrer">↗ SEC Source</a>`
                                : '<span style="color: var(--text-muted); font-size: 0.75rem;">Verified</span>';
                            html += `<tr>
                                <td><span class="id-badge">${c.claim_id}</span></td>
                                <td>${c.text}</td>
                                <td><span style="font-size: 0.75rem; color: var(--text-secondary);">${c.claim_type}</span></td>
                                <td>${link}</td>
                            </tr>`;
                        });
                        html += `</tbody></table></div></details>`;
                    }

                    html += `</div>`;
                });

                document.getElementById("report-content").innerHTML = html;

                // Render Events & Insiders tab
                const fm = report.financial_metrics || {};
                const matEvents = fm.material_events || [];
                const insiderTxs = fm.insider_transactions || [];
                const guidance = fm.management_guidance || [];

                let eventsHTML = '';

                // 1. Material Events (Form 8-K)
                if (matEvents.length > 0) {
                    eventsHTML += `
                        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem;">
                            <h4 style="color: var(--accent-amber); font-size: 1.05rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                                <span>📄</span> Recent Material Corporate Disclosures (SEC Form 8-K)
                            </h4>
                            <div class="table-scroll-container" style="max-height: 280px;">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th style="width: 15%;">Filing Date</th>
                                            <th style="width: 55%;">Event Title & Substantive Summary</th>
                                            <th style="width: 15%;">Items</th>
                                            <th style="width: 15%;">SEC Filing Link</th>
                                        </tr>
                                    </thead>
                                    <tbody>`;
                    matEvents.forEach(ev => {
                        const itemsStr = (ev.items && ev.items.length > 0)
                            ? ev.items.map(it => `<span class="id-badge">${it.item_number}</span>`).join(" ")
                            : '<span class="id-badge">8-K</span>';
                        eventsHTML += `
                            <tr>
                                <td><span style="font-size: 0.8rem; color: var(--text-secondary);">${ev.date || 'Recent'}</span></td>
                                <td>
                                    <div style="font-weight: 600; color: #F1F5F9; margin-bottom: 0.2rem;">${ev.title}</div>
                                    <div style="font-size: 0.8rem; color: #94A3B8;">${ev.summary}</div>
                                </td>
                                <td>${itemsStr}</td>
                                <td><a class="sec-link" href="${ev.url}" target="_blank" rel="noopener noreferrer">↗ View 8-K</a></td>
                            </tr>
                        `;
                    });
                    eventsHTML += `</tbody></table></div></div>`;
                }

                // 2. Insider Trading (Form 4)
                if (insiderTxs.length > 0) {
                    eventsHTML += `
                        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem;">
                            <h4 style="color: var(--accent-cyan); font-size: 1.05rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                                <span>👤</span> Insider Trading & Executive Ownership (SEC Form 4)
                            </h4>
                            <div class="table-scroll-container" style="max-height: 280px;">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th style="width: 25%;">Reporting Owner & Role</th>
                                            <th style="width: 15%;">Date</th>
                                            <th style="width: 15%;">Action</th>
                                            <th style="width: 15%;">Shares</th>
                                            <th style="width: 15%;">Price / Total Value</th>
                                            <th style="width: 15%;">SEC Source</th>
                                        </tr>
                                    </thead>
                                    <tbody>`;
                    insiderTxs.forEach(tx => {
                        const isBuy = tx.code === "P" || tx.type === "Purchase";
                        const badgeStyle = isBuy
                            ? "background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4);"
                            : "background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.4);";
                        eventsHTML += `
                            <tr>
                                <td>
                                    <div style="font-weight: 600; color: #F1F5F9;">${tx.owner}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">${tx.role}</div>
                                </td>
                                <td><span style="font-size: 0.8rem; color: var(--text-secondary);">${tx.date}</span></td>
                                <td><span style="padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; ${badgeStyle}">${tx.type} (${tx.code})</span></td>
                                <td><span style="font-family: monospace;">${Number(tx.shares).toLocaleString()}</span></td>
                                <td>
                                    <div style="font-weight: 600;">$${Number(tx.total_value).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">$${Number(tx.price).toFixed(2)} / share</div>
                                </td>
                                <td><a class="sec-link" href="${tx.url}" target="_blank" rel="noopener noreferrer">↗ Form 4</a></td>
                            </tr>
                        `;
                    });
                    eventsHTML += `</tbody></table></div></div>`;
                }

                // 3. Management Guidance
                if (guidance.length > 0) {
                    eventsHTML += `
                        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.25rem;">
                            <h4 style="color: var(--accent-blue); font-size: 1.05rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                                <span>🎙️</span> Management Guidance & Executive Commentary
                            </h4>
                            <div style="display: grid; gap: 0.75rem;">`;
                    guidance.forEach(g => {
                        eventsHTML += `
                            <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.85rem;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                                    <span style="font-weight: 600; color: var(--accent-cyan); font-size: 0.9rem;">${g.topic}</span>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">Attributed to ${g.speaker}</span>
                                </div>
                                <div style="font-size: 0.85rem; color: #E2E8F0; line-height: 1.5;">${g.text}</div>
                            </div>
                        `;
                    });
                    eventsHTML += `</div></div>`;
                }

                if (!eventsHTML) {
                    eventsHTML = '<p style="color: var(--text-secondary); font-size: 0.9rem;">No Form 8-K material events, Form 4 insider trades, or guidance statements recorded for this run.</p>';
                }
                const eventsContainer = document.getElementById("events-content");
                if (eventsContainer) eventsContainer.innerHTML = eventsHTML;

                // PDF download button
                const pdfBtn = document.getElementById("download-pdf-btn");
                pdfBtn.href = `${API_BASE}/api/runs/${runId}/report/pdf`;
                pdfBtn.classList.remove("hidden");

                // Switch to Report Tab
                switchTab('report-tab', document.querySelectorAll('.tab-btn')[2]);
            } catch (e) {
                console.error(e);
            }
        }

        async function loadUserProfileAndWorkspaces() {
            try {
                const res = await fetch(`${API_BASE}/api/auth/me`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.user) {
                        const userEl = document.getElementById("active-user-name");
                        if (userEl) userEl.innerText = `${data.user.name} (${data.user.role})`;
                    }
                    if (data.workspaces && data.workspaces.length > 0) {
                        const wsBadge = document.getElementById("active-workspace-badge");
                        const activeWs = data.workspaces.find(w => w.workspace_id === data.user.active_workspace_id) || data.workspaces[0];
                        if (wsBadge) wsBadge.innerText = `🏢 ${activeWs.name}`;
                    }
                }
            } catch (e) {
                console.warn("Could not load user profile:", e);
            }
        }

        setInterval(checkHealth, 5000);
        checkHealth();
        loadUserProfileAndWorkspaces();
    </script>
</body>
</html>
"""

final class SwiftHTTPServer: Sendable {
    private let port: UInt16

    init(port: UInt16) {
        self.port = port
    }

    func start() {
        let serverSocket = socket(AF_INET, SOCK_STREAM, 0)
        guard serverSocket >= 0 else {
            fatalError("Failed to create socket")
        }

        var opt: Int32 = 1
        setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, &opt, socklen_t(MemoryLayout<Int32>.size))
        #if canImport(Darwin)
        setsockopt(serverSocket, SOL_SOCKET, SO_REUSEPORT, &opt, socklen_t(MemoryLayout<Int32>.size))
        #endif

        var serverAddr = sockaddr_in()
        serverAddr.sin_family = sa_family_t(AF_INET)
        serverAddr.sin_port = in_port_t(self.port.bigEndian)
        serverAddr.sin_addr.s_addr = in_addr_t(0) // INADDR_ANY

        let bindResult = withUnsafePointer(to: &serverAddr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(serverSocket, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }

        guard bindResult >= 0 else {
            print("❌ Error: Could not bind port \(self.port). It may already be in use by another process.")
            print("   You can free port \(self.port) using: lsof -ti :\(self.port) | xargs kill -9")
            print("   Or set an alternative port: PORT=3001 swift run ApolloDashboard")
            exit(1)
        }

        guard listen(serverSocket, 20) >= 0 else {
            print("❌ Error: Failed to listen on socket.")
            exit(1)
        }

        print("=================================================================")
        print(" Apollo Swift Web Dashboard running on http://localhost:\(self.port)")
        print(" Communicating with FastAPI Backend on http://localhost:8000")
        print("=================================================================")

        while true {
            var clientAddr = sockaddr_in()
            var clientAddrLen = socklen_t(MemoryLayout<sockaddr_in>.size)
            let clientSocket = withUnsafeMutablePointer(to: &clientAddr) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    accept(serverSocket, $0, &clientAddrLen)
                }
            }

            guard clientSocket >= 0 else { continue }

            DispatchQueue.global(qos: .userInitiated).async {
                self.handleClient(clientSocket: clientSocket)
            }
        }
    }

    private func handleClient(clientSocket: Int32) {
        defer { close(clientSocket) }

        var buffer = [UInt8](repeating: 0, count: 2048)
        let bytesRead = read(clientSocket, &buffer, buffer.count)
        guard bytesRead > 0 else { return }

        let htmlData = dashboardHTML.data(using: .utf8) ?? Data()
        let responseHeader = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: \(htmlData.count)\r\nConnection: close\r\n\r\n"

        if let headerData = responseHeader.data(using: .utf8) {
            _ = headerData.withUnsafeBytes { write(clientSocket, $0.baseAddress, headerData.count) }
        }
        _ = htmlData.withUnsafeBytes { write(clientSocket, $0.baseAddress, htmlData.count) }
    }
}

let server = SwiftHTTPServer(port: PORT)
server.start()
