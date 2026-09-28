import json
from typing import List, Dict, Any
from openai import OpenAI
from tester.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from tester.schema import AuditResponse, FuzzAction, UXImprovement

SYSTEM_PROMPT = """<ROLE>
You are an expert QA Automation, UX Design, and Accessibility Auditor.
</ROLE>

<TASK>
Analyze a sanitized DOM tree of an application and generate:
1. Targeted boundary/edge-case fuzz actions (`fuzz_actions`) to probe for runtime JavaScript crashes, validation bugs, or network errors.
2. Human-friendly, semantic, layout, or accessibility flaws (`ux_improvements`) detected in the DOM structure.
</TASK>

<BEHAVIOUR>
1. Fuzz Actions:
   - Numeric inputs: negative numbers, zero, float values, integer overflows.
   - Freeform text & promo inputs: SQL injection, script/HTML tags, very long strings, empty strings.
   - Action buttons: click action for buttons to probe network endpoints.
   - For every action, provide plain-English rationale, user_scenario, and business_impact.
2. UX Improvements:
   - Write every issue, impact_rationale, and suggested_fix in SIMPLE, NON-TECHNICAL, INTUITIVE PLAIN ENGLISH.
   - Avoid technical jargon in issue titles; describe the human problem directly (e.g. "The quantity box has no title or label, so shoppers don't know what number to enter.").
   - In suggested_fix, start with a 1-sentence plain-English action followed by the code snippet.
</BEHAVIOUR>

<CONTRAINTS>
- Use only valid selectors present in the provided DOM tree.
- Categorize UX improvements strictly as: "Accessibility", "Layout", "Usability", or "Copywriting".
- Return ONLY a valid JSON object matching the schema in OUTPUT without markdown wrapper or conversational text.
</CONTRAINTS>

<OUTPUT>
{
  "fuzz_actions": [
    {
      "selector": "#element-id",
      "action_type": "fill",
      "payload": "-1",
      "rationale": "Testing intent in plain English",
      "user_scenario": "How a real user triggers this scenario",
      "business_impact": "How this bug harms the user or business if it crashes"
    }
  ],
  "ux_improvements": [
    {
      "category": "Accessibility",
      "selector": "#element-id",
      "issue": "Simple, jargon-free description of the problem",
      "impact_rationale": "Why this matters: user confusion, friction, or accessibility barrier caused by this defect",
      "suggested_fix": "Simple plain-English action followed by code snippet"
    }
  ]
}
</OUTPUT>"""

def generate_fallback_audit(dom_elements: List[Dict[str, Any]]) -> AuditResponse:
    """
    Fallback rule-based audit generator to ensure zero demo crashes if API key is absent or unreachable.
    """
    fuzz_actions: List[FuzzAction] = []
    ux_improvements: List[UXImprovement] = []
    seen_ux_selectors = set()

    for item in dom_elements:
        tag = item.get("tag")
        elem_id = item.get("id")
        selector = item.get("selector") or (f"#{elem_id}" if elem_id else tag)

        if tag == "input":
            # Rule-based fuzz action: boundary values
            if item.get("type") == "number" or "quantity" in (elem_id or ""):
                fuzz_actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="-5",
                    rationale="Test boundary condition with negative integer quantity input",
                    user_scenario="A customer makes a typo or tries to remove items by typing -5 instead of using a delete button",
                    business_impact="The checkout crashes on an unhandled tax calculation error, preventing the order from going through and losing the sale"
                ))
            elif item.get("type") == "text" or "promo" in (elem_id or ""):
                fuzz_actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="INVALID_PROMO_999",
                    rationale="Test non-existent promo code to probe API response handling",
                    user_scenario="A shopper copies and pastes an expired or mistyped discount code found on social media",
                    business_impact="The promo lookup triggers a failed network call; if not handled, the customer sees an error and abandons their cart"
                ))
            
            # UX Flaw check: missing associated label (deduplicated)
            if not item.get("has_associated_label") and not item.get("aria_label"):
                if selector not in seen_ux_selectors:
                    seen_ux_selectors.add(selector)
                    name_hint = item.get("placeholder") or item.get("name") or elem_id or "Input Field"
                    ux_improvements.append(UXImprovement(
                        category="Accessibility",
                        selector=selector,
                        issue=f"The '{name_hint}' input box has no visible title or label above it.",
                        impact_rationale="Shoppers have to guess what this box is for, and blind customers using voice screen readers cannot hear any description, leading to confusion and abandoned purchases.",
                        suggested_fix=f"Add a clear title like '{name_hint}' above the box:\n<label for=\"{elem_id or 'input-field'}\">{name_hint}</label>"
                    ))

        elif tag == "button" or tag == "form":
            elem_type = item.get("type")
            if elem_type == "submit" or tag == "form":
                fuzz_actions.append(FuzzAction(
                    selector=selector if tag == "button" else "#submit-order-btn",
                    action_type="click",
                    payload="",
                    rationale="Click submit button to test form submission with current input values",
                    user_scenario="A customer rushes through checkout and clicks 'Place Order' before completing required fields",
                    business_impact="The app crashes with an uncaught runtime error rather than showing a friendly validation notice"
                ))
            else:
                fuzz_actions.append(FuzzAction(
                    selector=selector,
                    action_type="click",
                    payload="",
                    rationale="Trigger secondary action button to verify client network calls",
                    user_scenario="A shopper clicks an optional button to check live rates or apply a promotion",
                    business_impact="If the background API fails, the user is left waiting or confused by an unhandled service error"
                ))

        elif tag == "img":
            if not item.get("has_alt"):
                ux_improvements.append(UXImprovement(
                    category="Accessibility",
                    selector=selector,
                    issue="The store header icon has no text description attached to it.",
                    impact_rationale="Visually impaired customers using screen reading software cannot tell what this image represents or may hear confusing file code read out loud.",
                    suggested_fix="Add a short descriptive explanation for screen readers:\nalt=\"Company store logo\" (or alt=\"\" if purely decorative)."
                ))

    # Add empty submit fuzz action if not present
    if not any(f.payload == "" and f.action_type == "click" for f in fuzz_actions):
        fuzz_actions.append(FuzzAction(
            selector="#submit-order-btn",
            action_type="click",
            payload="",
            rationale="Submit empty form to check client-side boundary validation",
            user_scenario="A shopper clicks Place Order without filling in their details",
            business_impact="The app crashes instead of gently highlighting missing fields"
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

            audit = AuditResponse.model_validate(parsed_data)
            
            # Deduplicate UX improvements so no selector is repeatedly reported
            seen_selectors = set()
            unique_ux = []
            for ux in audit.ux_improvements:
                if ux.selector not in seen_selectors:
                    seen_selectors.add(ux.selector)
                    unique_ux.append(ux)
            audit.ux_improvements = unique_ux
            return audit

    except Exception as err:
        print(f"[Warning] {LLM_PROVIDER.upper()} API call failed ({err}). Falling back to deterministic rule engine.")
        return generate_fallback_audit(dom_elements)
