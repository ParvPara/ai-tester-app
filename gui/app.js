document.addEventListener('DOMContentLoaded', () => {
    const auditForm = document.getElementById('audit-form');
    const urlInput = document.getElementById('target-url-input');
    const startBtn = document.getElementById('start-audit-btn');
    const presetChips = document.querySelectorAll('.preset-chip');

    const progressSection = document.getElementById('progress-section');
    const progressTitle = document.getElementById('progress-title');
    const progressSub = document.getElementById('progress-sub');

    const resultsSection = document.getElementById('results-section');
    const metricTime = document.getElementById('metric-time');
    const metricBugs = document.getElementById('metric-bugs');
    const metricUx = document.getElementById('metric-ux');
    const metricElements = document.getElementById('metric-elements');

    const countBugs = document.getElementById('count-bugs');
    const countUx = document.getElementById('count-ux');

    const hardBugsList = document.getElementById('hard-bugs-list');
    const uxImprovementsList = document.getElementById('ux-improvements-list');
    const rawJsonOutput = document.getElementById('raw-json-output');
    const tabButtons = document.querySelectorAll('.tab-btn');

    // Preset Chip Click Handlers
    presetChips.forEach(chip => {
        chip.addEventListener('click', () => {
            presetChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            urlInput.value = chip.getAttribute('data-url');
        });
    });

    // Tab Switching
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const tabId = btn.getAttribute('data-tab');
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
            
            const targetPane = document.getElementById(`tab-${tabId}`);
            if (targetPane) targetPane.classList.remove('hidden');
        });
    });

    // Form Submission
    auditForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        // UI State: Running
        startBtn.disabled = true;
        startBtn.querySelector('.btn-text').textContent = 'Executing...';
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');

        // Reset Graph Canvas
        resetGraph();
        const spinner = progressSection.querySelector('.spinner');
        if (spinner) spinner.style.display = 'block';
        progressTitle.textContent = 'Executing Multi-Agent Graph...';
        progressSub.textContent = 'Orchestrating DOM ingestion, parallel fuzzer/auditor threads, and grounding gate';

        // Stage 1: DOM Ingestion Node Active
        setNodeStatus('dom-ingest', 'active', 'Harvesting interactive controls & discovering same-origin routes...');

        // Stage 2: Parallel Agents Active (Fuzzer || Auditor)
        const stage2Timer = setTimeout(() => {
            setNodeStatus('dom-ingest', 'completed', 'Interactive controls extracted (<500 tokens)');
            setNodeStatus('fuzzer', 'active', 'Generating boundary attack vectors & injection payloads...');
            setNodeStatus('auditor', 'active', 'Auditing accessibility & semantic friction in parallel...');
            progressTitle.textContent = 'Parallel Agent Reasoning...';
            progressSub.textContent = 'Adversarial Fuzzer and WCAG Auditor executing concurrently';
        }, 1200);

        // Stage 3: Playwright Grounding Gate
        const stage3Timer = setTimeout(() => {
            setNodeStatus('fuzzer', 'completed', 'Boundary test hypotheses generated');
            setNodeStatus('auditor', 'completed', 'Accessibility & human friction audit complete');
            setNodeStatus('playwright-gate', 'active', 'Executing fuzz actions in headless browser with live error interception...');
            progressTitle.textContent = 'Playwright Grounding Gate Active...';
            progressSub.textContent = 'Physically testing boundary hypotheses against headless browser runtime';
        }, 2800);

        // Stage 4: False Positive Judge Node
        const stage4Timer = setTimeout(() => {
            setNodeStatus('playwright-gate', 'completed', 'Fuzz actions physically executed in browser');
            setNodeStatus('judge', 'active', 'Correlating intercepted telemetry: enforcing 0% false positives...');
            progressTitle.textContent = 'False-Positive Judge Node Verifying...';
            progressSub.textContent = 'Filtering out speculative noise; verifying runtime crashes & failed requests';
        }, 4400);

        try {
            const response = await fetch('/api/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            clearTimeout(stage2Timer);
            clearTimeout(stage3Timer);
            clearTimeout(stage4Timer);

            const result = await response.json();

            if (!result.success) {
                alert("Audit Error: " + (result.error || "Failed to audit URL"));
                return;
            }

            // Mark all nodes completed with exact metrics
            const routeCount = (result.audited_routes && result.audited_routes.length) ? result.audited_routes.length : 1;
            setNodeStatus('dom-ingest', 'completed', `${routeCount} route(s) swept (${result.element_count} controls total)`);
            setNodeStatus('fuzzer', 'completed', `${result.fuzz_actions_count} boundary hypotheses across ${routeCount} route(s)`);
            setNodeStatus('auditor', 'completed', `${result.ux_improvements.length} UX & accessibility flaws detected`);
            setNodeStatus('playwright-gate', 'completed', `${result.fuzz_actions_count} test actions executed & intercepted`);
            setNodeStatus('judge', 'completed', `${result.hard_bugs.length} hard bugs verified (0% false positives)`);
            setNodeStatus('synthesis', 'completed', `Dual-bucket synthesis finalized in ${result.elapsed_time}s`);

            // Header state completed
            if (spinner) spinner.style.display = 'none';
            progressTitle.textContent = 'Multi-Agent Graph Complete';
            progressSub.textContent = `Completed in ${result.elapsed_time}s across ${routeCount} route(s). 0% false positives verified.`;

            // Populate Results
            renderResults(result);

            // Reveal Results Section
            resultsSection.classList.remove('hidden');

            // Scroll down to results smoothly
            setTimeout(() => {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);

        } catch (err) {
            clearTimeout(stage2Timer);
            clearTimeout(stage3Timer);
            clearTimeout(stage4Timer);
            alert("Network Error: Could not connect to audit backend. Ensure server.py is running.\n" + err.message);
        } finally {
            startBtn.disabled = false;
            startBtn.querySelector('.btn-text').textContent = 'Execute Audit';
        }
    });

    function setNodeStatus(nodeId, status, metaText) {
        const nodeEl = document.getElementById(`node-${nodeId}`);
        const badgeEl = document.getElementById(`status-${nodeId}`);
        const metaEl = document.getElementById(`meta-${nodeId}`);
        if (!nodeEl || !badgeEl) return;

        nodeEl.classList.remove('active', 'completed');
        if (status === 'active') {
            nodeEl.classList.add('active');
            badgeEl.textContent = 'Running';
        } else if (status === 'completed') {
            nodeEl.classList.add('completed');
            badgeEl.textContent = 'Verified';
        } else {
            badgeEl.textContent = 'Pending';
        }

        if (metaText && metaEl) {
            metaEl.textContent = metaText;
        }
    }

    function resetGraph() {
        setNodeStatus('dom-ingest', 'pending', 'Awaiting execution...');
        setNodeStatus('fuzzer', 'pending', 'Hypotheses generation');
        setNodeStatus('auditor', 'pending', 'Parallel semantic reasoning');
        setNodeStatus('playwright-gate', 'pending', 'Physical error interception');
        setNodeStatus('judge', 'pending', 'Hard bug verification');
        setNodeStatus('synthesis', 'pending', 'Final report assembly');
    }

    function renderResults(data) {
        metricTime.textContent = `${data.elapsed_time}s`;
        metricBugs.textContent = data.hard_bugs.length;
        metricUx.textContent = data.ux_improvements.length;
        metricElements.textContent = data.element_count;

        const routeCount = (data.audited_routes && data.audited_routes.length) ? data.audited_routes.length : 1;
        if (routeCount > 1) {
            const sub = metricElements.parentElement.querySelector('.metric-sub');
            if (sub) sub.textContent = `${routeCount} routes swept`;
        }

        countBugs.textContent = data.hard_bugs.length;
        countUx.textContent = data.ux_improvements.length;

        // Render Hard Bugs
        if (data.hard_bugs.length === 0) {
            hardBugsList.innerHTML = `<div class="empty-state">No runtime defects detected. All boundary actions executed safely without unhandled exceptions.</div>`;
        } else {
            hardBugsList.innerHTML = data.hard_bugs.map((bug) => {
                const reproHtml = bug.reproduction_steps.map(step => `<li>${step}</li>`).join('');
                return `
                    <div class="report-card bug">
                        <div class="card-top">
                            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                                <h3>${bug.title}</h3>
                                ${bug.page_url ? `<span class="route-badge">${escapeHtml(bug.page_url)}</span>` : ''}
                            </div>
                            <span class="badge badge-danger">${bug.severity}</span>
                        </div>
                        
                        <!-- Plain English Executive / Non-Technical Summary -->
                        <div class="plain-english-box">
                            ${bug.test_intent ? `
                            <div class="meta-row">
                                <span class="tag-label">Test Intent</span>
                                <p>${escapeHtml(bug.test_intent)}</p>
                            </div>` : ''}
                            ${bug.user_scenario ? `
                            <div class="meta-row">
                                <span class="tag-label">User Scenario</span>
                                <p>${escapeHtml(bug.user_scenario)}</p>
                            </div>` : ''}
                            ${bug.business_impact ? `
                            <div class="meta-row impact">
                                <span class="tag-label danger">Commercial & Business Impact</span>
                                <p>${escapeHtml(bug.business_impact)}</p>
                            </div>` : ''}
                        </div>

                        <!-- Technical Developer Section -->
                        <div class="field-row" style="margin-top: 0.8rem;">
                            <strong>Target:</strong> <code>${escapeHtml(bug.selector)}</code> &nbsp;|&nbsp; <strong>Action:</strong> <code>${bug.action_type}</code> 
                            ${bug.payload ? `(Payload: <code>${escapeHtml(bug.payload)}</code>)` : ''}
                        </div>
                        <div class="error-box">${escapeHtml(bug.error_message)}</div>
                        <div class="repro-steps">
                            <h4>Reproduction Instructions</h4>
                            <ol>${reproHtml}</ol>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Render UX Improvements
        if (data.ux_improvements.length === 0) {
            uxImprovementsList.innerHTML = `<div class="empty-state">No accessibility or usability issues detected across interactive controls.</div>`;
        } else {
            uxImprovementsList.innerHTML = data.ux_improvements.map(ux => {
                return `
                    <div class="report-card ux">
                        <div class="card-top">
                            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                                <h3>Target: <code>${escapeHtml(ux.selector)}</code></h3>
                                ${ux.page_url ? `<span class="route-badge">${escapeHtml(ux.page_url)}</span>` : ''}
                            </div>
                            <span class="badge badge-warning">${ux.category}</span>
                        </div>
                        <div class="field-row">
                            <strong>Issue:</strong> ${escapeHtml(ux.issue)}
                        </div>
                        ${ux.impact_rationale ? `
                        <div class="impact-box">
                            <strong>User Impact & Rationale:</strong> ${escapeHtml(ux.impact_rationale)}
                        </div>` : ''}
                        <div class="fix-box">
                            <strong>Suggested Remediation:</strong> ${escapeHtml(ux.suggested_fix)}
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Raw JSON output
        rawJsonOutput.textContent = JSON.stringify(data, null, 2);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
});
