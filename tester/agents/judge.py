import urllib.parse
from typing import List, Dict, Any, Optional
from tester.config import TRACKER_IGNORE_DOMAINS
from tester.schema import FuzzAction, HardBug

def is_tracker_noise(url: str) -> bool:
    """Filters out advertising, analytics, and telemetry tracker domain failures."""
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return any(tracker in netloc for tracker in TRACKER_IGNORE_DOMAINS)
    except Exception:
        return False

def evaluate_execution_telemetry(
    action: FuzzAction,
    target_url: str,
    page_errors: List[str],
    network_errors: List[Dict[str, Any]],
    repro_steps: List[str]
) -> List[HardBug]:
    """
    Judge Node: Strictly evaluates Playwright telemetry against the Fuzzer's test action.
    
    Zero False-Positive Invariant:
    A hard bug is ONLY created if an unhandled JavaScript exception or HTTP 4xx/5xx failure
    was physically intercepted by browser telemetry during execution of this action.
    Hypothetical or theoretical defects are strictly rejected.
    """
    verified_bugs: List[HardBug] = []
    seen_signatures = set()

    # 1. Gate: Unhandled Client-Side JavaScript Runtime Exceptions
    for err_msg in page_errors:
        clean_err = str(err_msg).strip()
        sig = f"js:{action.selector}:{clean_err}"
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        # Determine severity based on crash type
        severity = "Critical" if any(k in clean_err for k in ["TypeError", "RangeError", "SyntaxError", "DOMException", "Uncaught"]) else "High"
        
        # Enrich test intent & impact
        intent = action.rationale or f"Testing boundary resilience on '{action.selector}'"
        scenario = action.user_scenario or f"A user interacts with element '{action.selector}' under unexpected data conditions"
        impact = action.business_impact or "The application freezes or crashes with an unhandled exception, leaving the user stranded"

        verified_bugs.append(HardBug(
            title="Uncaught JavaScript Runtime Exception",
            severity=severity,
            selector=action.selector,
            action_type=action.action_type,
            payload=action.payload,
            error_message=clean_err,
            status_code=None,
            test_intent=intent,
            user_scenario=scenario,
            business_impact=impact,
            reproduction_steps=list(repro_steps),
            page_url=action.page_url or target_url
        ))

    # 2. Gate: HTTP 4xx / 5xx Network Failures
    for net_err in network_errors:
        err_url = net_err.get("url", "")
        status = net_err.get("status", 0)
        status_text = net_err.get("status_text", "Error")

        # Reject tracker noise (Google Analytics, Sentry, Facebook Pixel, etc.)
        if is_tracker_noise(err_url):
            continue

        sig = f"net:{action.selector}:{status}:{err_url}"
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        severity = "Critical" if status >= 500 else "High"
        intent = action.rationale or f"Testing network endpoint resilience triggered by '{action.selector}'"
        scenario = action.user_scenario or f"A customer triggers an action requiring server communication via '{action.selector}'"
        impact = action.business_impact or f"The feature fails with HTTP {status}, breaking key functionality and causing user friction"

        verified_bugs.append(HardBug(
            title=f"Failed Network Request (HTTP {status})",
            severity=severity,
            selector=action.selector,
            action_type=action.action_type,
            payload=action.payload,
            error_message=f"Request to {err_url} failed with {status} {status_text}",
            status_code=status,
            test_intent=intent,
            user_scenario=scenario,
            business_impact=impact,
            reproduction_steps=list(repro_steps),
            page_url=action.page_url or target_url
        ))

    return verified_bugs
