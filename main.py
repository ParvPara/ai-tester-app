import sys
import os
import time
import argparse
import threading
import http.server
import socketserver
import urllib.request
import webbrowser
from tester.config import DEFAULT_TARGET_URL
from tester.browser import inspect_page
from tester.llm import analyze_dom_with_llm
from tester.runner import execute_fuzz_tests
from tester.reporter import render_terminal_report, generate_html_report
from server import run_gui_server

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
            pass

    def _serve():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
                httpd.serve_forever()
        except Exception:
            pass

    server_thread = threading.Thread(target=_serve, daemon=True)
    server_thread.start()
    time.sleep(0.4)
    print(f"🚀 Started local demo server at http://127.0.0.1:{port} serving '{directory}/'")

def run_cli_audit(target_url: str, output_path: str = "report.html", force_serve: bool = False):
    """Runs the direct terminal CLI pipeline."""
    if ("localhost:8000" in target_url or "127.0.0.1:8000" in target_url or force_serve):
        if not is_server_running(target_url):
            start_local_target_server(8000, "target-app")

    start_time = time.time()

    print(f"\n🔍 Step 1/3: Launching headless browser against {target_url}...")
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

    render_terminal_report(hard_bugs, ux_improvements, elapsed, target_url)
    generate_html_report(hard_bugs, ux_improvements, elapsed, target_url, output_path)

def main():
    parser = argparse.ArgumentParser(description="AI App Tester - Deterministic Browser QA & Fuzzing Engine")
    parser.add_argument("--url", default=None, help="Target URL to audit directly in CLI mode")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode instead of launching the GUI")
    parser.add_argument("--output", default="report.html", help="Path for HTML report export (default: report.html)")
    parser.add_argument("--port", type=int, default=5050, help="Port for Web GUI dashboard (default: 5050)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser on GUI start")
    args = parser.parse_args()

    # Determine execution mode: CLI if --cli or --url provided, else default to Web GUI
    if args.cli or args.url:
        url = args.url or DEFAULT_TARGET_URL
        run_cli_audit(url, args.output)
    else:
        # Launch Web GUI
        gui_url = f"http://127.0.0.1:{args.port}"
        if not args.no_browser:
            def _open():
                time.sleep(0.8)
                webbrowser.open(gui_url)
            threading.Thread(target=_open, daemon=True).start()

        run_gui_server(args.port)

if __name__ == "__main__":
    main()
