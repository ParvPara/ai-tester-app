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
    Prioritizes form controls and caps links/images to guarantee payload stays strictly under 500 tokens.
    """
    elements_data = page.evaluate("""
        () => {
            const items = [];

            // 1. High priority: Form interactive controls
            const controls = document.querySelectorAll('input:not([type="hidden"]), button, select, textarea, form');
            controls.forEach(node => {
                if (items.length >= 20) return;
                const tag = node.tagName.toLowerCase();
                let labelText = '';
                
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
                    text: node.innerText ? node.innerText.trim().substring(0, 30) : null,
                    has_associated_label: Boolean(labelText),
                    associated_label: labelText || null,
                    value: node.value || null
                });
            });

            // 2. Medium priority: Primary navigation links (capped to 5)
            const links = document.querySelectorAll('a[href]:not([href^="#"]):not([href^="javascript"])');
            let linkCount = 0;
            links.forEach(a => {
                if (linkCount >= 5 || items.length >= 25) return;
                const text = a.innerText ? a.innerText.trim() : '';
                if (text && text.length > 1) {
                    items.push({
                        tag: 'a',
                        id: a.id || null,
                        href: a.getAttribute('href'),
                        text: text.substring(0, 30)
                    });
                    linkCount++;
                }
            });

            // 3. Accessibility flaw inspection: images without alt attributes (capped to 5)
            const images = document.querySelectorAll('img');
            let imgCount = 0;
            images.forEach(img => {
                if (imgCount >= 5 || items.length >= 30) return;
                const alt = img.getAttribute('alt');
                if (!alt) {
                    items.push({
                        tag: 'img',
                        id: img.id || null,
                        src: img.getAttribute('src') ? img.getAttribute('src').substring(0, 40) + '...' : null,
                        alt: null,
                        has_alt: false
                    });
                    imgCount++;
                }
            });

            return items;
        }
    """)
    return elements_data


def inspect_page(target_url: str) -> Tuple[List[Dict[str, Any]], BrowserTelemetry]:
    """
    Launches Playwright Chromium, attaches telemetry listeners, navigates to target_url,
    and returns extracted DOM items along with the telemetry instance.
    Uses domcontentloaded for high compatibility with modern sites (Shopify, SPAs).
    """
    telemetry = BrowserTelemetry()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Attach telemetry listeners before navigation
        page.on("pageerror", telemetry._on_page_error)
        page.on("response", telemetry._on_response)

        try:
            # Use domcontentloaded to avoid hanging on background analytics/beacons
            page.goto(target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(800) # Short grace period for client hydration
        except Exception:
            # Fallback to load state if domcontentloaded raises error
            page.goto(target_url, timeout=BROWSER_TIMEOUT_MS, wait_until="load")

        dom_elements = extract_sanitized_dom(page)
        browser.close()

    return dom_elements, telemetry
