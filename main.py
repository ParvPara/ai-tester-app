import sys
import os
import time
import argparse
import threading
import http.server
import socketserver
import urllib.request
from tester.config import DEFAULT_TARGET_URL
from tester.browser import inspect_page
from tester.llm import analyze_dom_with_llm
from tester.runner import execute_fuzz_tests
from tester.reporter import render_terminal_report, generate_html_report

def is_server_running(url: str, timeout: float = 1.0) -> bool:
    """Checks if the target server is already responsive."""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False

def start_local_target_server(port: int = 8000, directory: str = "target-app"):
    """Starts a local HTTP server in a background thread to serve the target app."""
    abs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), directory)
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=abs_dir, **kwargs)
        def log_message(self, format, *args):
            pass # Suppress HTTP access logs to keep terminal output clean

    def _serve():
        # Allow immediate socket reuse
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()

    server_thread = threading.Thread(target=_serve, daemon=True)
    server_thread.start()
    time.sleep(0.5)
    print(f"🚀 Started local demo server at http://localhost:{port} serving '{directory}/'")

def main():
    parser = argparse.ArgumentParser(description="AI App Tester Prototype - Deterministic Browser QA & Fuzzing Engine")
    parser.add_argument("--url", default=DEFAULT_TARGET_URL, help=f"Target URL to audit (default: {DEFAULT_TARGET_URL})")
    parser.add_argument("--output", default="report.html", help="Path for HTML report export (default: report.html)")
    parser.add_argument("--serve", action="store_true", help="Force start local demo target server")
    args = parser.parse_args()

    target_url = args.url

    # Check if target server is running; auto-spin local demo server if localhost:8000 is down
    if ("localhost:8000" in target_url or "127.0.0.1:8000" in target_url or args.serve):
        if not is_server_running(target_url):
            start_local_target_server(8000, "target-app")

    start_time = time.time()

    print("\n🔍 Step 1/3: Launching headless browser and extracting interactive DOM elements...")
    dom_elements, _ = inspect_page(target_url)
    print(f"   ✓ Extracted {len(dom_elements)} sanitized interactive elements (< 500 tokens).")

    print("\n🧠 Step 2/3: Analyzing DOM semantics with LLM reasoning layer...")
    audit = analyze_dom_with_llm(dom_elements)
    print(f"   ✓ Generated {len(audit.fuzz_actions)} targeted boundary test cases.")
    print(f"   ✓ Identified {len(audit.ux_improvements)} accessibility/UX improvements.")

    print("\n⚡ Step 3/3: Executing boundary actions via Playwright & applying verification gate...")
    hard_bugs, ux_improvements = execute_fuzz_tests(target_url, audit)
    print(f"   ✓ Fuzz execution complete. Verified Hard Bugs: {len(hard_bugs)}.")

    elapsed = time.time() - start_time

    # Render reports
    render_terminal_report(hard_bugs, ux_improvements, elapsed, target_url)
    generate_html_report(hard_bugs, ux_improvements, elapsed, target_url, args.output)

if __name__ == "__main__":
    main()
