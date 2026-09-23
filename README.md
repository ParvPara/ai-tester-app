# AI App Tester 🤖

A lightweight, deterministic AI App Tester prototype in Python designed for technical presentations and forward-deployed engineering workflows.

The tool inspects any live web application (or the included seeded demo app), extracts a sanitized, token-efficient representation of interactive DOM elements, uses an LLM with strict structured outputs to generate boundary test cases and UX/accessibility audits, executes the tests deterministically via headless Playwright, and renders an interactive dashboard partitioned into **Hard Bugs vs. UX Improvements**.

---

## 🏗️ Architecture & Core Components

```text
ai-app-tester/
├── gui/
│   ├── index.html       # Modern dark mode dashboard with live audit controls
│   ├── style.css        # Responsive glassmorphism styles & status cards
│   └── app.js           # Frontend controller & dynamic report renderer
├── server.py            # Local REST API server & static GUI server (127.0.0.1)
├── target-app/
│   ├── index.html       # Standalone demo app seeded with intentional bugs
│   └── app.js           # Client-side logic with uncaught exceptions & broken API calls
├── tester/
│   ├── __init__.py      # Package initialization
│   ├── config.py        # Configuration and environment settings
│   ├── schema.py        # Pydantic models enforcing structured input/output schemas
│   ├── browser.py       # Playwright telemetry harness & sanitized DOM extractor (<500 tokens)
│   ├── llm.py           # LLM reasoning layer (OpenAI structured outputs + fallback rule engine)
│   ├── runner.py        # Fuzz execution engine with Strict Verification Gate
│   └── reporter.py      # Dual-bucket HTML and terminal reporting layer
├── main.py              # Unified entry point (Launches Web GUI or CLI)
├── requirements.txt     # Python dependencies
└── README.md            # Architecture notes & setup instructions
```

---

## ⚡ Key Design Rationale

1. **Deterministic Strict Verification Gate (Zero False Positives)**:
   - An edge-case finding is **only** elevated to a **Hard Bug** if Playwright actively intercepts:
     - An uncaught JavaScript exception (`pageerror` event).
     - A failed network request with an HTTP status code >= 400 (`response` event).
   - Prevents LLM hallucinations or speculative findings from polluting high-severity bug backlogs.

2. **Ultra-Fast & Token-Efficient (< 30s Execution, < 500 Tokens)**:
   - Instead of feeding massive raw DOM trees or screenshots to the LLM, `tester/browser.py` extracts a pruned, sanitized JSON representation of only interactive nodes (`<input>`, `<button>`, `<a>`, `<select>`, `<form>`, and unlabelled `<img>`).
   - Keeps LLM prompt tokens under 500, minimizing latency and API costs.

3. **Guaranteed Presentation Stability (Offline & Zero-Crash Fallback)**:
   - The GUI server binds explicitly to loopback `127.0.0.1`, guaranteeing 100% functionality without relying on conference Wi-Fi or router DNS.
   - If `OPENAI_API_KEY` is not present or network drops, `tester/llm.py` automatically activates its deterministic rule engine within milliseconds.

4. **Actionable Dual-Bucket Reporting**:
   - **🔴 Hard Bugs**: Concrete runtime crashes and 4xx/5xx failures with exact reproduction steps, selectors, and error stack traces.
   - **🟡 UX & Accessibility Improvements**: Semantic DOM issues (missing `<label>`, missing `alt` attributes, lack of `aria-label`) with developer remediation recommendations.

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
