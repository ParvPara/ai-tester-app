# AI App Tester

A deterministic, multi-agent automated web testing and quality engineering framework in Python.

The system inspects any live web application over HTTP (such as the default deployed target or local endpoints), extracts a sanitized, token-efficient DOM representation of interactive controls, and uses specialized LLM agents with structured outputs to generate boundary test cases and accessibility/usability audits. It physically executes the generated boundary actions using headless Chromium workers to intercept runtime errors, network failures, and DOM exceptions, presenting findings in a structured dashboard split into verified hard defects, test hypotheses, and UX improvements.

---

## Architecture and Core Components

```text
ai-app-tester/
├── gui/
│   ├── index.html       # Web dashboard with state graph visualizer and report panels
│   ├── style.css        # Minimalist dark interface styling and typography
│   └── app.js           # Client-side graph controller, API client, and report renderer
├── server.py            # Local REST API server (POST /api/audit) & static GUI file server
├── target-app/
│   ├── index.html       # Storefront catalog with boundary quantity handling and accessibility flaws
│   ├── cart.html        # Shopping cart view with promo code and shipping rate HTTP endpoints
│   └── checkout.html    # Express checkout view with unsanitized DOM insertion and overflow states
├── tester/
│   ├── __init__.py      # Package initialization
│   ├── config.py        # Runtime settings, timeouts, and multi-tier LLM provider configuration
│   ├── schema.py        # Pydantic data models (AgentState, FuzzAction, HardBug, UXImprovement)
│   ├── browser.py       # Playwright telemetry harness, DOM extraction, and route discovery
│   ├── graph.py         # Parallel Multi-Agent State Graph orchestrator with concurrent worker pool
│   ├── agents/          # Specialized multi-agent system nodes
│   │   ├── __init__.py
│   │   ├── fuzzer.py    # Adversarial Fuzzing Agent (numeric boundaries, injection payloads)
│   │   ├── auditor.py   # WCAG and plain-English usability auditor agent
│   │   └── judge.py     # Deterministic False-Positive Judge node (0% false positives)
│   ├── llm.py           # Unified multi-provider LLM interface with automatic failover
│   ├── runner.py        # Headless Playwright test harness and verification utilities
│   └── reporter.py      # Dual-bucket HTML and terminal reporting generators
├── main.py              # Application entry point (launches Web GUI or CLI audit pipeline)
├── requirements.txt     # Python package dependencies
└── README.md            # System documentation and architecture reference
```

---

## Key Design Rationale

1. **Parallel Multi-Agent State Graph and Multi-Route Sweep**:
   - The tester operates strictly as a black-box HTTP client. It never imports, inspects, or modifies the target application's source code.
   - Starting from any target URL, the engine discovers same-origin navigation routes (e.g. Catalog -> Cart -> Checkout) directly from the live DOM over HTTP.
   - Specialized agent nodes run concurrently:
     - **DOM Ingestion Node**: Headless Chromium DOM harvesting and token pruning (typically under 500 tokens per route).
     - **Adversarial Fuzzer Agent**: Generates numeric boundary vectors, payload injections, and unexpected control sequences.
     - **WCAG and UX Auditor Agent**: Runs concurrently via thread pooling across routes to evaluate accessibility, readability, and cognitive friction.
     - **Playwright Grounding Gate**: Concurrently executes test actions across isolated browser contexts, intercepting runtime exceptions (`pageerror`) and failed HTTP responses (`response`).
     - **False-Positive Judge Node**: Correlates telemetry against proposed actions, strictly rejecting unverified hypotheses to guarantee zero false positives.
     - **Dual-Bucket Synthesis Node**: Combines verified runtime defects, test hypotheses evaluated, and plain-English UX improvements into a unified report.

2. **Parallelized Execution Worker Pool**:
   - Boundary test actions are partitioned across concurrent Chromium worker threads (`ThreadPoolExecutor`).
   - Rather than executing 10 to 15 browser interactions sequentially (which takes 25-35 seconds), parallel workers run actions simultaneously, reducing browser execution latency to under 4 seconds.

3. **Multi-Tier LLM Failover**:
   - Configurable primary provider (`OpenAI` or `Groq`) with automatic failover:
     - Tier 1: Primary provider (e.g. OpenAI `gpt-4o-mini` or Groq `openai/gpt-oss-120b`).
     - Tier 2: Secondary provider fallback if rate limits (HTTP 429) or token quotas are encountered.
     - Tier 3: Deterministic offline rule engine if no internet connectivity or API keys are available.

4. **Plain-English Executive Summaries**:
   - For every verified hard defect, the report produces:
     - **Test Intent**: Plain-English explanation of what boundary condition was probed.
     - **User Scenario**: Realistic user actions that trigger the condition (e.g. accidental negative quantities or rapid clicks).
     - **Commercial and Business Impact**: Financial, conversion, or operational consequences if the issue remains unresolved.
   - For UX improvements, technical specifications are translated into clear, actionable recommendations with suggested remediation code.

5. **Deterministic Strict Verification Gate (Zero False Positives)**:
   - An issue is elevated to a **Hard Defect** only if Playwright captures concrete browser telemetry:
     - An uncaught JavaScript runtime exception (`TypeError`, `RangeError`, `DOMException`, `SyntaxError`).
     - A network request returning HTTP status >= 400 (e.g. 404, 500).
   - Third-party analytics and ad-tracker domains (`google-analytics.com`, `clarity.ms`, `facebook.net`) are filtered to prevent external network noise from creating false positives.

6. **Generated Hypotheses vs. Verified Defects Visibility**:
   - The dashboard displays the full spectrum of generated test hypotheses alongside confirmed defects.
   - Each generated test case displays its execution verdict: `Defect Verified` (with the intercepted stack trace) or `Handled Safely` (validating that the application handled the boundary condition cleanly).

---

## Setup and Quickstart

### 1. Prerequisites and Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```bash
# Provider Preference: "openai" or "groq"
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Groq Configuration (Optional secondary failover)
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=openai/gpt-oss-120b

# Default Target URL (Optional, defaults to deployed Vercel target)
TARGET_URL=https://ai-target-app.vercel.app/
```
*(If no API keys are supplied, the engine automatically uses its deterministic offline rule engine).*

### 3. Launch the Web Dashboard
Start the application server:
```bash
python main.py
```
This launches the dashboard at `http://127.0.0.1:5050` and opens the browser interface.
- Target URL defaults to the deployed storefront (`https://ai-target-app.vercel.app/`).
- Preset buttons allow switching between the live Vercel app, the local seed app (`http://127.0.0.1:8000`), or custom endpoints.
- Click **Execute Audit** to view real-time state graph progression and inspection results.

### 4. Command Line Interface (CLI) Mode
To execute audits directly in the terminal and output an HTML report:
```bash
# Audit the default deployed target
python main.py --cli --url https://ai-target-app.vercel.app/

# Audit the local test server
python main.py --cli --url http://127.0.0.1:8000

# Audit any remote HTTP target
python main.py --cli --url https://example.com
```

Reports are automatically generated and saved to `report.html`.
