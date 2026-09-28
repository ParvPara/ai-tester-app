import json
from typing import List, Dict, Any
from openai import OpenAI
from tester.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from tester.schema import FuzzAction, FuzzerOutput

FUZZER_SYSTEM_PROMPT = """You are an Adversarial Fuzzing Agent and Penetration Testing specialist.
Your mission is to probe the target web application for unhandled client-side runtime crashes, validation bypasses, and broken API endpoints.

Analyze the sanitized DOM tree and generate targeted boundary fuzz actions (`fuzz_actions`):
1. Numeric inputs: negative numbers (-1, -5), zero (0), float values, integer overflows (999999999).
2. Freeform text & promo inputs: SQL injection (' OR 1=1;--), XSS/HTML tags (<script>, <svg/onload=alert(1)>), very long strings ("A" * 500), empty strings.
3. Interactive buttons: YOU MUST generate a 'click' action for EVERY button found in the DOM (e.g. promo claim buttons, rate calculation buttons, submit buttons) to probe network endpoints.
4. Form submissions: clicking submit buttons with empty or invalid states.

For every action, provide:
- `rationale`: What is being tested and why.
- `user_scenario`: What a real human user would do to trigger this condition.
- `business_impact`: What happens to the customer and business if it breaks.

You MUST return ONLY a JSON object matching this schema:
{
  "fuzz_actions": [
    {
      "selector": "#element-id",
      "action_type": "fill" or "click",
      "payload": "fuzz-payload",
      "rationale": "Testing intent in plain English",
      "user_scenario": "How a real user triggers this scenario",
      "business_impact": "How this bug harms the user or business if it crashes"
    }
  ]
}
"""

def generate_fallback_fuzz(dom_elements: List[Dict[str, Any]]) -> List[FuzzAction]:
    """Deterministic fallback fuzzer for zero-crash offline execution."""
    actions: List[FuzzAction] = []
    
    for item in dom_elements:
        tag = item.get("tag")
        elem_id = item.get("id")
        selector = item.get("selector") or (f"#{elem_id}" if elem_id else tag)

        if tag == "input":
            elem_type = item.get("type")
            if elem_type == "number" or "quantity" in (elem_id or ""):
                actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="-5",
                    rationale="Test boundary condition with negative integer quantity input",
                    user_scenario="A customer makes a typo or tries to remove items by typing -5 instead of using a delete button",
                    business_impact="The checkout crashes on an unhandled tax calculation error, preventing the order from going through and losing the sale"
                ))
            elif elem_type == "text" or "promo" in (elem_id or ""):
                actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="INVALID_PROMO_999",
                    rationale="Test non-existent promo code to probe API response handling",
                    user_scenario="A shopper copies and pastes an expired or mistyped discount code found on social media",
                    business_impact="The promo lookup triggers a failed network call; if not handled, the customer sees an error and abandons their cart"
                ))
            elif "note" in (elem_id or ""):
                actions.append(FuzzAction(
                    selector=selector,
                    action_type="fill",
                    payload="<script>alert(1)</script>",
                    rationale="Probe freeform text input with script injection payload",
                    user_scenario="A user types special characters or quotes in their delivery note",
                    business_impact="If the client-side parser fails, order submission halts entirely"
                ))

        elif tag == "button" or tag == "form":
            elem_type = item.get("type")
            if elem_type == "submit" or tag == "form":
                actions.append(FuzzAction(
                    selector=selector if tag == "button" else "#submit-order-btn",
                    action_type="click",
                    payload="",
                    rationale="Click submit button to test form submission with current input values",
                    user_scenario="A customer rushes through checkout and clicks Place Order before completing required fields",
                    business_impact="The app crashes with an uncaught runtime error rather than showing a friendly validation notice"
                ))
            else:
                actions.append(FuzzAction(
                    selector=selector,
                    action_type="click",
                    payload="",
                    rationale="Trigger secondary action button to verify client network calls",
                    user_scenario="A shopper clicks an optional button to check live rates or apply a promotion",
                    business_impact="If the background API fails, the user is left waiting or confused by an unhandled service error"
                ))

    if not any(f.payload == "" and f.action_type == "click" for f in actions):
        actions.append(FuzzAction(
            selector="#submit-order-btn",
            action_type="click",
            payload="",
            rationale="Submit empty form to check client-side boundary validation",
            user_scenario="A shopper clicks Place Order without filling in their details",
            business_impact="The app crashes instead of gently highlighting missing fields"
        ))

    return actions


def run_fuzzer_agent(dom_elements: List[Dict[str, Any]]) -> List[FuzzAction]:
    """
    Executes the Adversarial Fuzzer Agent node.
    Returns targeted boundary test cases.
    """
    if not LLM_API_KEY:
        print("[Agent: Fuzzer] No API key detected. Running deterministic fallback fuzzer.")
        return generate_fallback_fuzz(dom_elements)

    try:
        print(f"[Agent: Fuzzer] Generating boundary attack vectors via {LLM_PROVIDER.upper()} ({LLM_MODEL})...")
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        user_content = f"Interactive DOM Elements:\n{json.dumps(dom_elements, indent=2)}"

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": FUZZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        raw_json = response.choices[0].message.content
        parsed = json.loads(raw_json)

        # Normalize possible synonym keys
        if "fuzz_actions" not in parsed:
            for syn in ["actions", "tests", "test_cases", "boundary_actions"]:
                if syn in parsed:
                    parsed["fuzz_actions"] = parsed.pop(syn)
                    break

        out = FuzzerOutput.model_validate(parsed)

        # Ensure all interactive buttons in the DOM have a corresponding test action
        existing_click_selectors = {a.selector for a in out.fuzz_actions if a.action_type == "click"}
        for item in dom_elements:
            if item.get("tag") == "button":
                btn_id = item.get("id")
                sel = item.get("selector") or (f"#{btn_id}" if btn_id else "button")
                if sel not in existing_click_selectors:
                    btn_text = item.get("text") or sel
                    out.fuzz_actions.append(FuzzAction(
                        selector=sel,
                        action_type="click",
                        payload="",
                        rationale=f"Trigger action button '{btn_text}' to test backend API response and client-side stability",
                        user_scenario=f"A shopper clicks '{btn_text}' expecting an immediate result",
                        business_impact="If the network endpoint fails or crashes, the customer is stranded and transaction fails"
                    ))
                    existing_click_selectors.add(sel)

        return out.fuzz_actions

    except Exception as err:
        print(f"[Agent: Fuzzer Warning] Fuzzer agent encountered error ({err}). Using fallback.")
        return generate_fallback_fuzz(dom_elements)
