import os
import re
import time
from typing import List
from tester.schema import HardBug, UXImprovement

CLEAN_STEP_RE = re.compile(r"^\d+\.\s*")

def render_terminal_report(hard_bugs: List[HardBug], ux_improvements: List[UXImprovement], elapsed_time: float, target_url: str):
    """Prints a clean, partitioned dual-bucket summary directly to the terminal."""
    print("\n" + "="*70)
    print(" APPTESTER — EXECUTIVE AUDIT REPORT")
    print(f" Target URL: {target_url}")
    print(f" Duration: {elapsed_time:.2f}s | Hard Defects: {len(hard_bugs)} | UX Findings: {len(ux_improvements)}")
    print("="*70 + "\n")

    # BUCKET 1: HARD BUGS
    print("BUCKET 1: HARD DEFECTS (VERIFIED RUNTIME & NETWORK EXCEPTIONS)")
    print("-" * 70)
    if not hard_bugs:
        print("  Zero hard defects detected.")
    else:
        for i, bug in enumerate(hard_bugs, start=1):
            print(f"  [{i}] [{bug.severity.upper()}] {bug.title}")
            if bug.test_intent:
                print(f"      Test Intent    : {bug.test_intent}")
            if bug.user_scenario:
                print(f"      User Scenario  : {bug.user_scenario}")
            if bug.business_impact:
                print(f"      Commercial     : {bug.business_impact}")
            if bug.page_url:
                print(f"      Page Route     : {bug.page_url}")
            print(f"      Target Selector: {bug.selector}")
            print(f"      Action / Vector: {bug.action_type} -> '{bug.payload or ''}'")
            print(f"      Error Details  : {bug.error_message}")
            print("      Reproduction Steps:")
            for s_idx, step in enumerate(bug.reproduction_steps, 1):
                clean_step = CLEAN_STEP_RE.sub("", step)
                print(f"        {s_idx}. {clean_step}")
            print()

    # BUCKET 2: UX & ACCESSIBILITY IMPROVEMENTS
    print("BUCKET 2: ACCESSIBILITY & USABILITY FINDINGS")
    print("-" * 70)
    if not ux_improvements:
        print("  Zero accessibility or usability barriers detected.")
    else:
        for i, ux in enumerate(ux_improvements, start=1):
            route_info = f" [{ux.page_url}]" if ux.page_url else ""
            print(f"  [{i}] [{ux.category}]{route_info} Target: {ux.selector}")
            print(f"      Issue Description: {ux.issue}")
            if ux.impact_rationale:
                print(f"      Impact Rationale : {ux.impact_rationale}")
            print(f"      Suggested Fix    : {ux.suggested_fix}")
            print()
    print("="*70 + "\n")


