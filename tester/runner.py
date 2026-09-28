import urllib.parse
from typing import List, Tuple
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from tester.config import HEADLESS, BROWSER_TIMEOUT_MS, TRACKER_IGNORE_DOMAINS
from tester.schema import AuditResponse, HardBug, UXImprovement
from tester.browser import BrowserTelemetry


def execute_fuzz_tests(target_url: str, audit: AuditResponse) -> Tuple[List[HardBug], List[UXImprovement]]:
    """
    Executes generated fuzz actions against the live target application.
    Enforces a Strict Verification Gate: an issue is ONLY classified as a HardBug
    if Playwright actively captures an uncaught JS exception (pageerror) or an HTTP >= 400 network failure.
    """
    hard_bugs: List[HardBug] = []
    target_netloc = urllib.parse.urlparse(target_url).netloc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        telemetry = BrowserTelemetry()
        page.on("pageerror", telemetry._on_page_error)
        page.on("response", telemetry._on_response)

        # Initial navigation with domcontentloaded for high compatibility
        try:
            page.goto(target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(600)
        except Exception as err:
            hard_bugs.append(HardBug(
                title="Target Application Unreachable",
                severity="Critical",
                selector="N/A",
                action_type="goto",
                payload=target_url,
                error_message=f"Failed to navigate to target URL: {str(err)}",
                reproduction_steps=[f"1. Navigate to {target_url}"]
            ))
            browser.close()
            return hard_bugs, audit.ux_improvements

        # Execute each fuzz action sequentially
        for idx, action in enumerate(audit.fuzz_actions, start=1):
            telemetry.clear_logs()
            repro_steps: List[str] = [f"1. Open target URL: {target_url}"]

            try:
                if action.action_type == "fill":
                    repro_steps.append(f"2. Fill input '{action.selector}' with payload: '{action.payload}'")
                    page.fill(action.selector, action.payload or "", timeout=2000)
                elif action.action_type == "click":
                    repro_steps.append(f"2. Click element '{action.selector}'")
                    page.click(action.selector, timeout=2000)

                # Small delay to allow async handlers/network requests to trigger
                page.wait_for_timeout(400)

            except PlaywrightError:
                # Element not interactable or off-screen, continue gracefully
                pass

            # --- STRICT VERIFICATION GATE ---
            # 1. Uncaught JS Runtime Exception Gate
            if telemetry.page_errors:
                for err_msg in telemetry.page_errors:
                    hard_bugs.append(HardBug(
                        title="Uncaught JavaScript Runtime Exception",
                        severity="Critical",
                        selector=action.selector,
                        action_type=action.action_type,
                        payload=action.payload,
                        error_message=err_msg,
                        test_intent=action.rationale or "Testing boundary conditions on form controls",
                        user_scenario=action.user_scenario or "An end user inputs unexpected data or clicks before completing all fields",
                        business_impact=action.business_impact or "The application crashes with an unhandled error, leaving the customer stranded and unable to proceed",
                        reproduction_steps=repro_steps
                    ))

            # 2. HTTP Network Failure (4xx/5xx) Gate
            if telemetry.network_errors:
                for net_err in telemetry.network_errors:
                    err_url = net_err['url']
                    err_netloc = urllib.parse.urlparse(err_url).netloc
                    
                    # Filter out third-party advertising/tracking noise
                    if any(tracker in err_netloc for tracker in TRACKER_IGNORE_DOMAINS):
                        continue

                    hard_bugs.append(HardBug(
                        title=f"Failed Network Request (HTTP {net_err['status']})",
                        severity="High",
                        selector=action.selector,
                        action_type=action.action_type,
                        payload=action.payload,
                        error_message=f"Request to {err_url} failed with {net_err['status']} {net_err['status_text']}",
                        status_code=net_err['status'],
                        test_intent=action.rationale or "Testing backend API endpoint response handling",
                        user_scenario=action.user_scenario or "An end user interacts with a feature that triggers an external API call",
                        business_impact=action.business_impact or "The feature fails silently or displays a broken network message, causing customer frustration",
                        reproduction_steps=repro_steps
                    ))

        browser.close()

    return hard_bugs, audit.ux_improvements
