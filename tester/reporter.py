import os
import time
from typing import List
from tester.schema import HardBug, UXImprovement

def render_terminal_report(hard_bugs: List[HardBug], ux_improvements: List[UXImprovement], elapsed_time: float, target_url: str):
    """Prints a clean, partitioned dual-bucket summary directly to the terminal."""
    print("\n" + "="*70)
    print(" 🤖 AI APP TESTER PROTOTYPE - EXECUTIVE SUMMARY REPORT")
    print(f" Target URL: {target_url}")
    print(f" Execution Time: {elapsed_time:.2f}s | Hard Bugs: {len(hard_bugs)} | UX Flaws: {len(ux_improvements)}")
    print("="*70 + "\n")

    # BUCKET 1: HARD BUGS
    print("🔴 BUCKET 1: HARD BUGS (VERIFIED RUNTIME & NETWORK FAILURES)")
    print("-" * 70)
    if not hard_bugs:
        print("  ✨ Zero hard bugs detected.")
    else:
        for i, bug in enumerate(hard_bugs, start=1):
            print(f"  [{i}] [{bug.severity.upper()}] {bug.title}")
            if bug.test_intent:
                print(f"      🎯 Test Intent    : {bug.test_intent}")
            if bug.user_scenario:
                print(f"      👤 User Scenario  : {bug.user_scenario}")
            if bug.business_impact:
                print(f"      📉 Business Impact: {bug.business_impact}")
            if bug.page_url:
                print(f"      📍 Page Route     : {bug.page_url}")
            print(f"      Target Selector : {bug.selector}")
            print(f"      Action / Payload: {bug.action_type} -> '{bug.payload or ''}'")
            print(f"      Error Details   : {bug.error_message}")
            print("      Reproduction Steps:")
            for step in bug.reproduction_steps:
                print(f"        {step}")
            print()

    # BUCKET 2: UX & ACCESSIBILITY IMPROVEMENTS
    print("🟡 BUCKET 2: UX & ACCESSIBILITY IMPROVEMENTS")
    print("-" * 70)
    if not ux_improvements:
        print("  ✨ Zero UX or accessibility issues detected.")
    else:
        for i, ux in enumerate(ux_improvements, start=1):
            route_info = f" [{ux.page_url}]" if ux.page_url else ""
            print(f"  [{i}] [{ux.category}]{route_info} Target: {ux.selector}")
            print(f"      Issue Description: {ux.issue}")
            if ux.impact_rationale:
                print(f"      User Impact / Why: {ux.impact_rationale}")
            print(f"      Suggested Fix    : {ux.suggested_fix}")
            print()
    print("="*70 + "\n")


