import json
from typing import List, Dict, Any
from openai import OpenAI
from tester.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from tester.schema import UXImprovement, AuditorOutput

AUDITOR_SYSTEM_PROMPT = """You are a specialized WCAG Accessibility and Human-Centered UX Auditor Agent.
Your mission is to inspect the sanitized DOM structure of an application and uncover human friction, accessibility compliance barriers, and usability ambiguities.

Focus areas:
1. Form Accessibility (WCAG 2.1 A/AA): Form controls lacking an associated `<label>` element, title, or ARIA description.
2. Graphic Accessibility: Images (`<img>`) without meaningful `alt` descriptions, causing screen reader confusion.
3. User Flow Clarity & Microcopy: Buttons with ambiguous copy that don't clearly state what action will occur, or inputs lacking formatting hints/placeholders.
4. Interactive Feedback: Missing status regions or instructions that leave users unsure whether an action succeeded.

IMPORTANT TONE & CLARITY INSTRUCTIONS:
Write every `issue`, `impact_rationale`, and `suggested_fix` in SIMPLE, INTUITIVE, JARGON-FREE PLAIN ENGLISH that a non-technical Product Manager or Founder can immediately grasp.
- Avoid developer jargon like "lacks an associated <label> element", "missing ARIA role", or "needs fieldset/legend" in the primary issue title.
- Explain the real-world human problem:
  * Example for missing label: "The quantity box has no visible title, so shoppers don't know what number to enter."
  * Example for missing image alt: "The store header logo has no text description, making it completely invisible to blind customers using voice screen readers."
  * Example for unclear button: "The 'Live Rates' button doesn't explain whether clicking it calculates a preview or charges a fee."
- In `suggested_fix`: Provide a simple 1-sentence action followed by the clean HTML/CSS fix.

You MUST return ONLY a JSON object matching this schema:
{
  "ux_improvements": [
    {
      "category": "Accessibility" | "Layout" | "Usability" | "Copywriting",
      "selector": "#element-id",
      "issue": "Simple, jargon-free description of the problem",
      "impact_rationale": "Why this matters: user confusion, friction, or accessibility barrier",
      "suggested_fix": "Clear action followed by developer snippet"
    }
  ]
}
"""

def generate_fallback_audit(dom_elements: List[Dict[str, Any]]) -> List[UXImprovement]:
    """Deterministic fallback UX & Accessibility auditor for zero-crash offline execution."""
    improvements: List[UXImprovement] = []
    seen_selectors = set()

    for item in dom_elements:
        tag = item.get("tag")
        elem_id = item.get("id")
        selector = item.get("selector") or (f"#{elem_id}" if elem_id else tag)

        if selector in seen_selectors:
            continue

        if tag == "input":
            has_label = item.get("has_associated_label", False)
            aria_label = item.get("aria_label")
            if not has_label and not aria_label:
                seen_selectors.add(selector)
                name_hint = item.get("placeholder") or item.get("name") or elem_id or "Input Field"
                improvements.append(UXImprovement(
                    category="Accessibility",
                    selector=selector,
                    issue=f"The '{name_hint}' input box has no visible title or label above it.",
                    impact_rationale="Shoppers have to guess what this box is for, and blind customers using voice screen readers cannot hear any description, leading to confusion and abandoned purchases.",
                    suggested_fix=f"Add a clear title like '{name_hint}' above the box:\n<label for=\"{elem_id or 'input-field'}\">{name_hint}</label>"
                ))

        elif tag == "img":
            if not item.get("has_alt"):
                seen_selectors.add(selector)
                improvements.append(UXImprovement(
                    category="Accessibility",
                    selector=selector,
                    issue="The store header icon has no text description attached to it.",
                    impact_rationale="Visually impaired customers using screen reading software cannot tell what this image represents or may hear confusing file code read out loud.",
                    suggested_fix="Add a short descriptive explanation for screen readers:\nalt=\"Company store logo\" (or alt=\"\" if purely decorative)."
                ))

        elif tag == "button":
            text = (item.get("text") or "").strip()
            if text in ["Go", "Click Here", "Submit", "Rate"]:
                seen_selectors.add(selector)
                improvements.append(UXImprovement(
                    category="Usability",
                    selector=selector,
                    issue=f"The button text '{text}' is vague and does not clarify the outcome.",
                    impact_rationale="Shoppers may hesitate to click because they cannot tell whether this will trigger a calculation or finalize a transaction.",
                    suggested_fix=f"Update button copy to be specific and action-oriented (e.g. 'Calculate Shipping Rates' or 'Apply Discount Code')."
                ))

    return improvements


def run_auditor_agent(dom_elements: List[Dict[str, Any]]) -> List[UXImprovement]:
    """
    Executes the WCAG & UX Auditor Agent node.
    Returns plain-English accessibility and human experience improvements.
    """
    if not LLM_API_KEY:
        print("[Agent: Auditor] No API key detected. Running deterministic fallback auditor.")
        return generate_fallback_audit(dom_elements)

    try:
        print(f"[Agent: Auditor] Auditing accessibility & UX via {LLM_PROVIDER.upper()} ({LLM_MODEL})...")
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        user_content = f"Interactive DOM Elements for WCAG & Usability Audit:\n{json.dumps(dom_elements, indent=2)}\n\nRespond with a valid JSON object containing 'ux_improvements'."

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            raw_json = response.choices[0].message.content
        except Exception as api_err:
            if "json_validate_failed" in str(api_err) or "400" in str(api_err):
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.1
                )
                raw_json = response.choices[0].message.content
            else:
                raise api_err

        clean_json = raw_json.strip()
        start_idx = clean_json.find("{")
        end_idx = clean_json.rfind("}")
        if start_idx != -1 and end_idx != -1:
            clean_json = clean_json[start_idx:end_idx + 1]

        parsed = json.loads(clean_json)

        # Normalize synonym keys
        if "ux_improvements" not in parsed:
            for syn in ["improvements", "findings", "issues", "audit_results", "ux_issues"]:
                if syn in parsed:
                    parsed["ux_improvements"] = parsed.pop(syn)
                    break

        out = AuditorOutput.model_validate(parsed)

        # Deduplicate by selector to avoid repetitive cards
        unique_improvements: List[UXImprovement] = []
        seen = set()
        for item in out.ux_improvements:
            if item.selector not in seen:
                seen.add(item.selector)
                unique_improvements.append(item)

        return unique_improvements if unique_improvements else generate_fallback_audit(dom_elements)

    except Exception as err:
        print(f"[Agent: Auditor Warning] Auditor agent encountered error ({err}). Using fallback.")
        return generate_fallback_audit(dom_elements)
