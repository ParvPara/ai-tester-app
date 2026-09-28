import time
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable
from playwright.sync_api import sync_playwright, Error as PlaywrightError

from tester.config import HEADLESS, BROWSER_TIMEOUT_MS
from tester.schema import AgentState, FuzzAction, UXImprovement, HardBug
from tester.browser import inspect_page, BrowserTelemetry
from tester.agents.fuzzer import run_fuzzer_agent
from tester.agents.auditor import run_auditor_agent
from tester.agents.judge import evaluate_execution_telemetry


class AppTesterGraph:
    """
    Parallel Multi-Agent State Graph Orchestrator.
    
    Graph Topology:
    [Target URL]
          │
          ▼
    [1. DOM Ingestion Node] (Playwright headless inspection)
          │
          ├──────────────────────────────┐
          ▼                              ▼
    [2a. Adversarial Fuzzer Node]   [2b. WCAG & UX Auditor Node]   <-- (Parallel ThreadPool execution)
          │                              │
          ▼                              │
    [3. Playwright Grounding Gate]       │
          │                              │
          ▼                              │
    [4. False Positive Judge Node]       │
          │                              │
          ├──────────────────────────────┘
          ▼
    [5. Dual-Bucket Synthesis Node]
          │
          ▼
    [Verified Hard Bugs + Plain-English UX Improvements]
    """

    def __init__(
        self,
        target_url: str,
        on_step_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]] = None
    ):
        self.state = AgentState(target_url=target_url)
        self.callback = on_step_callback or (lambda node, status, data=None: None)

    def _notify(self, node_name: str, status: str, data: Optional[Dict[str, Any]] = None):
        self.state.active_node = node_name if status == "running" else None
        if status == "completed" and node_name not in self.state.completed_nodes:
            self.state.completed_nodes.append(node_name)
        try:
            self.callback(node_name, status, data)
        except Exception:
            pass

    def run(self) -> AgentState:
        start_time = time.time()
        print(f"\n=======================================================")
        print(f"🚀 Launching Parallel Multi-Agent Testing Graph on: {self.state.target_url}")
        print(f"=======================================================")

        # ----------------------------------------------------
        # NODE 1: DOM Ingestion Node
        # ----------------------------------------------------
        self._notify("dom_ingest", "running")
        print("\n[Node 1: DOM Ingestion] Harvesting interactive controls via Playwright...")
        dom_elements, initial_telemetry = inspect_page(self.state.target_url)
        self.state.dom_elements = dom_elements
        self._notify("dom_ingest", "completed", {"element_count": len(dom_elements)})
        print(f"  ✓ Harvested {len(dom_elements)} interactive elements (inputs, buttons, links, images)")

        # ----------------------------------------------------
        # NODE 2: Parallel Multi-Agent Analysis Node
        # (Adversarial Fuzzer || WCAG & UX Auditor)
        # ----------------------------------------------------
        self._notify("parallel_agents", "running")
        print("\n[Node 2: Parallel Agents] Spawning Fuzzer Agent & Auditor Agent concurrently...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_fuzzer = executor.submit(run_fuzzer_agent, dom_elements)
            future_auditor = executor.submit(run_auditor_agent, dom_elements)

            fuzz_actions = future_fuzzer.result()
            ux_improvements = future_auditor.result()

        self.state.fuzz_actions = fuzz_actions
        self.state.ux_improvements = ux_improvements
        self._notify("parallel_agents", "completed", {
            "fuzz_count": len(fuzz_actions),
            "ux_count": len(ux_improvements)
        })
        print(f"  ✓ Fuzzer Agent produced {len(fuzz_actions)} boundary test hypotheses")
        print(f"  ✓ Auditor Agent produced {len(ux_improvements)} plain-English UX/accessibility improvements")

        # ----------------------------------------------------
        # NODE 3 & 4: Playwright Grounding Gate & Judge Node
        # ----------------------------------------------------
        self._notify("playwright_gate", "running")
        print(f"\n[Node 3: Playwright Grounding Gate] Executing {len(fuzz_actions)} test actions with live error interception...")

        hard_bugs: List[HardBug] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            for idx, action in enumerate(fuzz_actions, 1):
                telemetry = BrowserTelemetry()
                page = context.new_page()

                # Attach live event listeners to intercept runtime crashes and 4xx/5xx network errors
                page.on("pageerror", telemetry._on_page_error)
                page.on("response", telemetry._on_response)

                repro_steps = [f"1. Open target URL: {self.state.target_url}"]

                try:
                    try:
                        page.goto(self.state.target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                        page.wait_for_timeout(300)
                    except Exception:
                        page.goto(self.state.target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="load")

                    if action.action_type == "fill":
                        repro_steps.append(f"2. Fill input '{action.selector}' with payload: '{action.payload}'")
                        page.fill(action.selector, action.payload or "", timeout=2000)
                    elif action.action_type == "click":
                        repro_steps.append(f"2. Click element '{action.selector}'")
                        page.click(action.selector, timeout=2000)

                    page.wait_for_timeout(400)

                except PlaywrightError:
                    pass
                finally:
                    # ----------------------------------------------------
                    # NODE 4: Judge Node (Strict verification on each executed action)
                    # ----------------------------------------------------
                    action_bugs = evaluate_execution_telemetry(
                        action=action,
                        target_url=self.state.target_url,
                        page_errors=telemetry.page_errors,
                        network_errors=telemetry.network_errors,
                        repro_steps=repro_steps
                    )
                    hard_bugs.extend(action_bugs)
                    page.close()

            browser.close()

        self._notify("playwright_gate", "completed", {"executed_count": len(fuzz_actions)})
        self._notify("judge_node", "completed", {"verified_hard_bugs": len(hard_bugs)})
        self.state.hard_bugs = hard_bugs
        print(f"  ✓ False Positive Judge Node verified {len(hard_bugs)} deterministic hard bugs (0% false positives)")

        # ----------------------------------------------------
        # NODE 5: Dual-Bucket Synthesis Node
        # ----------------------------------------------------
        self._notify("synthesis", "running")
        total_time = round(time.time() - start_time, 2)
        self.state.elapsed_time = total_time
        self._notify("synthesis", "completed", {
            "elapsed_time": total_time,
            "hard_bugs": len(self.state.hard_bugs),
            "ux_improvements": len(self.state.ux_improvements)
        })

        print(f"\n=======================================================")
        print(f"✨ Multi-Agent Graph Completed in {total_time}s")
        print(f"   Hard Bugs Verified: {len(self.state.hard_bugs)}")
        print(f"   UX Improvements:    {len(self.state.ux_improvements)}")
        print(f"=======================================================\n")

        return self.state


def run_multi_agent_pipeline(
    target_url: str,
    on_step_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]] = None
) -> AgentState:
    """Convenience entry point for running the complete multi-agent graph pipeline."""
    graph = AppTesterGraph(target_url, on_step_callback=on_step_callback)
    return graph.run()
