# Apollo — Plugin-Based Financial Research Platform

Apollo is a production-oriented financial research agent system designed for financial analysts and investors. Apollo investigates publicly traded companies using official US Securities and Exchange Commission (SEC EDGAR) filings and generates a downloadable, publication-grade PDF research report with verifiable citations and clickable primary-source links.

---

## 1. System Architecture

Apollo is built around three principal agents coordinated through a stateful **LangGraph** workflow:

- **Apollo (Orchestrator):** Plans research, controls workflow execution, manages human approvals, enforces autonomy limits, and evaluates completion rules.
- **Athena (Research Agent):** Discovers and retrieves official filings and financial metrics through registered source plugins, dispatching documents to narrative and XBRL extractor plugins.
- **Hermes (Evidence & Gap Analyzer):** Evaluates question-level evidence coverage, identifies knowledge gaps, and triggers targeted follow-up retrieval requests within approved bounds.

```text
[Analyst / User]
       │
       ▼
[Swift Web App Dashboard: Port 3000]
       │
       ▼ (HTTP REST)
[FastAPI Backend: Port 8000]
       │
       ▼
[Apollo Orchestrator: LangGraph]
 ├── 1. Request Normalization & CIK Resolution
 ├── 2. Research Planning (Itinerary Generation)
 ├── 3. [HUMAN APPROVAL GATE]
 ├── 4. Athena Retrieval (SEC EDGAR Plugin)
 ├── 5. Extractors (HTML & XBRL Facts Plugins)
 ├── 6. Hermes Gap Detection Loop (Bounded Follow-ups)
 ├── 7. Stage 1: Section-Specific Synthesis
 ├── 8. Stage 2: Final Report Assembly & Claim Validation
 └── 9. ReportLab PDF Exporter (Clickable Citations)
```

---

## 2. Core Invariants & Completion Rules

1. **Evidence Governs Completion:** Only deterministic application logic can mark a run `COMPLETE`. No LLM prompt or plugin can override this.
2. **100% Required Coverage:** A research run is `COMPLETE` only when every required research question has at least one valid primary-source evidence record attached.
3. **Traceability Chain:** Every material factual claim maps to an evidence ID, which resolves to an accession number and official SEC canonical URL:
   `Research Question → Evidence Record → Source Document → Claim → Section Draft → Final PDF`
4. **Preservation of Financial Context:** Numeric values retain Decimal representation, units/currencies (e.g. USD), reporting period start/end dates, and fiscal periods (`FY2024`, `Q3 2024`).
5. **Two-Stage Synthesis:** Section drafts are generated independently first; the overall report is assembled second with executive summary, transitions, limitations, and bibliography.
6. **Bounded Autonomy:** Default maximum of 3 automatic follow-up rounds. Unresolved questions yield an `INCOMPLETE` report with explicit disclosures.

---

## 3. First-Class Plugin Architecture

All extensions conform to typed Python `Protocol` interfaces and declare a `PluginManifest`:

| Plugin Type | Responsibility | Built-in Plugin | Capabilities |
|---|---|---|---|
| `source_connector` | Discovers and fetches sources | `sec_edgar` | `sec.issuer.resolve`, `sec.filings.search`, `sec.filings.fetch`, `sec.facts.fetch` |
| `document_extractor` | Converts raw filings into evidence | `filing_html`, `xbrl_facts` | `documents.html.extract`, `documents.xbrl.extract` |
| `evidence_validator` | Validates units and provenance | `financial_checks` | `evidence.financial.validate` |
| `synthesis_strategy` | Section synthesis from evidence | `financial_synthesis` | `synthesis.sections.generate` |
| `model_provider` | LLM invocation abstraction | `ollama` (gemma4), `mock` | `model.text.generate`, `model.structured.generate` |
| `report_exporter` | Renders report to artifact | `pdf` (ReportLab) | `report.pdf.export` |

### How to Create a New Plugin

1. Inherit from the relevant `Protocol` in `app/plugins/contracts.py` (e.g. `SourceConnector` or `ReportExporter`).
2. Declare a `PluginManifest` with unique `plugin_id`, `api_version="1.0"`, and declared `capabilities`.
3. Implement the required contract methods.
4. Expose an entrypoint factory or register with `plugin_registry.register(MyPlugin())`.

Example:

