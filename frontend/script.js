const API = '';
let currentCampaignId = null;

function $(id) { return document.getElementById(id); }

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const map = { create: 'createView', dashboard: 'dashboardView', docs: 'docsView' };
    $(map[name]).classList.add('active');
    document.querySelector(`.nav-btn[data-view="${name}"]`).classList.add('active');
}

document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => showView(btn.dataset.view));
});

function setStatus(stepId, status) {
    const el = $(stepId);
    if (!el) return;
    el.classList.remove('done', 'active');
    if (status) el.classList.add(status);
}

function renderProgress(state) {
    const steps = [
        { id: 'stepResearch', label: 'Research', states: ['RESEARCHING', 'RESEARCH_COMPLETE', 'EDITOR_REVIEW', 'REVISION_REQUIRED', 'APPROVED', 'READY_TO_PUBLISH', 'PUBLISHED'] },
        { id: 'stepPositioning', label: 'Positioning', states: ['RESEARCH_COMPLETE', 'EDITOR_REVIEW', 'REVISION_REQUIRED', 'APPROVED', 'READY_TO_PUBLISH', 'PUBLISHED'] },
        { id: 'stepCopy', label: 'Copywriting', states: ['COPYWRITING', 'EDITOR_REVIEW', 'REVISION_REQUIRED', 'APPROVED', 'READY_TO_PUBLISH', 'PUBLISHED'] },
        { id: 'stepEditor', label: 'Editorial QA', states: ['EDITOR_REVIEW', 'REVISION_REQUIRED', 'APPROVED', 'READY_TO_PUBLISH', 'PUBLISHED'] },
        { id: 'stepApproval', label: 'Human Approval', states: ['APPROVED', 'READY_TO_PUBLISH', 'PUBLISHED'] },
        { id: 'stepPublish', label: 'Publishing', states: ['READY_TO_PUBLISH', 'PUBLISHED'] },
    ];
    const html = steps.map(s => {
        let cls = '';
        if (s.states.includes(state)) cls = 'done';
        else if (steps.find(x => x.id === s.id) && steps.indexOf(steps.find(x => x.id === s.id)) < steps.findIndex(x => x.states.includes(state))) cls = 'done';
        else if (state === 'REVISION_REQUIRED' && s.id === 'stepEditor') cls = 'active';
        else if (state === 'RESEARCHING' && s.id === 'stepResearch') cls = 'active';
        else if (state === 'COPYWRITING' && ['stepCopy', 'stepEditor'].includes(s.id)) cls = 'active';
        const icon = cls === 'done' ? '✓' : (cls === 'active' ? '…' : '○');
        return `<div class="step ${cls}"><div class="icon">${icon}</div><div><div>${s.label}</div><div class="badge ${state === 'REVISION_REQUIRED' && s.id === 'stepEditor' ? 'reject' : (cls === 'done' ? 'pass' : '')}">${state}</div></div></div>`;
    }).join('');
    $('agentProgress').innerHTML = html;
}

function renderCampaign(campaign) {
    currentCampaignId = campaign.id;
    const overview = $('campaignOverview');
    overview.innerHTML = `
        <div class="item"><div class="label">Name</div><div class="value">${escapeHtml(campaign.name)}</div></div>
        <div class="item"><div class="label">Objective</div><div class="value">${escapeHtml(campaign.brief.campaign_objective)}</div></div>
        <div class="item"><div class="label">Audience</div><div class="value">${escapeHtml(campaign.brief.target_audience)}</div></div>
        <div class="item"><div class="label">Channels</div><div class="value">${campaign.brief.preferred_channels.map(escapeHtml).join(', ')}</div></div>
        <div class="item"><div class="label">Status</div><div class="value"><span class="status-dot" style="background:${statusColor(campaign.state)}"></span>${campaign.state}</div></div>
        <div class="item"><div class="label">Revisions</div><div class="value">${campaign.revision_count} / ${campaign.max_revisions}</div></div>
    `;
    renderProgress(campaign.state);
    renderResearch(campaign.research_report);
    renderContent(campaign);
    renderQA(campaign);
    renderFinal(campaign);
}

function statusColor(state) {
    const colors = { PUBLISHED: '#22c55e', READY_TO_PUBLISH: '#22c55e', APPROVED: '#22c55e', FAILED: '#ef4444', REVISION_REQUIRED: '#f59e0b' };
    return colors[state] || '#3b82f6';
}

