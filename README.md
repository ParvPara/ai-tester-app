# AI App Tester Prototype 🤖

A lightweight, deterministic AI App Tester prototype in Python designed for technical presentations and forward-deployed engineering workflows.

The tool inspects a live web application, extracts a sanitized, token-efficient representation of interactive DOM elements, uses an LLM with strict structured outputs to generate boundary test cases and UX/accessibility audits, executes the tests deterministically via headless Playwright, and exports a dual-bucket developer report.

---

## 🏗️ Architecture & Core Components

```text
ai-app-tester/
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
├── main.py              # Single CLI entry point
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

3. **Guaranteed Demo Stability (Zero Crash Fallback)**:
   - If `OPENAI_API_KEY` is not present or an API network blip occurs, `tester/llm.py` automatically falls back to an integrated deterministic rule-based generator, guaranteeing the presentation never halts or fails.

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

### 3. Run the Tester
Execute against the included target demo application:
```bash
python main.py
```
Or test against an external URL:
```bash
python main.py --url https://example.com --output report.html
```

When finished, review the terminal output and open `report.html` in your browser.