```python
from app.plugins.manifest import PluginManifest
from app.models.sources import SourceQuery, SourceDocumentRef

class CustomSourcePlugin:
    manifest = PluginManifest(
        plugin_id="custom_source",
        display_name="Custom Data Connector",
        version="1.0.0",
        api_version="1.0",
        plugin_type="source_connector",
        capabilities=["sec.filings.search", "sec.filings.fetch"],
    )

    def resolve_issuer(self, identifier: str): ...
    def search(self, query: SourceQuery): ...
    def fetch(self, source: SourceDocumentRef) -> bytes: ...
    def get_company_facts(self, cik: str): ...
```

---

## 4. Getting Started

### Prerequisites

- macOS with Python 3.11+ (Python 3.12 recommended)
- Swift 6.0+ (installed with Xcode / Command Line Tools)
- [Ollama](https://ollama.ai) running locally for `gemma4:latest` (or mock mode for offline testing)

### Installation

```bash
# Clone and enter directory
cd apollo-research

# Create / activate virtual environment
python3.12 -m venv env
source env/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Copy environment configuration
cp .env.example .env
```

---

## 5. Running the Application

### Step 1: Start the FastAPI Backend

```bash
./env/bin/uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000` with interactive OpenAPI docs at `http://localhost:8000/docs`.

### Step 2: Start the Swift Web Dashboard

In a new terminal window:

```bash
cd frontend
swift run ApolloDashboard
```

The Swift Web Dashboard will be live at **`http://localhost:3000`**.

---

## 6. Demonstrated End-to-End Workflow

1. Open `http://localhost:3000` in your browser.
2. Enter a ticker symbol (e.g. `MSFT`, `AAPL`, or `NVDA`) and submit the research form.
3. Apollo resolves the issuer to its official CIK, generates a 5-section research itinerary, and pauses at the **Human Approval Gate**.
4. Review the proposed questions, then click **Approve Itinerary**.
5. Athena retrieves official filings and XBRL metrics; Hermes evaluates question coverage and performs targeted follow-ups if gaps exist.
6. The two-stage synthesis pipeline drafts each section and validates all factual claims.
7. Click **Download PDF Report** to view the publication-grade PDF with clickable inline SEC citations and a primary-source bibliography.

---

## 7. Automated Acceptance Tests (AT-01 to AT-17)

Run the full automated test suite:

```bash
./env/bin/pytest tests/ -v
```

### Acceptance Test Matrix

| ID | Test Suite | Description | Status |
|---|---|---|---|
| **AT-01** | `test_issuer_resolution.py` | Valid ticker resolves to CIK; invalid ticker fails safely | **PASSED** |
| **AT-02** | `test_sec_retrieval.py` | Filing metadata and canonical SEC link are stored | **PASSED** |
| **AT-03** | `test_coverage_and_gaps.py` | Every supported question has validated evidence | **PASSED** |
| **AT-04** | `test_coverage_and_gaps.py` | Seeded missing evidence causes targeted follow-up & reevaluation | **PASSED** |
| **AT-05** | `test_coverage_and_gaps.py` | Workflow stops at max follow-up rounds and exposes unresolved gaps | **PASSED** |
| **AT-06** | `test_human_approval.py` | Graph pauses for plan approval and resumes correctly via thread ID | **PASSED** |
| **AT-07** | `test_financial_context.py` | Decimal values, currencies, and reporting periods are preserved | **PASSED** |
| **AT-08** | `test_citation_validation.py` | Missing or fabricated evidence IDs are deterministically rejected | **PASSED** |
| **AT-09** | `test_two_stage_synthesis.py` | Section drafts exist independently before report assembly | **PASSED** |
| **AT-10** | `test_incomplete_completion.py` | Unresolved required question prevents `COMPLETE` status | **PASSED** |
| **AT-11** | `test_pdf_exporter.py` | PDF artifact opens and contains clickable links & bibliography | **PASSED** |
| **AT-12** | `test_error_recovery.py` | Simulated 429/timeout produces bounded retries and safe failure | **PASSED** |
| **AT-13** | `test_plugin_system.py` | Missing method, invalid manifest, or incompatible API is rejected | **PASSED** |
| **AT-14** | `test_plugin_system.py` | Fake source plugin can substitute SEC without modifying graph code | **PASSED** |
| **AT-15** | `test_plugin_system.py` | Plugin cannot execute undeclared or ungranted capabilities | **PASSED** |
| **AT-16** | `test_plugin_system.py` | Malformed plugin response is contained without corrupting state | **PASSED** |
| **AT-17** | `test_plugin_system.py` | Alternative exporter consumes validated report model without synthesis edits | **PASSED** |
| **Integration** | `test_end_to_end_workflow.py` | End-to-end slice with fixture and live SEC connectivity | **PASSED** |
