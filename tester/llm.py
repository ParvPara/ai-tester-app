import json
from typing import List, Dict, Any
from openai import OpenAI
from tester.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from tester.schema import AuditResponse, FuzzAction, UXImprovement

SYSTEM_PROMPT = """You are an expert QA Automation, UX Design, and Accessibility Auditor.
Your task is to analyze a sanitized DOM tree of an application and generate:
1. Targeted boundary/edge-case fuzz actions (`fuzz_actions`) to probe for runtime JavaScript crashes, validation bugs, or network errors (e.g., negative numbers, zero, empty input submit, special characters, injection strings, clicking action buttons).
2. Semantic, layout, or accessibility flaws (`ux_improvements`) detected in the DOM structure (e.g., inputs missing <label> or aria-label, images missing alt text, buttons lacking clear affordance, missing guidance).

For every UX/accessibility improvement, you MUST explicitly provide the `impact_rationale` explaining:
- Why this issue matters to the end user.
- What specific confusion, hesitation, or barrier it creates (e.g., "Screen reader users will not know what to input", "Users may be confused about how to submit the form without a clear call-to-action button", "Users are unsure if discount codes are case-sensitive").

You MUST output ONLY a valid JSON object matching this exact structure:
{
  "fuzz_actions": [
    {
      "selector": "#element-id",
      "action_type": "fill" or "click",
      "payload": "fuzz-string-or-number",
      "rationale": "Reason for testing this boundary"
    }
  ],
  "ux_improvements": [
    {
      "category": "Accessibility" or "Layout" or "Usability" or "Copywriting",
      "selector": "#element-id",
      "issue": "Concise issue description",
      "impact_rationale": "Why this matters: user confusion, friction, or accessibility barrier caused by this defect",
      "suggested_fix": "Clear developer remediation or drop-in code snippet"
    }
  ]
}
"""

def generate_fallback_audit(dom_elements: List[Dict[str, Any]]) -> AuditResponse:
    """
    Fallback rule-based audit generator to ensure zero demo crashes if API key is absent or unreachable.
    """
    fuzz_actions: List[FuzzAction] = []
    ux_improvements: List[UXImprovement] = []

    for item in dom_elements:
        tag = item.get("tag")
        elem_id = item.get("id")
        selector = f"#{elem_id}" if elem_id else tag

        if tag == "input":
            # Rule-based fuzz action: boundary values
            if item.get("type") == "number" or "quantity" in (elem_id or ""):
                fuzz_actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="-5",
                    rationale="Test boundary condition with negative integer quantity input"
                ))
            elif item.get("type") == "text" or "promo" in (elem_id or ""):
                fuzz_actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="INVALID_PROMO_999",
                    rationale="Test non-existent promo code to probe API response handling"
                ))
            
            # UX Flaw check: missing associated label
            if not item.get("has_associated_label") and not item.get("aria_label"):
                ux_improvements.append(UXImprovement(
                    category="Accessibility",
                    selector=selector,
                    issue="Input field lacks an associated <label> element or 'aria-label' attribute.",
                    impact_rationale="Screen readers cannot announce what this input field is for, leaving visually impaired users unable to understand what data to enter and likely causing form abandonment.",
                    suggested_fix=f"Add <label for=\"{elem_id or 'input-id'}\">Label Name</label> or aria-label to support assistive technology."
                ))

        elif tag == "button" or tag == "form":
            elem_type = item.get("type")
            if elem_type == "submit" or tag == "form":
                fuzz_actions.append(FuzzAction(
                    selector=selector if tag == "button" else "#submit-order-btn",
                    action_type="click",
                    payload="",
                    rationale="Click submit button to test form submission with current input values"
                ))
            else:
                fuzz_actions.append(FuzzAction(
                    selector=selector,
                    action_type="click",
                    payload="",
                    rationale="Trigger secondary action button to verify client network calls"
                ))

        elif tag == "img":
            if not item.get("has_alt"):
                ux_improvements.append(UXImprovement(
                    category="Accessibility",
                    selector=selector,
                    issue="Image element is missing an 'alt' text description attribute.",
                    impact_rationale="Assistive screen readers will announce confusing raw file paths instead of describing the image, creating cognitive friction for visually impaired users.",
                    suggested_fix="Add descriptive alt=\"Header logo\" attribute, or alt=\"\" if decorative."
                ))

    # Add empty submit fuzz action if not present
    if not any(f.payload == "" and f.action_type == "click" for f in fuzz_actions):
        fuzz_actions.append(FuzzAction(
            selector="#submit-order-btn",
            action_type="click",
            payload="",
            rationale="Submit empty form to check client-side boundary validation"
        ))

    return AuditResponse(fuzz_actions=fuzz_actions, ux_improvements=ux_improvements)


def analyze_dom_with_llm(dom_elements: List[Dict[str, Any]]) -> AuditResponse:
    """
    Sends extracted DOM representation to LLM reasoning engine (Groq LPU or OpenAI).
    Falls back to deterministic rule engine if API key is absent or network fails.
    """
    if not LLM_API_KEY:
        print("[Notice] No LLM API key detected. Using deterministic rule engine fallback.")
        return generate_fallback_audit(dom_elements)

    try:
        print(f"[AI Engine] Reasoning via {LLM_PROVIDER.upper()} ({LLM_MODEL})...")
        
        client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL
        )
        user_content = f"Extracted DOM Interactive Elements:\n{json.dumps(dom_elements, indent=2)}"

        if LLM_PROVIDER == "openai" and LLM_BASE_URL is None:
            # Native OpenAI structured outputs
            response = client.beta.chat.completions.parse(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                response_format=AuditResponse,
                temperature=0.0
            )
            return response.choices[0].message.parsed
        else:
            # Groq / OpenAI-compatible JSON mode
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            raw_json = response.choices[0].message.content
            parsed_data = json.loads(raw_json)
            
            # Normalize possible synonym keys
            if "ux_improvements" not in parsed_data:
                for syn in ["ux_issues", "improvements", "accessibility_improvements", "accessibility_flaws", "ux"]:
                    if syn in parsed_data:
                        parsed_data["ux_improvements"] = parsed_data.pop(syn)
                        break
            if "fuzz_actions" not in parsed_data:
                for syn in ["tests", "test_cases", "actions", "boundary_actions"]:
                    if syn in parsed_data:
                        parsed_data["fuzz_actions"] = parsed_data.pop(syn)
                        break

            return AuditResponse.model_validate(parsed_data)

    except Exception as err:
        print(f"[Warning] {LLM_PROVIDER.upper()} API call failed ({err}). Falling back to deterministic rule engine.")
        return generate_fallback_audit(dom_elements)
