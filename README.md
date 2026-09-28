# AI App Tester 🤖

A lightweight, deterministic AI App Tester prototype in Python designed for technical presentations and forward-deployed engineering workflows.

The tool inspects any live web application (or the included seeded demo app), extracts a sanitized, token-efficient representation of interactive DOM elements, uses an LLM with strict structured outputs to generate boundary test cases and UX/accessibility audits, executes the tests deterministically via headless Playwright, and renders an interactive dashboard partitioned into **Hard Bugs vs. UX Improvements**.

---

## 🏗️ Architecture & Core Components

```text
ai-app-tester/
├── gui/
│   ├── index.html       # Modern dark mode dashboard with interactive State Graph visualizer
│   ├── style.css        # Responsive glassmorphism styles, graph node pulses & status cards
│   └── app.js           # Dynamic graph controller & dual-bucket executive report renderer
├── server.py            # Local REST API server & static GUI server (127.0.0.1)
├── target-app/
│   ├── index.html       # Storefront catalog with boundary quantity and accessibility flaws
│   ├── cart.html        # Shopping cart with promo & shipping rate HTTP 404 endpoints
│   └── checkout.html    # Express checkout with script injection DOMException & cargo overflow
├── tester/
│   ├── __init__.py      # Package initialization
│   ├── config.py        # Environment settings (Groq LPU / OpenAI / Offline fallback)
│   ├── schema.py        # Pydantic models (AgentState, FuzzAction, HardBug, UXImprovement)
│   ├── browser.py       # Playwright telemetry harness & same-origin route discovery (<500 tokens)
│   ├── graph.py         # Parallel Multi-Agent State Graph Orchestrator (Multi-Route Sweep)
│   ├── agents/          # Specialized Multi-Agent System Nodes
│   │   ├── __init__.py
│   │   ├── fuzzer.py    # Adversarial Fuzzing Agent (boundary & injection attack vectors)
│   │   ├── auditor.py   # WCAG & Plain-English Usability Auditor Agent
│   │   └── judge.py     # Deterministic False-Positive Judge Node (0% false positives)
│   ├── llm.py           # Unified LLM reasoning layer & deterministic fallback engine
│   ├── runner.py        # Headless Playwright test harness & verification gate
│   └── reporter.py      # Dual-bucket HTML and terminal reporting layer
├── main.py              # Unified entry point (Launches Web GUI or CLI graph pipeline)
├── requirements.txt     # Python dependencies
└── README.md            # Architecture notes & setup instructions
```

---

## ⚡ Key Design Rationale

1. **Parallel Multi-Agent State Graph & Black-Box Multi-Route Sweep**:
   - The tester operates **strictly as a black-box HTTP client**; it never touches or imports the target app's source code.
   - Starting from any target URL, the engine discovers same-origin navigation routes (e.g. Catalog ➔ Cart ➔ Checkout) directly from the live DOM over HTTP.
   - Specialized agent nodes run concurrently:
     - **🌐 DOM Ingestion Node**: Headless Playwright DOM harvest & token pruning (<500 tokens per route).
     - **⚡ Adversarial Fuzzer Agent**: Specialized in numeric boundaries, SQLi/XSS, and API endpoint attack vectors.
     - **👁️ WCAG & UX Auditor Agent**: Runs in **parallel** via thread pooling across routes to audit accessibility and human friction concurrently.
     - **🛡️ Playwright Grounding Gate**: Physically executes fuzz actions in isolated browser contexts, capturing runtime crashes and HTTP failures across routes.
     - **⚖️ False-Positive Judge Node**: Correlates telemetry against proposed actions, strictly rejecting unverified hypotheses to guarantee **0% false positives**.
     - **📊 Dual-Bucket Synthesis**: Assembles route-badged reports split into verified Hard Bugs vs. Plain-English UX improvements.

2. **Plain-English Executive Summaries (Non-Engineer Friendly)**:
   - For every verified Hard Bug, the report produces:
     - **🎯 Test Intent**: Why this boundary or action was probed in plain English.
     - **👤 User Scenario**: Realistic customer behavior that triggers the issue (e.g. typos, rushing through checkout).
     - **📉 Business Impact**: Customer and revenue consequences if left unfixed (e.g. cart abandonment, lost sales).
   - For UX improvements, jargon like `<label for="">` or `aria-describedby` is replaced with intuitive human explanations of friction and screen-reader accessibility.

3. **Deterministic Strict Verification Gate (Zero False Positives)**:
   - An issue is **only** elevated to a **Hard Bug** if Playwright actively intercepts:
     - An uncaught JavaScript exception (`pageerror` event: `TypeError`, `RangeError`, `DOMException`).
     - A failed network request with an HTTP status code >= 400 (`response` event: 404, 500).
   - Filters out 3rd-party ad trackers (`google-analytics`, `facebook.net`, `clarity.ms`) to avoid false alarms.

4. **Ultra-Fast & Token-Efficient (< 20s Execution, $0 Cost)**:
   - Uses **Groq LPU** (`openai/gpt-oss-120b`) for ultra-low latency (~1.5s inference) with OpenAI fallback.
   - Extracts sanitized representations under 500 tokens, running entire multi-agent audits in ~15-18 seconds total.

5. **Guaranteed Presentation Stability (Offline & Zero-Crash Fallback)**:
   - Strict loopback binding (`127.0.0.1`) avoids macOS IPv6 resolution timeouts and enterprise Wi-Fi blocks.
   - 100% deterministic offline fallback rule engine ensures the system never crashes during a live demo even if internet or API keys drop.

---

## 🚀 Setup & Quickstart

### 1. Prerequisites & Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment (Optional)
If using OpenAI structured outputs, create a `.env` file (or set your environment variable):
```bash
OPENAI_API_KEY="your-api-key-here"
OPENAI_MODEL="gpt-4o-mini"
```
*(If no API key is provided, the tool automatically uses its deterministic rule engine).*

### 3. Launch the Web GUI Dashboard
Start the application:
```bash
python main.py
```
This automatically spins up the GUI server at **`http://127.0.0.1:5050`** and opens your default browser.
- Select the **🎯 Seeded Demo App** preset chip or enter any custom URL.
- Click **⚡ Run AI Audit** to watch the real-time execution stepper and inspect the live findings.

### 4. Optional: CLI Mode
To run audits directly from the command line without the GUI:
```bash
python main.py --cli --url http://127.0.0.1:8000
# Or against any arbitrary website:
python main.py --cli --url https://news.ycombinator.com
```
