# Apollo — Plugin-Based Autonomous Financial Research Agent

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Swift 6.0](https://img.shields.io/badge/swift-6.0-orange.svg)](https://www.swift.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Apollo is an enterprise-grade, autonomous financial research platform designed for equity research analysts, institutional investors, hedge funds, and investment committees.**
> It investigates publicly traded companies using official US Securities and Exchange Commission (SEC EDGAR) filings, corporate earnings call transcripts, Form 8-K material events, and Form 4 insider transactions—generating institutional-grade PDF research reports and a real-time reactive Swift web dashboard with **100% deterministic citation provenance**.

---

## Table of Contents

1. [What This Project Is About](#1-what-this-project-is-about)
   - [The Problem with Conventional Financial AI](#the-problem-with-conventional-financial-ai)
   - [The Apollo Solution](#the-apollo-solution)
   - [The Anti-Hallucination & Provenance Invariant](#the-anti-hallucination--provenance-invariant)
2. [System Architecture](#2-system-architecture)
   - [Multi-Agent Triad (Apollo, Athena, Hermes)](#multi-agent-triad)
   - [End-to-End Architecture Diagram](#end-to-end-architecture-diagram)
3. [Core Capabilities & Built-in Features](#3-core-capabilities--built-in-features)
   - [Real-Time Workflow Streaming & SSE (Phase 1)](#real-time-workflow-streaming--sse-phase-1)
   - [Deterministic Financial Analytics & Vector Charts (Phase 2)](#deterministic-financial-analytics--vector-charts-phase-2)
   - [Durable SQLite Persistence & Multi-Tenancy (Phase 3)](#durable-sqlite-persistence--multi-tenancy-phase-3)
   - [Extended SEC & Alternate Data Sources (Phase 4)](#extended-sec--alternate-data-sources-phase-4)
4. [First-Class Plugin Ecosystem](#4-first-class-plugin-ecosystem)
   - [Plugin Contract Matrix](#plugin-contract-matrix)
   - [Creating Custom Plugins](#creating-custom-plugins)
5. [Getting Started & Local Installation](#5-getting-started--local-installation)
   - [Prerequisites](#prerequisites)
   - [Step-by-Step Setup](#step-by-step-setup)
   - [Starting the FastAPI Backend](#step-1-start-the-fastapi-backend)
   - [Starting the Swift Web Dashboard](#step-2-start-the-swift-web-dashboard)
6. [License](#6-license)

---

## 1. What This Project Is About

### The Problem with Conventional Financial AI

Large Language Models (LLMs) used in finance suffer from critical flaws that prevent institutional adoption:
- **Hallucinations & Fabricated Figures:** Models generate convincing financial metrics that differ subtly or wildly from audited statements.
- **Untraceable Claims & Dead Links:** Generic AI summaries assert trends, growth figures, or risk factors without providing traceable proof back to primary filings.
- **Uncontrolled Autonomy:** Autonomous web agents loop indefinitely, browse unverified blog posts, and hallucinate conclusions when source data is missing.
- **Opaque Reasoning:** Research conclusions cannot be audited, verified, or submitted to compliance and investment committees.

### The Apollo Solution

**Apollo transforms corporate filings into verifiable investment intelligence.** It replaces black-box guessing with an auditable, multi-agent research pipeline anchored directly to official SEC EDGAR disclosures:

```text
Research Question
       │
       ▼
[Athena Retrieval] ──> US SEC EDGAR (10-K, 10-Q, 8-K, Form 4, XBRL Facts)
       │
       ▼
Evidence Record (UUID, CIK, Accession Number, Canonical URL, Verbatim Excerpt)
       │
       ▼
Deterministic Financial Validator (Decimal Math, Period Alignment, Currency Check)
       │
       ▼
Two-Stage Synthesis (Section Drafts ──> Assembly & Cross-Section Coherence)
       │
       ▼
Final Deliverables (Publication-Grade Vector PDF + Real-Time Swift Web Dashboard)
```

### The Anti-Hallucination & Provenance Invariant

Apollo guarantees institutional compliance through non-negotiable architectural invariants:

1. **Deterministic Logic Governs Completion:** Only strict, deterministic Python application code can mark a research run as `COMPLETE`. No LLM prompt or plugin can declare success if requirements are unmet.
2. **100% Required Question Coverage:** A research run is strictly marked `INCOMPLETE` if any required research question lacks a validated primary-source evidence record. Gaps are explicitly disclosed in the final report.
3. **End-to-End Citation Provenance:** 100% of material claims in the synthesized report link directly to an immutable `EvidenceRecord` containing the issuer's CIK, accession number, fiscal period, and clickable canonical SEC EDGAR URL.
4. **Preservation of Numeric Context:** All financial figures preserve exact `Decimal` precision, unit definitions (e.g. USD Millions), reporting period start/end dates, and fiscal periods (`FY2024`, `Q3 2024`). Floating-point approximations are prohibited.
5. **Human-in-the-Loop Governance:** Apollo pauses at a formal **Human Approval Gate** after generating its research plan, allowing analysts to review, adjust, or approve research itineraries before retrieval commences.

---

## 2. System Architecture

Apollo is built around a specialized three-agent team orchestrated via a stateful **LangGraph** execution graph:

### Multi-Agent Triad

- **Apollo (The Orchestrator):**
  Normalizes company tickers to official SEC CIK numbers, creates tailored 5-section research itineraries, enforces autonomy budgets (default maximum of 3 follow-up rounds), and gates workflow progression behind human sign-off.
- **Athena (The Research Agent):**
  Executes high-throughput queries against SEC EDGAR endpoints, retrieves annual Form 10-Ks, quarterly Form 10-Qs, material event Form 8-Ks, insider trading Form 4 filings, and XBRL Company Facts, dispatching raw documents to registered document extractors.
- **Hermes (The Evidence & Gap Analyzer):**
  Performs question-by-question evidence coverage analysis, verifies provenance, discovers information gaps, and orchestrates targeted retrieval iterations until full coverage is achieved or the autonomy budget is exhausted.

### End-to-End Architecture Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   EQUITY RESEARCH ANALYST / USER                       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                   HTTP REST / SSE │ (Port 3000 -> Port 8000)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                NATIVE SWIFT WEB DASHBOARD (PORT 3000)                  │
│  ├── Executive Summary & Key Investment Findings                       │
│  ├── Dynamic Evidence Table (Scrollable & Sizable Provenance Grid)     │
│  ├── Financial Ratios & Multi-Year CAGR Vector SVG Charts              │
│  ├── Corporate Events (8-K Taxonomy) & Insider Trading Radar (Form 4)   │
│  └── Live SSE Terminal Logs with Step-by-Step Progress Bar             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND ENGINE (PORT 8000)                   │
│  ├── Auth & Multi-Tenancy (HMAC-SHA256 JWT, Bearer Tokens, API Keys)   │
│  ├── EventBroadcaster (Pub/Sub with In-Memory Replay Buffer)           │
│  └── Durable SQLite Persistence (WAL Mode, Thread-Safe RunStore)        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│              APOLLO LANGGRAPH WORKFLOW ORCHESTRATOR                    │
│  ├── 1. Request Normalization & Ticker-to-CIK Resolution               │
│  ├── 2. Research Itinerary Generation (5 Core Research Questions)      │
│  ├── 3. [HUMAN APPROVAL GATE - Pause / Resume via Thread ID]           │
│  ├── 4. Athena Retrieval (SEC EDGAR, XBRL Facts, 8-K, Form 4)          │
│  ├── 5. Extractors (HTML Chunkers & XBRL Facts Plugins)                │
│  ├── 6. Financial Analytics Engine (YoY Growth, Margins, Debt, CAGR)   │
│  ├── 7. Hermes Evidence Coverage & Bounded Gap Recovery Loop           │
│  ├── 8. Stage 1: Independent Section-Specific Synthesis (Gemma 4)      │
│  ├── 9. Stage 2: Final Report Assembly & Citation Link Verification    │
│  └── 10. ReportLab PDF Exporter (Vector Charts & Clickable Citations)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Capabilities & Built-in Features

### Real-Time Workflow Streaming & SSE (Phase 1)
- **High-Performance Pub/Sub:** The backend features an asynchronous `EventBroadcaster` that captures every sub-agent transition, retrieval event, and synthesis milestone.
- **Replay Buffer:** Late-joining dashboard connections automatically receive historical events, preventing missed log updates.
- **Server-Sent Events (SSE):** `GET /api/runs/{run_id}/events` delivers zero-latency updates to the Swift dashboard.

### Deterministic Financial Analytics & Vector Charts (Phase 2)
- **Deterministic Math Engine:** The `FinancialAnalyticsPlugin` computes year-over-year revenue growth, operating margins, net margins, and debt-to-equity ratios with exact `Decimal` precision.
- **Multi-Year CAGR:** Computes Compound Annual Growth Rates across 3-to-5 year horizons with trend classification (Accelerating, Moderate, Decelerating).
- **Dual Vector Visualizations:**
  - **Swift Web Dashboard:** Native responsive SVG vector charts with interactive tooltips and crisp resolution on Retina displays.
  - **ReportLab PDF:** Embedded publication-grade vector bar charts and ratio tables rendered natively in exported research reports.

### Durable SQLite Persistence & Multi-Tenancy (Phase 3)
- **SQLite WAL Mode:** Full database persistence across application restarts using SQLite in Write-Ahead Logging (`PRAGMA journal_mode=WAL`) mode.
- **Thread-Safe Repository:** Dedicated `RunStore` managing `ResearchRunRecord`, `EvidenceRecordEntity`, and `AuditLogRecord` entities.
- **Cryptographic Security:** HMAC-SHA256 JWT-compatible bearer tokens and API keys with tamper detection and role-based permissions (`analyst`, `admin`).
- **Multi-Tenant Workspace Scoping:** Runs, evidence, and audit logs are strictly isolated by workspace ID (`ws_default`, `ws_alpha`, etc.) with HTTP 403 authorization enforcement.

### Extended SEC & Alternate Data Sources (Phase 4)
- **Material Corporate Events (Form 8-K):** The `SECMaterialEventsPlugin` retrieves and classifies unscheduled corporate disclosures using official SEC Item codes:
  - *Item 1.01:* Material Definitive Agreements
  - *Item 2.02:* Results of Operations and Financial Condition
  - *Item 5.02:* Departure/Election of Directors & Principal Officers
  - *Item 7.01:* Regulation FD Disclosures
- **Insider Trading Radar (Form 4):** Automatically extracts legal insider transactions for corporate officers and directors, tracking acquisition/disposition codes (`P` purchase, `S` sale, `A` award), share counts, and transaction prices.
- **Corporate Transcripts & Guidance:** The `ManagementTranscriptsPlugin` extracts executive commentary and forward-looking guidance targets (FY revenue, operating margin expectations) directly from earnings call disclosures.
- **Swift Dashboard Dedicated Tab:** A dedicated **⚡ Corporate Events & Insiders** view displays scrollable 8-K events, Form 4 insider trading cards, and executive guidance summaries.

---

## 4. First-Class Plugin Ecosystem

Apollo is designed from the ground up as a modular, plugin-based architecture. Every core component is defined as a Python `Protocol` and registered with a `PluginManifest`:

### Plugin Contract Matrix

| Plugin ID | Type | Class | Capabilities |
|---|---|---|---|
| `sec_edgar` | `source_connector` | `SecEdgarPlugin` | `sec.issuer.resolve`, `sec.filings.search`, `sec.filings.fetch`, `sec.facts.fetch` |
| `sec_material_events` | `source_connector` | `SECMaterialEventsPlugin` | `sec.8k.search`, `sec.8k.fetch`, `sec.form4.search`, `sec.form4.fetch` |
| `management_transcripts` | `source_connector` | `ManagementTranscriptsPlugin` | `transcripts.fetch`, `transcripts.guidance.extract` |
| `filing_html` | `document_extractor` | `FilingHtmlExtractorPlugin` | `documents.html.extract` |
| `xbrl_facts` | `document_extractor` | `XbrlFactsExtractorPlugin` | `documents.xbrl.extract` |
| `financial_analytics` | `evidence_validator` | `FinancialAnalyticsPlugin` | `analytics.ratios.compute`, `analytics.trends.cagr` |
| `financial_checks` | `evidence_validator` | `FinancialChecksPlugin` | `evidence.financial.validate` |
| `financial_synthesis` | `synthesis_strategy` | `FinancialSynthesisPlugin` | `synthesis.sections.generate` |
| `ollama` | `model_provider` | `OllamaModelProviderPlugin` | `model.text.generate`, `model.structured.generate` (Gemma 4) |
| `pdf` | `report_exporter` | `PdfReportExporterPlugin` | `report.pdf.export` (ReportLab Vector PDF) |

### Creating Custom Plugins

To add a new data source or export format:
1. Inherit from the typed `Protocol` in `app/plugins/contracts.py`.
2. Define a `PluginManifest` with `plugin_id`, `version`, `api_version="1.0"`, and declared `capabilities`.
3. Implement the required contract methods.
4. Register the plugin via `plugin_registry.register(MyPlugin())`.

```python
from app.plugins.manifest import PluginManifest
from app.models.sources import SourceQuery, SourceDocumentRef

class BloombergConnectorPlugin:
    manifest = PluginManifest(
        plugin_id="bloomberg_terminal",
        display_name="Bloomberg Data Connector",
        version="1.0.0",
        api_version="1.0",
        plugin_type="source_connector",
        capabilities=["market.pricing.fetch", "market.estimates.fetch"],
    )

    def resolve_issuer(self, identifier: str): ...
    def search(self, query: SourceQuery): ...
    def fetch(self, source: SourceDocumentRef) -> bytes: ...
    def get_company_facts(self, cik: str): ...
```

---

## 5. Getting Started & Local Installation

### Prerequisites

- **macOS** (Tested on Apple Silicon & Intel)
- **Python 3.12+**
- **Swift 6.0+** (Included with Xcode or Apple Command Line Tools)
- **Ollama** (Optional for local LLM inference with `gemma4:latest`; mock provider included for fast, offline operation)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/rahul02-dat/Apollo-research.git
cd Apollo-research

# 2. Create and activate a Python 3.12 virtual environment
python3.12 -m venv env
source env/bin/activate

# 3. Install Python dependencies in editable mode
pip install -e ".[dev]"

# 4. Set up environment configuration
cp .env.example .env
```

### Step 1: Start the FastAPI Backend

Run the FastAPI backend on port 8000:

```bash
./env/bin/uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### Step 2: Start the Swift Web Dashboard

In a separate terminal window, launch the high-performance Swift HTTP server:

```bash
cd frontend
swift run ApolloDashboard
```

- Swift Web Dashboard URL: **`http://localhost:3000`**

---

## 6. License

Apollo is released under the **MIT License**. See `LICENSE` for details.