function renderResearch(research) {
    const panel = $('researchPanel');
    if (!research) { panel.innerHTML = '<div class="placeholder">No research yet.</div>'; return; }
    const fmt = (label, val) => val ? `<details><summary>${label}</summary><pre>${escapeHtml(JSON.stringify(val, null, 2))}</pre></details>` : '';
    panel.innerHTML = `
        <details open><summary>Market Position</summary><p>${escapeHtml(research.market_position)}</p></details>
        ${fmt('Audience Insights', research.target_audience_insights)}
        ${fmt('Pain Points', research.pain_points)}
        ${fmt('Competitor Messaging', research.competitor_messaging)}
        ${fmt('Market Trends', research.market_trends)}
        ${fmt('Keywords', research.keyword_opportunities)}
        ${fmt('Differentiation', research.differentiation_opportunities)}
        ${fmt('Risks', research.risks)}
        <div class="chip">Confidence: ${research.confidence}</div>
        <div class="chip">Mode: ${research.research_mode}</div>
        <details><summary>Sources (${research.sources.length})</summary><ul>${research.sources.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul></details>
    `;
}

function renderContent(campaign) {
    const panel = $('contentPanel');
    if (!campaign.copy_variants.length) { panel.innerHTML = '<div class="placeholder">No variants yet.</div>'; return; }
    panel.innerHTML = campaign.copy_variants.map(v => `
        <div class="variant">
            <div class="meta"><span class="tag">${v.platform}</span><span class="tag">${v.framework}</span><span class="tag">${v.character_count} chars</span></div>
            <div><strong>${escapeHtml(v.headline)}</strong></div>
            <div style="margin-top:0.4rem">${escapeHtml(v.primary_text)}</div>
            ${v.subheadline ? `<div style="margin-top:0.4rem;color:var(--text-secondary)">${escapeHtml(v.subheadline)}</div>` : ''}
            <div style="margin-top:0.5rem"><strong>CTA:</strong> ${escapeHtml(v.cta)}</div>
            ${v.benefits.length ? `<div style="margin-top:0.5rem">${v.benefits.map(b => `<span class="chip">${escapeHtml(b)}</span>`).join('')}</div>` : ''}
        </div>
    `).join('');
}

