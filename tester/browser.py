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

                let sel = tag;
                if (node.id) {
                    sel = `#${node.id}`;
                } else if (node.getAttribute('name')) {
                    sel = `${tag}[name="${node.getAttribute('name')}"]`;
                } else if (node.getAttribute('placeholder')) {
                    sel = `${tag}[placeholder="${node.getAttribute('placeholder').substring(0, 20)}"]`;
                } else if (node.getAttribute('type')) {
                    sel = `${tag}[type="${node.getAttribute('type')}"]`;
                }

                items.push({
                    tag: tag,
                    selector: sel,
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


def normalize_route_url(url: str) -> str:
    """Normalizes URL by stripping fragments, queries, trailing slashes, and index.html aliases."""
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    clean_path = parsed.path.rstrip("/")
    for alias in ["/index.html", "/index.htm", "/index.php"]:
        if clean_path.endswith(alias):
            clean_path = clean_path[:-len(alias)].rstrip("/")
            break
    clean_url = f"{parsed.scheme}://{parsed.netloc}{clean_path}".rstrip("/")
    return clean_url


def extract_same_origin_routes(page: Page, base_url: str, max_routes: int = 3) -> List[str]:
    """
    Extracts unique same-origin navigation routes directly from the live DOM via Playwright.
    Pure black-box discovery strictly over HTTP; zero access to backend source files.
    """
    import urllib.parse
    base_parsed = urllib.parse.urlparse(base_url)
    base_netloc = base_parsed.netloc.lower()
    norm_base = normalize_route_url(base_url)

    raw_hrefs = page.evaluate("""
        () => {
            const anchors = Array.from(document.querySelectorAll('a[href]'));
            return anchors.map(a => a.getAttribute('href')).filter(Boolean);
        }
    """)

    discovered: List[str] = []
    seen = {norm_base, base_url.rstrip("/"), base_url}

    for href in raw_hrefs:
        href_str = str(href).strip()
        if not href_str or href_str.startswith("#") or href_str.startswith("javascript:") or href_str.startswith("mailto:"):
            continue

        absolute_url = urllib.parse.urljoin(base_url, href_str)
        norm_url = normalize_route_url(absolute_url)
        parsed = urllib.parse.urlparse(absolute_url)

        if parsed.netloc.lower() == base_netloc and norm_url not in seen:
            if not any(absolute_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg", ".css", ".js", ".pdf", ".zip"]):
                seen.add(norm_url)
                discovered.append(absolute_url)
                if len(discovered) >= max_routes:
                    break

    return discovered


def inspect_page(target_url: str) -> Tuple[List[Dict[str, Any]], List[str], BrowserTelemetry]:
    """
    Launches Playwright Chromium, attaches telemetry listeners, navigates to target_url,
    and returns extracted DOM items, discovered same-origin routes, and telemetry.
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
        discovered_routes = extract_same_origin_routes(page, target_url)
        browser.close()

    return dom_elements, discovered_routes, telemetry