def generate_html_report(hard_bugs: List[HardBug], ux_improvements: List[UXImprovement], elapsed_time: float, target_url: str, output_path: str = "report.html"):
    """Generates a modern, developer-actionable dual-bucket HTML report."""
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    hard_bugs_html = ""
    if not hard_bugs:
        hard_bugs_html = "<div class='empty-state'>✨ Zero Hard Bugs Detected</div>"
    else:
        for b in hard_bugs:
            steps_html = "".join([f"<li>{step}</li>" for step in b.reproduction_steps])
            intent_html = f"<div style='margin-bottom: 0.5rem;'><span style='background: rgba(56,189,248,0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>🎯 TEST INTENT</span> <span style='font-size: 0.9rem; color: #e2e8f0;'>{b.test_intent}</span></div>" if b.test_intent else ""
            scenario_html = f"<div style='margin-bottom: 0.5rem;'><span style='background: rgba(148,163,184,0.15); color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>👤 USER SCENARIO</span> <span style='font-size: 0.9rem; color: #cbd5e1;'>{b.user_scenario}</span></div>" if b.user_scenario else ""
            impact_html = f"<div style='margin-bottom: 0.5rem;'><span style='background: rgba(239,68,68,0.15); color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>📉 BUSINESS IMPACT</span> <span style='font-size: 0.9rem; color: #fca5a5;'>{b.business_impact}</span></div>" if b.business_impact else ""
            route_tag = f"<span class='badge' style='background: rgba(255,255,255,0.08); color: #94a3b8; font-size: 0.75rem; margin-left: 0.5rem;'>📍 {b.page_url}</span>" if b.page_url else ""
            
            hard_bugs_html += f"""
            <div class="card bug-card">
                <div class="card-header">
                    <span class="badge badge-danger">{b.severity}</span>
                    {route_tag}
                    <h3 class="card-title">{b.title}</h3>
                </div>
                <div class="card-body">
                    <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; border: 1px solid rgba(255,255,255,0.06);">
                        {intent_html}
                        {scenario_html}
                        {impact_html}
                    </div>
                    <p><strong>Target Selector:</strong> <code>{b.selector}</code> &nbsp;|&nbsp; <strong>Action:</strong> <code>{b.action_type}</code> (Payload: <code>"{b.payload or ''}"</code>)</p>
                    <p><strong>Error Trace:</strong></p>
                    <pre class="error-trace">{b.error_message}</pre>
                    <p><strong>Developer Steps to Reproduce:</strong></p>
                    <ol class="repro-list">{steps_html}</ol>
                </div>
            </div>
            """

    ux_html = ""
    if not ux_improvements:
        ux_html = "<div class='empty-state'>✨ Zero UX / Accessibility Issues Detected</div>"
    else:
        for ux in ux_improvements:
            impact_html = f"<p style='color: #fde68a; margin: 0.5rem 0;'><strong>⚠️ User Impact & Rationale:</strong> {ux.impact_rationale}</p>" if ux.impact_rationale else ""
            route_tag = f"<span class='badge' style='background: rgba(255,255,255,0.08); color: #94a3b8; font-size: 0.75rem; margin-left: 0.5rem;'>📍 {ux.page_url}</span>" if ux.page_url else ""
            ux_html += f"""
            <div class="card ux-card">
                <div class="card-header">
                    <span class="badge badge-warning">{ux.category}</span>
                    {route_tag}
                    <h3 class="card-title">Target: <code>{ux.selector}</code></h3>
                </div>
                <div class="card-body">
                    <p><strong>Issue:</strong> {ux.issue}</p>
                    {impact_html}
                    <div class="fix-box">
                        <strong>Suggested Fix:</strong> {ux.suggested_fix}
                    </div>
                </div>
            </div>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI App Tester - Developer Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --subtext: #94a3b8;
            --danger: #ef4444;
            --warning: #f59e0b;
            --accent: #38bdf8;
            --code-bg: #0f172a;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem;
        }}
        .header {{
            max-width: 1000px;
            margin: 0 auto 2rem auto;
            background: var(--card-bg);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .header h1 {{ margin: 0 0 0.5rem 0; color: var(--accent); font-size: 1.8rem; }}
        .metrics {{ display: flex; gap: 2rem; margin-top: 1rem; font-size: 0.95rem; color: var(--subtext); }}
        .metrics span strong {{ color: var(--text); }}
        .container {{ max-width: 1000px; margin: 0 auto; display: grid; gap: 2rem; }}
        .section-title {{ font-size: 1.4rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }}
        .card {{ background: var(--card-bg); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; border-left: 4px solid #334155; }}
        .bug-card {{ border-left-color: var(--danger); }}
        .ux-card {{ border-left-color: var(--warning); }}
        .card-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }}
        .card-title {{ margin: 0; font-size: 1.1rem; color: var(--text); }}
        .badge {{ padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }}
        code {{ background: var(--code-bg); padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; color: var(--accent); }}
        .error-trace {{ background: var(--code-bg); color: #fca5a5; padding: 0.75rem; border-radius: 6px; font-size: 0.85rem; overflow-x: auto; white-space: pre-wrap; }}
        .fix-box {{ background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 0.75rem; border-radius: 6px; margin-top: 0.5rem; font-size: 0.9rem; }}
        .repro-list {{ margin: 0.5rem 0 0 1.25rem; padding: 0; color: var(--subtext); font-size: 0.9rem; }}
        .empty-state {{ background: var(--card-bg); padding: 1.5rem; text-align: center; border-radius: 8px; color: var(--subtext); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI App Tester - Audit Report</h1>
        <div class="metrics">
            <span>Target URL: <strong>{target_url}</strong></span>
            <span>Execution Time: <strong>{elapsed_time:.2f}s</strong></span>
            <span>Hard Bugs: <strong style="color:var(--danger);">{len(hard_bugs)}</strong></span>
            <span>UX Flaws: <strong style="color:var(--warning);">{len(ux_improvements)}</strong></span>
            <span>Generated: <strong>{timestamp}</strong></span>
        </div>
    </div>

    <div class="container">
        <section>
            <h2 class="section-title">🔴 Hard Bugs (Verified Exceptions & Network Errors)</h2>
            {hard_bugs_html}
        </section>

        <section>
            <h2 class="section-title">🟡 UX & Accessibility Improvements</h2>
            {ux_html}
        </section>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"📄 Detailed HTML Report saved to: {os.path.abspath(output_path)}")
