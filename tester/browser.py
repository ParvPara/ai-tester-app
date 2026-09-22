from typing import List, Dict, Any, Tuple
from playwright.sync_api import sync_playwright, Page, Response, Error as PlaywrightError
from tester.config import HEADLESS, BROWSER_TIMEOUT_MS

class BrowserTelemetry:
    def __init__(self):
        self.page_errors: List[str] = []
        self.network_errors: List[Dict[str, Any]] = []

    def clear_logs(self):
        self.page_errors.clear()
        self.network_errors.clear()

    def _on_page_error(self, error: Exception):
        self.page_errors.append(str(error))

    def _on_response(self, response: Response):
        if response.status >= 400:
            self.network_errors.append({
                "url": response.url,
                "status": response.status,
                "status_text": response.status_text
            })


def extract_sanitized_dom(page: Page) -> List[Dict[str, Any]]:
    """
    Extracts lightweight, sanitized representation of interactive elements (<input>, <button>, <form>, <a>, <select>).
    Strips scripts, heavy CSS, and inline styles to keep payload under ~500 tokens.
    """
    elements_data = page.evaluate("""
        () => {
            const items = [];
            const selector = 'input, button, select, textarea, a, form';
            const nodes = document.querySelectorAll(selector);

            nodes.forEach(node => {
                const tag = node.tagName.toLowerCase();
                let labelText = '';
                
                // Find associated label if input
                if (node.id) {
                    const label = document.querySelector(`label[for="${node.id}"]`);
                    if (label) labelText = label.innerText.trim();
                }
                if (!labelText && node.closest('label')) {
                    labelText = node.closest('label').innerText.trim();
                }

                items.push({
                    tag: tag,
                    id: node.id || null,
                    name: node.getAttribute('name') || null,
                    type: node.getAttribute('type') || null,
                    placeholder: node.getAttribute('placeholder') || null,
                    aria_label: node.getAttribute('aria-label') || null,
                    text: node.innerText ? node.innerText.trim() : null,
                    has_associated_label: Boolean(labelText),
                    associated_label: labelText || null,
                    value: node.value || null
                });
            });

            // Also check for images without alt tags (UX/Accessibility flaw inspection)
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                items.push({
                    tag: 'img',
                    id: img.id || null,
                    src: img.getAttribute('src') ? img.getAttribute('src').substring(0, 40) + '...' : null,
                    alt: img.getAttribute('alt'),
                    has_alt: Boolean(img.getAttribute('alt'))
                });
            });

            return items;
        }
    """)
    return elements_data


def inspect_page(target_url: str) -> Tuple[List[Dict[str, Any]], BrowserTelemetry]:
    """
    Launches Playwright Chromium, attaches telemetry listeners, navigates to target_url,
    and returns extracted DOM items along with the telemetry instance.
    """
    telemetry = BrowserTelemetry()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        # Attach telemetry listeners before navigation
        page.on("pageerror", telemetry._on_page_error)
        page.on("response", telemetry._on_response)

        page.goto(target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="networkidle")
        dom_elements = extract_sanitized_dom(page)

        browser.close()

    return dom_elements, telemetry