def generate_html_report(hard_bugs: List[HardBug], ux_improvements: List[UXImprovement], elapsed_time: float, target_url: str, output_path: str = "report.html"):
    """Generates a modern, developer-actionable dual-bucket HTML report."""
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    hard_bugs_html = ""
    if not hard_bugs:
        hard_bugs_html = "<div class='empty-state'>Zero runtime defects detected. All boundary actions executed safely without unhandled exceptions.</div>"
    else:
        for b in hard_bugs:
            steps_html = "".join([f"<li>{CLEAN_STEP_RE.sub('', step)}</li>" for step in b.reproduction_steps])
            intent_html = f"<div class='meta-row'><span class='tag-label'>Test Intent</span><p>{b.test_intent}</p></div>" if b.test_intent else ""
            scenario_html = f"<div class='meta-row'><span class='tag-label'>User Scenario</span><p>{b.user_scenario}</p></div>" if b.user_scenario else ""
            impact_html = f"<div class='meta-row impact'><span class='tag-label danger'>Commercial & Business Impact</span><p>{b.business_impact}</p></div>" if b.business_impact else ""
            route_tag = f"<span class='route-badge'>{b.page_url}</span>" if b.page_url else ""
            
            hard_bugs_html += f"""
            <div class="card bug-card">
                <div class="card-header">
                    <span class="badge badge-danger">{b.severity}</span>
                    {route_tag}
                    <h3 class="card-title">{b.title}</h3>
                </div>
                <div class="card-body">
                    <div class="plain-box">
                        {intent_html}
                        {scenario_html}
                        {impact_html}
                    </div>
                    <p class="field-meta"><strong>Target:</strong> <code>{b.selector}</code> &nbsp;|&nbsp; <strong>Action:</strong> <code>{b.action_type}</code> (Payload: <code>"{b.payload or ''}"</code>)</p>
                    <pre class="error-trace">{b.error_message}</pre>
                    <div class="repro-box">
                        <h4>Reproduction Instructions</h4>
                        <ol class="repro-list">{steps_html}</ol>
                    </div>
                </div>
            </div>
            """

    ux_html = ""
    if not ux_improvements:
        ux_html = "<div class='empty-state'>Zero accessibility or usability barriers detected across interactive controls.</div>"
    else:
        for ux in ux_improvements:
            impact_html = f"<div class='impact-box'><strong>Impact Rationale:</strong> {ux.impact_rationale}</div>" if ux.impact_rationale else ""
            route_tag = f"<span class='route-badge'>{ux.page_url}</span>" if ux.page_url else ""
            ux_html += f"""
            <div class="card ux-card">
                <div class="card-header">
                    <span class="badge badge-warning">{ux.category}</span>
                    {route_tag}
                    <h3 class="card-title">Target: <code>{ux.selector}</code></h3>
                </div>
                <div class="card-body">
                    <p class="field-meta"><strong>Issue:</strong> {ux.issue}</p>
                    {impact_html}
                    <div class="fix-box">
                        <strong>Suggested Remediation:</strong> {ux.suggested_fix}
                    </div>
                </div>
            </div>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AppTester — Quality Engineering Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #09090b;
            --surface: #121215;
            --surface-elevated: #18181b;
            --border: rgba(255, 255, 255, 0.08);
            --text-primary: #f4f4f5;
            --text-secondary: #a1a1aa;
            --text-muted: #71717a;
            --danger: #ef4444;
            --warning: #f59e0b;
            --code-bg: #141417;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text-primary);
            padding: 3rem 1.5rem;
            -webkit-font-smoothing: antialiased;
            letter-spacing: -0.01em;
        }}
        .header {{
            max-width: 960px;
            margin: 0 auto 2.5rem;
            background: var(--surface);
            padding: 1.75rem 2rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .header h1 {{
            font-size: 1.35rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 0.75rem;
        }}
        .metrics {{
            display: flex;
            gap: 2rem;
            font-size: 0.825rem;
            color: var(--text-muted);
            flex-wrap: wrap;
        }}
        .metrics strong {{ color: var(--text-primary); }}
        .container {{ max-width: 960px; margin: 0 auto; display: grid; gap: 2.5rem; }}
        .section-title {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.25rem;
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .card-title {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }}
        .route-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.2rem 0.5rem;
            color: var(--text-muted);
        }}
        .badge {{
            font-size: 0.675rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            padding: 0.2rem 0.55rem;
            border-radius: 4px;
        }}
        .badge-danger {{
            background: rgba(239, 68, 68, 0.08);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        .badge-warning {{
            background: rgba(245, 158, 11, 0.08);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }}
        .plain-box {{
            background: var(--surface-elevated);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}
        .meta-row {{ display: flex; flex-direction: column; gap: 0.2rem; }}
        .meta-row.impact {{
            padding-top: 0.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .tag-label {{
            font-size: 0.675rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
            color: var(--text-muted);
        }}
        .tag-label.danger {{ color: #f87171; }}
        .meta-row p {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }}
        .field-meta {{
            font-size: 0.825rem;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
        }}
        code {{
            background: rgba(255, 255, 255, 0.04);
            padding: 0.15rem 0.35rem;
            border-radius: 3px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-primary);
        }}
        .error-trace {{
            background: rgba(239, 68, 68, 0.04);
            border: 1px solid rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.775rem;
            overflow-x: auto;
            white-space: pre-wrap;
            margin-bottom: 1rem;
        }}
        .repro-box h4 {{
            font-size: 0.725rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
        }}
        .repro-list {{
            margin-left: 1.25rem;
            color: var(--text-secondary);
            font-size: 0.825rem;
            line-height: 1.6;
        }}
        .impact-box {{
            background: var(--surface-elevated);
            border-left: 3px solid var(--warning);
            padding: 0.75rem 1rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin: 0.75rem 0;
            line-height: 1.5;
        }}
        .fix-box {{
            background: var(--surface-elevated);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.75rem 1rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }}
        .fix-box strong {{
            color: var(--text-primary);
            display: block;
            margin-bottom: 0.25rem;
            font-size: 0.725rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .empty-state {{
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 2.5rem;
            text-align: center;
            border-radius: 8px;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AppTester — Audit Summary</h1>
        <div class="metrics">
            <span>Target: <strong>{target_url}</strong></span>
            <span>Duration: <strong>{elapsed_time:.2f}s</strong></span>
            <span>Hard Defects: <strong style="color:var(--danger);">{len(hard_bugs)}</strong></span>
            <span>UX Findings: <strong style="color:var(--warning);">{len(ux_improvements)}</strong></span>
            <span>Timestamp: <strong>{timestamp}</strong></span>
        </div>
    </div>

    <div class="container">
        <section>
            <h2 class="section-title">Hard Defects (Runtime & Network Exceptions)</h2>
            {hard_bugs_html}
        </section>

        <section>
            <h2 class="section-title">Accessibility & Usability Findings</h2>
            {ux_html}
        </section>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Report saved to: {os.path.abspath(output_path)}")
