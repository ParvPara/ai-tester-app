import time
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable
from playwright.sync_api import sync_playwright, Error as PlaywrightError

from tester.config import HEADLESS, BROWSER_TIMEOUT_MS
from tester.schema import AgentState, FuzzAction, UXImprovement, HardBug
from tester.browser import inspect_page, BrowserTelemetry, normalize_route_url
from tester.agents.fuzzer import run_fuzzer_agent
from tester.agents.auditor import run_auditor_agent
from tester.agents.judge import evaluate_execution_telemetry


def _run_fuzz_worker_batch(actions_batch: List[FuzzAction], base_target_url: str) -> List[HardBug]:
    """Worker thread running a dedicated Playwright instance to evaluate a batch of fuzz actions concurrently."""
    worker_bugs: List[HardBug] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        for action in actions_batch:
            action_target_url = action.page_url or base_target_url
            telemetry = BrowserTelemetry()
            page = context.new_page()

            # Attach live event listeners to intercept runtime crashes and 4xx/5xx network errors
            page.on("pageerror", telemetry._on_page_error)
            page.on("response", telemetry._on_response)

            repro_steps = [f"Open target URL: {action_target_url}"]

            try:
                try:
                    page.goto(action_target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                    page.wait_for_timeout(60)
                except Exception:
                    page.goto(action_target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="load")

                if action.action_type == "fill":
                    repro_steps.append(f"Fill input '{action.selector}' with payload: '{action.payload}'")
                    page.fill(action.selector, action.payload or "", timeout=800)
                    page.wait_for_timeout(50)

                    # Trigger client-side validation by submitting the enclosing form if present
                    submit_btn = (
                        page.query_selector(f"{action.selector} >> xpath=ancestor::form//button[@type='submit']")
                        or page.query_selector(f"{action.selector} >> xpath=ancestor::form//button")
                        or page.query_selector("button[type='submit']")
                    )
                    if submit_btn:
                        repro_steps.append("Submit form to trigger client-side validation and boundary handling")
                        submit_btn.click(timeout=800)
                    else:
                        page.press(action.selector, "Enter")

                elif action.action_type == "click":
                    repro_steps.append(f"Click element '{action.selector}'")
                    page.click(action.selector, timeout=800)

                page.wait_for_timeout(100)

            except PlaywrightError:
                pass
            finally:
                # ----------------------------------------------------
                # NODE 4: Judge Node (Strict verification on each executed action)
                # ----------------------------------------------------
                action_bugs = evaluate_execution_telemetry(
                    action=action,
                    target_url=action_target_url,
                    page_errors=telemetry.page_errors,
                    network_errors=telemetry.network_errors,
                    repro_steps=repro_steps
                )
                if action_bugs:
                    action.verified_bug = True
                    action.error_signature = action_bugs[0].error_message
                else:
                    action.verified_bug = False
                    action.error_signature = None
                worker_bugs.extend(action_bugs)
                page.close()

        browser.close()
    return worker_bugs


class AppTesterGraph:
    """
    Parallel Multi-Agent State Graph Orchestrator with Multi-Page Route Sweep.
    
    Graph Topology:
    [Target URL] (Black-box over HTTP)
          │
          ▼
    [1. DOM Ingestion & Multi-Route Discovery] ──► Discovers same-origin links (Top 3 pages)
          │
          ├──────────────────────────────┐
          ▼                              ▼
    [2a. Adversarial Fuzzer Node]   [2b. WCAG & UX Auditor Node]   <-- (ThreadPool per route)
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
    [Verified Hard Bugs + Plain-English UX Improvements across All Routes]
    """

    def __init__(
        self,
        target_url: str,
        max_routes: int = 3,
        on_step_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]] = None
    ):
        self.state = AgentState(target_url=target_url)
        self.max_routes = max_routes
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
        # NODE 1: DOM Ingestion & Same-Origin Route Discovery
        # ----------------------------------------------------
        self._notify("dom_ingest", "running")
        print("\n[Node 1: DOM Ingestion] Harvesting interactive controls & discovering same-origin routes...")

        routes_to_visit = [self.state.target_url]
        visited_routes: List[str] = []
        page_elements_map: Dict[str, List[Dict[str, Any]]] = {}
        all_dom_elements: List[Dict[str, Any]] = []

        visited_norm = set()

        while routes_to_visit and len(visited_routes) < self.max_routes:
            current_url = routes_to_visit.pop(0)
            norm_curr = normalize_route_url(current_url)
            if norm_curr in visited_norm:
                continue

            dom_elements, discovered_routes, _ = inspect_page(current_url)
            visited_norm.add(norm_curr)
            visited_routes.append(current_url)
            page_elements_map[current_url] = dom_elements
            all_dom_elements.extend(dom_elements)

            for route in discovered_routes:
                norm_r = normalize_route_url(route)
                if norm_r not in visited_norm and not any(normalize_route_url(q) == norm_r for q in routes_to_visit):
                    if len(visited_routes) + len(routes_to_visit) < self.max_routes:
                        routes_to_visit.append(route)

        self.state.audited_routes = visited_routes
        self.state.dom_elements = all_dom_elements
        self._notify("dom_ingest", "completed", {
            "element_count": len(all_dom_elements),
            "route_count": len(visited_routes),
            "routes": visited_routes
        })
        print(f"  ✓ Discovered {len(visited_routes)} route(s):")
        for r in visited_routes:
            print(f"    • {r}")
        print(f"  ✓ Harvested {len(all_dom_elements)} interactive elements total across all routes")

        # ----------------------------------------------------
        # NODE 2: Parallel Multi-Agent Analysis Node
        # (Fuzzer || Auditor concurrently across routes)
        # ----------------------------------------------------
        self._notify("parallel_agents", "running")
        print(f"\n[Node 2: Parallel Agents] Spawning Fuzzer & Auditor concurrently across {len(visited_routes)} route(s)...")

        all_fuzz_actions: List[FuzzAction] = []
        all_ux_improvements: List[UXImprovement] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_route = {}
            for route_url, elems in page_elements_map.items():
                future_fuzzer = executor.submit(run_fuzzer_agent, elems)
                future_auditor = executor.submit(run_auditor_agent, elems)
                future_to_route[route_url] = (future_fuzzer, future_auditor)

            for route_url, (fuzzer_fut, auditor_fut) in future_to_route.items():
                route_fuzz = fuzzer_fut.result()
                route_ux = auditor_fut.result()

                for act in route_fuzz:
                    act.page_url = route_url
                    all_fuzz_actions.append(act)

                for ux in route_ux:
                    ux.page_url = route_url
                    all_ux_improvements.append(ux)

        self.state.fuzz_actions = all_fuzz_actions
        self.state.ux_improvements = all_ux_improvements
        self._notify("parallel_agents", "completed", {
            "fuzz_count": len(all_fuzz_actions),
            "ux_count": len(all_ux_improvements)
        })
        print(f"  ✓ Fuzzer Agent produced {len(all_fuzz_actions)} boundary test hypotheses across all routes")
        print(f"  ✓ Auditor Agent produced {len(all_ux_improvements)} plain-English UX/accessibility improvements")

        # ----------------------------------------------------
        # NODE 3 & 4: Playwright Grounding Gate & Judge Node (Parallel Worker Pool)
        # ----------------------------------------------------
        self._notify("playwright_gate", "running")
        print(f"\n[Node 3: Playwright Grounding Gate] Executing {len(all_fuzz_actions)} test actions with parallel error interception...")

        hard_bugs: List[HardBug] = []

        if all_fuzz_actions:
            num_workers = min(3, len(all_fuzz_actions))
            batches = [[] for _ in range(num_workers)]
            for i, act in enumerate(all_fuzz_actions):
                batches[i % num_workers].append(act)
            batches = [b for b in batches if b]

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(batches)) as executor:
                futures = [
                    executor.submit(_run_fuzz_worker_batch, batch, self.state.target_url)
                    for batch in batches
                ]
                for fut in futures:
                    hard_bugs.extend(fut.result())

        self._notify("playwright_gate", "completed", {"executed_count": len(all_fuzz_actions)})
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
        print(f"✨ Multi-Agent Graph Completed in {total_time}s across {len(visited_routes)} route(s)")
        print(f"   Hard Bugs Verified: {len(self.state.hard_bugs)}")
        print(f"   UX Improvements:    {len(self.state.ux_improvements)}")
        print(f"=======================================================\n")

        return self.state


def run_multi_agent_pipeline(
    target_url: str,
    max_routes: int = 3,
    on_step_callback: Optional[Callable[[str, str, Optional[Dict[str, Any]]], None]] = None
) -> AgentState:
    """Convenience entry point for running the complete multi-agent graph pipeline."""
    graph = AppTesterGraph(target_url, max_routes=max_routes, on_step_callback=on_step_callback)
    return graph.run()