function renderQA(campaign) {
    const panel = $('qaPanel');
    if (!campaign.editorial_review) { panel.innerHTML = '<div class="placeholder">No editorial review yet.</div>'; return; }
    const r = campaign.editorial_review;
    const issuesHtml = r.issues.map(i => `<div class="issue ${i.severity}"><strong>[${i.check_type}] ${i.severity}</strong>: ${escapeHtml(i.issue)}<br><em>${escapeHtml(i.field)}</em>${i.required_action ? `<br><strong>Action:</strong> ${escapeHtml(i.required_action)}` : ''}</div>`).join('');
    panel.innerHTML = `
        <div><span class="badge ${r.status === 'PASS' ? 'pass' : 'reject'}">${r.status}</span> <span style="margin-left:0.5rem">Score: ${r.overall_score}</span></div>
        <div style="margin-top:0.5rem;font-size:0.85rem;color:var(--text-secondary)">Revisions: ${r.revision_instructions.length}</div>
        ${issuesHtml ? `<details open><summary>Issues (${r.issues.length})</summary>${issuesHtml}</details>` : '<div class="placeholder">No issues.</div>'}
        ${r.revision_instructions.length ? `<details><summary>Revision Instructions</summary><ul>${r.revision_instructions.map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ul></details>` : ''}
    `;
}

function renderFinal(campaign) {
    const approval = $('approvalActions');
    const exportActions = $('exportActions');
    if (campaign.state === 'APPROVED' || campaign.state === 'READY_TO_PUBLISH' || campaign.state === 'PUBLISHED') {
        approval.style.display = 'none';
        exportActions.style.display = 'flex';
        const base = `${API}/export/${campaign.id}`;
        $('exportJson').href = `${base}/json`;
        $('exportMd').href = `${base}/markdown`;
        $('exportCsv').href = `${base}/csv`;
    } else if (campaign.editorial_review && campaign.editorial_review.status === 'PASS') {
        approval.style.display = 'flex';
        exportActions.style.display = 'none';
    } else if (campaign.state === 'REVISION_REQUIRED') {
        approval.style.display = 'none';
        exportActions.style.display = 'none';
    } else {
        approval.style.display = 'none';
        exportActions.style.display = 'none';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function statusColor(state) {
    const map = { PUBLISHED: '#22c55e', READY_TO_PUBLISH: '#22c55e', APPROVED: '#22c55e', FAILED: '#ef4444', REVISION_REQUIRED: '#f59e0b', RESEARCHING: '#3b82f6', COPYWRITING: '#3b82f6', EDITOR_REVIEW: '#f59e0b' };
    return map[state] || '#64748b';
}

async function pollCampaign(id) {
    const res = await fetch(`${API}/campaigns/${id}`);
    if (!res.ok) return;
    const campaign = await res.json();
    renderCampaign(campaign);
    if (!['PUBLISHED', 'READY_TO_PUBLISH', 'APPROVED', 'FAILED', 'REVISION_REQUIRED'].includes(campaign.state)) {
        setTimeout(() => pollCampaign(id), 1500);
    }
}

$('briefForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        product_service: $('product_service').value,
        product_description: $('product_description').value,
        target_audience: $('target_audience').value,
        campaign_objective: $('campaign_objective').value,
        target_market: $('target_market').value,
        preferred_channels: $('preferred_channels').value.split(',').map(s => s.trim()).filter(Boolean),
        tone: $('tone').value,
        key_selling_points: ($('key_selling_points').value || '').split(',').map(s => s.trim()).filter(Boolean),
        cta: $('cta').value,
        campaign_duration: $('campaign_duration').value,
        competitor_names: ($('competitor_names').value || '').split(',').map(s => s.trim()).filter(Boolean),
        brand_guidelines: $('brand_guidelines').value || undefined,
    };
    const btn = $('runCampaignBtn');
    btn.disabled = true;
    btn.textContent = 'Running...';
    try {
        const res = await fetch(`${API}/campaigns/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (!res.ok) throw new Error('Failed');
        const campaign = await res.json();
        showView('dashboard');
        pollCampaign(campaign.id);
    } catch (err) {
        alert('Failed to create campaign: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Campaign';
    }
});

async function loadCampaigns() {
    const res = await fetch(`${API}/campaigns/`);
    if (!res.ok) return;
    const campaigns = await res.json();
    if (campaigns.length) {
        pollCampaign(campaigns[0].id);
    }
}

$('approveBtn').addEventListener('click', async () => {
    if (!currentCampaignId) return;
    await fetch(`${API}/campaigns/${currentCampaignId}/approve`, { method: 'POST' });
    pollCampaign(currentCampaignId);
});

$('reviseBtn').addEventListener('click', async () => {
    if (!currentCampaignId) return;
    await fetch(`${API}/campaigns/${currentCampaignId}/revise`, { method: 'POST' });
    pollCampaign(currentCampaignId);
});

$('rejectBtn').addEventListener('click', async () => {
    if (!currentCampaignId) return;
    const reason = prompt('Rejection reason:');
    if (reason === null) return;
    await fetch(`${API}/campaigns/${currentCampaignId}/reject?reason=${encodeURIComponent(reason)}`, { method: 'POST' });
    pollCampaign(currentCampaignId);
});

$('uploadBtn').addEventListener('click', async () => {
    const input = $('docUpload');
    if (!input.files.length) return alert('Select files first.');
    const form = new FormData();
    for (const f of input.files) form.append('files', f);
    form.append('document_type', 'brand');
    const res = await fetch(`${API}/documents/upload`, { method: 'POST', body: form });
    if (res.ok) { input.value = ''; loadDocs(); }
});

$('ingestBtn').addEventListener('click', async () => {
    const res = await fetch(`${API}/documents/ingest-folder`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'path=docs/brand' });
    if (res.ok) loadDocs();
});

async function loadDocs() {
    const res = await fetch(`${API}/documents/`);
    if (!res.ok) return;
    const docs = await res.json();
    $('docList').innerHTML = docs.map(d => `<div class="doc-item"><div><strong>${escapeHtml(d.filename)}</strong><div class="chip">${d.chunk_count} chunks</div></div></div>`).join('');
}

(async () => { await loadDocs(); await loadCampaigns(); })();
