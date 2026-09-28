import os
import sys
import json
import time
import urllib.parse
import http.server
import socketserver
import threading
import urllib.request
from tester.graph import run_multi_agent_pipeline

GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")
TARGET_APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target-app")

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local port is already responding."""
    try:
        req = urllib.request.Request(f"http://{host}:{port}", method="HEAD")
        with urllib.request.urlopen(req, timeout=0.5):
            return True
    except Exception:
        return False

def start_target_app_server(port: int = 8000):
    """Spins up background daemon server for the seeded demo app if not already running."""
    if is_port_in_use(port):
        return

    class TargetHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=TARGET_APP_DIR, **kwargs)
        def log_message(self, format, *args):
            pass

    def _run():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("127.0.0.1", port), TargetHandler) as httpd:
                httpd.serve_forever()
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(0.3)
    print(f"🎯 Seeded demo app active at http://127.0.0.1:{port}")


class GUIRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handles static GUI serving and POST /api/audit requests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=GUI_DIR, **kwargs)

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stdout.write(f"[Server] {self.address_string()} - {format%args}\n")

    def end_headers(self):
        # Enable CORS and disable aggressive caching for local dashboard
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/audit":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                data = json.loads(body) if body else {}
                raw_url = data.get("url", "").strip()

                if not raw_url:
                    self._send_json({"success": False, "error": "URL parameter is required."}, status=400)
                    return

                # Normalise URL
                target_url = raw_url
                if not target_url.startswith("http://") and not target_url.startswith("https://"):
                    target_url = "http://" + target_url

                # Execute Parallel Multi-Agent State Graph Pipeline
                state = run_multi_agent_pipeline(target_url)

                response_payload = {
                    "success": True,
                    "target_url": state.target_url,
                    "elapsed_time": state.elapsed_time,
                    "element_count": len(state.dom_elements),
                    "fuzz_actions_count": len(state.fuzz_actions),
                    "audited_routes": state.audited_routes,
                    "hard_bugs": [b.model_dump() for b in state.hard_bugs],
                    "ux_improvements": [ux.model_dump() for ux in state.ux_improvements],
                    "completed_nodes": state.completed_nodes
                }
                self._send_json(response_payload)

            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, payload: dict, status: int = 200):
        response_bytes = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def run_gui_server(gui_port: int = 5050):
    start_target_app_server(8000)

    socketserver.TCPServer.allow_reuse_address = True
    port = gui_port
    while port < gui_port + 10:
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", port), GUIRequestHandler)
            break
        except OSError:
            port += 1

    print("\n" + "="*60)
    print(f"✨ AI App Tester GUI running at: http://127.0.0.1:{port}")
    print(f"🎯 Seeded demo app available at : http://127.0.0.1:8000")
    print("="*60 + "\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GUI server...")
        httpd.server_close()

if __name__ == "__main__":
    run_gui_server()
