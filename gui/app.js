document.addEventListener('DOMContentLoaded', () => {
    const auditForm = document.getElementById('audit-form');
    const urlInput = document.getElementById('target-url-input');
    const startBtn = document.getElementById('start-audit-btn');
    const presetChips = document.querySelectorAll('.preset-chip');

    const progressSection = document.getElementById('progress-section');
    const progressTitle = document.getElementById('progress-title');
    const progressSub = document.getElementById('progress-sub');
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');

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
        startBtn.querySelector('.btn-text').textContent = 'Auditing...';
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');

        // Reset Stepper
        resetStepper();

        // Step 1: DOM Inspection Animation
        setStep(1, "Inspecting DOM & Extracting Nodes...", "Capturing interactive inputs, links, forms, and attributes (<500 tokens)");

        // Step 2 & 3 timer simulations for smooth UX while backend processes
        const step2Timer = setTimeout(() => {
            setStep(2, "Reasoning with LLM Layer...", "Generating targeted boundary test cases and identifying semantic UX flaws");
        }, 1200);

        const step3Timer = setTimeout(() => {
            setStep(3, "Executing Playwright Fuzz Tests...", "Applying Strict Verification Gate on runtime exceptions and network errors");
        }, 2500);

        try {
            const response = await fetch('/api/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            clearTimeout(step2Timer);
            clearTimeout(step3Timer);

            const result = await response.json();

            if (!result.success) {
                alert("Audit Error: " + (result.error || "Failed to audit URL"));
                return;
            }

            // Mark all steps complete
            completeAllSteps();

            // Populate Results
            renderResults(result);

            // Reveal Results Section
            resultsSection.classList.remove('hidden');

            // Scroll down to results smoothly
            setTimeout(() => {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 200);

        } catch (err) {
            clearTimeout(step2Timer);
            clearTimeout(step3Timer);
            alert("Network Error: Could not connect to audit backend. Ensure server.py is running.\n" + err.message);
        } finally {
            startBtn.disabled = false;
            startBtn.querySelector('.btn-text').textContent = 'Run AI Audit';
            setTimeout(() => {
                progressSection.classList.add('hidden');
            }, 800);
        }
    });

    function resetStepper() {
        [step1, step2, step3].forEach(s => {
            s.classList.remove('active', 'completed');
        });
    }

    function setStep(num, title, sub) {
        progressTitle.textContent = title;
        progressSub.textContent = sub;
        [step1, step2, step3].forEach((s, idx) => {
            if (idx + 1 < num) {
                s.classList.remove('active');
                s.classList.add('completed');
            } else if (idx + 1 === num) {
                s.classList.add('active');
                s.classList.remove('completed');
            } else {
                s.classList.remove('active', 'completed');
            }
        });
    }

    function completeAllSteps() {
        [step1, step2, step3].forEach(s => {
            s.classList.remove('active');
            s.classList.add('completed');
        });
    }

    function renderResults(data) {
        metricTime.textContent = `${data.elapsed_time}s`;
        metricBugs.textContent = data.hard_bugs.length;
        metricUx.textContent = data.ux_improvements.length;
        metricElements.textContent = data.element_count;

        countBugs.textContent = data.hard_bugs.length;
        countUx.textContent = data.ux_improvements.length;

        // Render Hard Bugs
        if (data.hard_bugs.length === 0) {
            hardBugsList.innerHTML = `<div class="empty-state">✨ Zero Hard Bugs Detected! All runtime exceptions & network checks passed.</div>`;
        } else {
            hardBugsList.innerHTML = data.hard_bugs.map((bug, index) => {
                const reproHtml = bug.reproduction_steps.map(step => `<li>${step}</li>`).join('');
                return `
                    <div class="report-card bug">
                        <div class="card-top">
                            <h3>${bug.title}</h3>
                            <span class="badge badge-danger">${bug.severity}</span>
                        </div>
                        
                        <!-- Plain English Executive / Non-Technical Summary -->
                        <div class="plain-english-box">
                            ${bug.test_intent ? `
                            <div class="meta-row">
                                <span class="tag-label">🎯 Test Intent</span>
                                <p>${escapeHtml(bug.test_intent)}</p>
                            </div>` : ''}
                            ${bug.user_scenario ? `
                            <div class="meta-row">
                                <span class="tag-label">👤 User Scenario</span>
                                <p>${escapeHtml(bug.user_scenario)}</p>
                            </div>` : ''}
                            ${bug.business_impact ? `
                            <div class="meta-row impact">
                                <span class="tag-label danger">📉 App & Business Impact</span>
                                <p>${escapeHtml(bug.business_impact)}</p>
                            </div>` : ''}
                        </div>

                        <!-- Technical Developer Section -->
                        <div class="field-row" style="margin-top: 0.8rem;">
                            <strong>Target Selector:</strong> <code>${escapeHtml(bug.selector)}</code> &nbsp;|&nbsp; <strong>Action:</strong> <code>${bug.action_type}</code> 
                            ${bug.payload ? `(Payload: <code>${escapeHtml(bug.payload)}</code>)` : ''}
                        </div>
                        <div class="error-box">${escapeHtml(bug.error_message)}</div>
                        <div class="repro-steps">
                            <h4>Developer Steps to Reproduce</h4>
                            <ol>${reproHtml}</ol>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Render UX Improvements
        if (data.ux_improvements.length === 0) {
            uxImprovementsList.innerHTML = `<div class="empty-state">✨ Zero UX or accessibility issues detected in interactive elements.</div>`;
        } else {
            uxImprovementsList.innerHTML = data.ux_improvements.map(ux => {
                return `
                    <div class="report-card ux">
                        <div class="card-top">
                            <h3>Target: <code>${escapeHtml(ux.selector)}</code></h3>
                            <span class="badge badge-warning">${ux.category}</span>
                        </div>
                        <div class="field-row">
                            <strong>Issue:</strong> ${escapeHtml(ux.issue)}
                        </div>
                        ${ux.impact_rationale ? `
                        <div class="impact-box">
                            <strong>⚠️ User Impact & Rationale:</strong> ${escapeHtml(ux.impact_rationale)}
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
