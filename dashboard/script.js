/**
 * TTS Audio Cache — Enhanced Dashboard (AI-Powered)
 * ===================================================
 * Chart.js analytics, real-time Web Audio visualizer,
 * drifting Canvas particles, client-side Search/Filters,
 * inline play previews, and Smart Recommendations.
 */

const API = '';
let latencyChart = null;
let hitMissChart = null;
let cachedEntries = [];
let playingKey = null;

// ── Audio Context & Analyser for Waveform Visualizer ─────────
let audioCtx = null;
let analyser = null;
let mainSource = null;
let inlineSource = null;
let isVisualizing = false;

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    initParticles();
    
    // Bind main player events
    const mainPlayer = document.getElementById('audioPlayer');
    if (mainPlayer) {
        mainPlayer.addEventListener('play', () => {
            resumeAudioContext();
        });
    }

    refreshAll();
    setInterval(refreshAll, 3000);
});

function refreshAll() {
    refreshStats();
    refreshEntries();
    refreshHistory();
    refreshRecommendations();
}

// ── Drifting Canvas Particles Background ─────────────────────
function initParticles() {
    const canvas = document.getElementById('particlesCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;
    
    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });
    
    const particles = [];
    const particleCount = 45;
    
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: Math.random() * 2 + 1,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4,
            alpha: Math.random() * 0.5 + 0.2
        });
    }
    
    function animate() {
        requestAnimationFrame(animate);
        ctx.clearRect(0, 0, width, height);
        
        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            
            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;
            
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(99, 102, 241, ${p.alpha})`; // Indigo glow
            ctx.fill();
        });
    }
    
    animate();
}

// ── Web Audio API Visualizer Setup ────────────────────────────
function initAudioVisualizer() {
    if (audioCtx) return;
    
    try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64; // thick bars
        analyser.connect(audioCtx.destination);
        
        const mainPlayer = document.getElementById('audioPlayer');
        const inlinePlayer = document.getElementById('inlineAudioPlayer');
        
        // Connect players to visualizer
        mainSource = audioCtx.createMediaElementSource(mainPlayer);
        mainSource.connect(analyser);
        
        inlineSource = audioCtx.createMediaElementSource(inlinePlayer);
        inlineSource.connect(analyser);
        
        startWaveformDrawing();
    } catch (e) {
        console.error("Web Audio API not supported or initialization failed", e);
    }
}

function resumeAudioContext() {
    if (!audioCtx) {
        initAudioVisualizer();
    }
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function startWaveformDrawing() {
    if (isVisualizing) return;
    isVisualizing = true;
    
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function draw() {
        requestAnimationFrame(draw);
        
        const width = canvas.width = canvas.parentElement.clientWidth;
        const height = canvas.height = canvas.parentElement.clientHeight;
        
        analyser.getByteFrequencyData(dataArray);
        
        ctx.fillStyle = 'rgba(8, 14, 28, 0.9)';
        ctx.fillRect(0, 0, width, height);
        
        const barWidth = (width / bufferLength) * 1.5;
        let barHeight;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            barHeight = (dataArray[i] / 255) * height * 0.8;
            
            // Cyan/Indigo theme gradient
            const grad = ctx.createLinearGradient(0, height, 0, height - barHeight);
            grad.addColorStop(0, '#6366f1'); // Indigo
            grad.addColorStop(0.5, '#22d3ee'); // Cyan
            grad.addColorStop(1, '#34d399'); // Emerald
            
            ctx.fillStyle = grad;
            ctx.fillRect(x, height - barHeight, barWidth - 1.5, barHeight);
            
            x += barWidth;
        }
    }
    
    draw();
}

// ── Charts ───────────────────────────────────────────────────
function initCharts() {
    const chartColors = {
        indigo: '#818cf8', emerald: '#34d399', amber: '#fbbf24',
        violet: '#a78bfa', cyan: '#22d3ee', rose: '#fb7185',
        grid: 'rgba(99,102,241,0.06)', text: '#64748b',
    };

    // Latency History Line Chart
    const latencyCtx = document.getElementById('latencyChart').getContext('2d');
    latencyChart = new Chart(latencyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Latency (ms)',
                data: [],
                borderColor: chartColors.indigo,
                backgroundColor: 'rgba(129,140,248,0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: [],
                pointBorderColor: [],
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(12,18,34,0.95)',
                    borderColor: 'rgba(99,102,241,0.2)', borderWidth: 1,
                    titleFont: { family: 'Inter', size: 12 },
                    bodyFont: { family: 'Inter', size: 11 },
                    padding: 10, cornerRadius: 8,
                    callbacks: {
                        label: (ctx) => `${ctx.parsed.y.toFixed(1)} ms`
                    }
                }
            },
            scales: {
                x: { display: true, grid: { color: chartColors.grid }, ticks: { color: chartColors.text, font: { family: 'Inter', size: 10 }, maxTicksLimit: 10 } },
                y: { display: true, grid: { color: chartColors.grid }, ticks: { color: chartColors.text, font: { family: 'Inter', size: 10 }, callback: v => v + 'ms' }, beginAtZero: true }
            },
            interaction: { intersect: false, mode: 'index' },
        }
    });

    // Hit/Miss Doughnut Chart
    const hmCtx = document.getElementById('hitMissChart').getContext('2d');
    hitMissChart = new Chart(hmCtx, {
        type: 'doughnut',
        data: {
            labels: ['Cache Hits', 'Cache Misses', 'Fuzzy Hits'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [chartColors.emerald, chartColors.amber, chartColors.violet],
                borderColor: 'rgba(12,18,34,0.8)',
                borderWidth: 3,
                hoverOffset: 6,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: chartColors.text, font: { family: 'Inter', size: 11 }, padding: 12, usePointStyle: true, pointStyleWidth: 10 }
                },
                tooltip: {
                    backgroundColor: 'rgba(12,18,34,0.95)',
                    borderColor: 'rgba(99,102,241,0.2)', borderWidth: 1,
                    titleFont: { family: 'Inter', size: 12 },
                    bodyFont: { family: 'Inter', size: 11 },
                    padding: 10, cornerRadius: 8,
                }
            }
        }
    });
}

// ── TTS Synthesis ────────────────────────────────────────────
async function synthesize() {
    const text = document.getElementById('ttsText').value.trim();
    if (!text) { showToast('Please enter text to synthesize.', 'error'); return; }

    const btn = document.getElementById('synthesizeBtn');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Synthesizing...';

    // Stop inline preview if playing
    const inlinePlayer = document.getElementById('inlineAudioPlayer');
    if (inlinePlayer) {
        inlinePlayer.pause();
        playingKey = null;
    }

    try {
        const payload = {
            text, voice_id: document.getElementById('voiceId').value,
            speed: parseFloat(document.getElementById('speed').value),
            pitch: parseFloat(document.getElementById('pitch').value),
        };
        const resp = await fetch(`${API}/api/tts/synthesize`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail || 'Synthesis failed'); }
        const data = await resp.json();
        
        resumeAudioContext();
        displayResult(data);
        refreshAll();
    } catch (err) { showToast(`Error: ${err.message}`, 'error'); }
    finally { btn.disabled = false; btn.innerHTML = orig; }
}

function displayResult(data) {
    const area = document.getElementById('resultArea');
    const badge = document.getElementById('resultBadge');
    const latency = document.getElementById('resultLatency');
    const bar = document.getElementById('latencyBar');
    const player = document.getElementById('audioPlayer');

    area.style.display = 'block';
    area.style.animation = 'none'; area.offsetHeight; area.style.animation = '';

    if (data.cache_hit) {
        if (data.fuzzy_match) {
            badge.textContent = `AI MATCH (${Math.round(data.similarity_score * 100)}%)`;
            badge.className = 'result-badge fuzzy-badge';
        } else {
            badge.textContent = 'CACHE HIT';
            badge.className = 'result-badge hit';
        }
    } else {
        badge.textContent = 'CACHE MISS';
        badge.className = 'result-badge miss';
    }

    const ms = data.latency_ms;
    latency.textContent = `${ms.toFixed(1)} ms`;
    const isFast = ms < 100;
    latency.className = `result-latency ${isFast ? 'fast' : 'slow'}`;

    const barWidth = Math.min((ms / 5000) * 100, 100);
    bar.style.width = '0%';
    bar.className = `latency-bar ${isFast ? 'fast' : 'slow'}`;
    requestAnimationFrame(() => { bar.style.width = `${barWidth}%`; });

    player.src = `${API}${data.audio_url}`;
    player.load();
    player.play().catch(e => console.log("Auto-play prevented by browser policy"));

    // Update predictive cache notification banner
    const predNotify = document.getElementById('predictiveNotify');
    if (data.predictive_cache_triggered && data.predictive_cache_triggered.length > 0) {
        const predText = data.predictive_cache_triggered[0];
        document.getElementById('predictiveNotifyText').innerHTML = `AI pre-cached next interview question: <strong>"${escapeHtml(predText)}"</strong> in background.`;
        predNotify.style.display = 'flex';
    } else {
        predNotify.style.display = 'none';
    }

    const msg = data.cache_hit
        ? (data.fuzzy_match ? `AI fuzzy match! Served in ${ms.toFixed(1)}ms` : `Cache hit! Served in ${ms.toFixed(1)}ms`)
        : `Generated & cached in ${ms.toFixed(0)}ms`;
    showToast(msg, data.cache_hit ? 'success' : 'info');
}

// ── Stats ────────────────────────────────────────────────────
async function refreshStats() {
    try {
        const resp = await fetch(`${API}/api/cache/stats`);
        if (!resp.ok) return;
        const s = await resp.json();

        document.getElementById('statEntries').textContent = s.total_entries;
        document.getElementById('statMaxEntries').textContent = `/ ${s.max_entries} max`;
        document.getElementById('statHitRate').textContent = `${s.hit_rate_percent}%`;
        document.getElementById('statHitMiss').textContent = `${s.cache_hits} hits / ${s.cache_misses} misses`;

        const sizeMb = s.total_size_mb;
        document.getElementById('statSize').textContent = sizeMb < 1 ? `${(s.total_size_bytes / 1024).toFixed(1)} KB` : `${sizeMb} MB`;
        document.getElementById('statCompression').textContent = s.compression_enabled ? `Saved ${s.compression_ratio}%` : 'No compression';

        document.getElementById('statAvgHit').textContent = `${s.avg_hit_latency_ms} ms`;
        document.getElementById('statAvgMiss').textContent = `${s.avg_miss_latency_ms} ms`;
        document.getElementById('statFuzzyHits').textContent = s.fuzzy_hits;

        // Update doughnut chart
        const regularHits = s.cache_hits - s.fuzzy_hits;
        hitMissChart.data.datasets[0].data = [regularHits, s.cache_misses, s.fuzzy_hits];
        hitMissChart.update('none');
    } catch (e) {}
}

// ── History / Timeline ───────────────────────────────────────
async function refreshHistory() {
    try {
        const resp = await fetch(`${API}/api/cache/history`);
        if (!resp.ok) return;
        const history = await resp.json();

        const empty = document.getElementById('timelineEmpty');
        const list = document.getElementById('timelineList');
        const countBadge = document.getElementById('requestCount');

        countBadge.textContent = `${history.length} requests`;

        if (history.length === 0) { empty.style.display = 'flex'; list.style.display = 'none'; return; }
        empty.style.display = 'none'; list.style.display = 'block';

        // Update latency chart
        const last20 = history.slice(-20);
        latencyChart.data.labels = last20.map((_, i) => `#${history.length - last20.length + i + 1}`);
        latencyChart.data.datasets[0].data = last20.map(r => r.latency_ms);
        latencyChart.data.datasets[0].pointBackgroundColor = last20.map(r =>
            r.fuzzy_match ? '#a78bfa' : r.cache_hit ? '#34d399' : '#fbbf24'
        );
        latencyChart.data.datasets[0].pointBorderColor = last20.map(r =>
            r.fuzzy_match ? '#a78bfa' : r.cache_hit ? '#34d399' : '#fbbf24'
        );
        latencyChart.update('none');

        // Render timeline
        const recent = history.slice(-15).reverse();
        list.innerHTML = recent.map(r => {
            const dotClass = r.fuzzy_match ? 'fuzzy' : r.cache_hit ? 'hit' : 'miss';
            const tagClass = r.fuzzy_match ? 'fuzzy' : r.cache_hit ? 'hit' : 'miss';
            const tagText = r.fuzzy_match ? `AI (${Math.round(r.similarity_score * 100)}%)` : r.cache_hit ? 'Hit' : 'Miss';
            const truncText = r.text.length > 60 ? r.text.substring(0, 60) + '...' : r.text;
            const age = getAge(r.timestamp);
            return `
                <div class="timeline-item">
                    <span class="timeline-dot ${dotClass}"></span>
                    <span class="timeline-text" title="${escapeHtml(r.text)}">${escapeHtml(truncText)}</span>
                    <div class="timeline-tags"><span class="timeline-tag ${tagClass}">${tagText}</span></div>
                    <span class="timeline-latency">${r.latency_ms.toFixed(1)}ms</span>
                    <span class="timeline-time">${age}</span>
                </div>`;
        }).join('');
    } catch (e) {}
}

// ── Entries ──────────────────────────────────────────────────
async function refreshEntries() {
    try {
        const resp = await fetch(`${API}/api/cache/entries`);
        if (!resp.ok) return;
        const entries = await resp.json();

        cachedEntries = entries;

        // Dynamic Voice filter populate
        const voiceSelect = document.getElementById('filterVoice');
        const prevVoice = voiceSelect.value;
        const voices = [...new Set(entries.map(e => e.voice_id))];
        
        voiceSelect.innerHTML = '<option value="all">All Voices</option>';
        voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v;
            
            let name = v;
            if (v === 'default') name = 'Default (US)';
            else if (v === 'female-1') name = 'British';
            else if (v === 'male-1') name = 'Australian';
            else if (v === 'female-2') name = 'Indian';
            else if (v === 'male-2') name = 'Canadian';
            
            opt.textContent = name;
            voiceSelect.appendChild(opt);
        });

        // Restore voice select value
        if ([...voiceSelect.options].some(opt => opt.value === prevVoice)) {
            voiceSelect.value = prevVoice;
        } else {
            voiceSelect.value = 'all';
        }

        const countBadge = document.getElementById('entriesCount');
        countBadge.textContent = `${entries.length} ${entries.length === 1 ? 'entry' : 'entries'}`;

        const empty = document.getElementById('tableEmpty');
        const container = document.getElementById('tableContainer');

        if (entries.length === 0) {
            empty.style.display = 'flex';
            container.style.display = 'none';
            document.getElementById('emptyStateMessage').textContent = 'No cached entries yet';
            document.getElementById('emptyStateSub').textContent = 'Use the synthesizer or cache warming to generate entries';
            return;
        }

        // Apply filters
        filterEntries();
    } catch (e) {}
}

// ── Search & Filter Logic ────────────────────────────────────
function filterEntries() {
    const query = document.getElementById('searchEntries').value.toLowerCase().trim();
    const voice = document.getElementById('filterVoice').value;
    const dateRange = document.getElementById('filterDate').value;
    
    const tbody = document.getElementById('entriesTableBody');
    const container = document.getElementById('tableContainer');
    const empty = document.getElementById('tableEmpty');
    
    const now = new Date();
    
    const filtered = cachedEntries.filter(entry => {
        // Text search match
        const textMatch = entry.text.toLowerCase().includes(query);
        
        // Voice filter match
        const voiceMatch = voice === 'all' || entry.voice_id === voice;
        
        // Date filter match
        let dateMatch = true;
        if (dateRange !== 'all') {
            const created = new Date(entry.created_at);
            const diffMs = now - created;
            if (dateRange === '10m') {
                dateMatch = diffMs <= 10 * 60 * 1000;
            } else if (dateRange === '1h') {
                dateMatch = diffMs <= 60 * 60 * 1000;
            } else if (dateRange === 'today') {
                dateMatch = created.toDateString() === now.toDateString();
            }
        }
        
        return textMatch && voiceMatch && dateMatch;
    });
    
    if (filtered.length === 0) {
        tbody.innerHTML = '';
        container.style.display = 'none';
        empty.style.display = 'flex';
        document.getElementById('emptyStateMessage').textContent = 'No matching entries found';
        document.getElementById('emptyStateSub').textContent = 'Refine your search or filters';
        return;
    }
    
    empty.style.display = 'none';
    container.style.display = 'block';
    
    tbody.innerHTML = filtered.map(entry => {
        const age = getAge(entry.created_at);
        const sizeKb = (entry.file_size_bytes / 1024).toFixed(1);
        const saved = entry.compressed && entry.original_size_bytes > 0
            ? `${Math.round((1 - entry.file_size_bytes / entry.original_size_bytes) * 100)}%`
            : '--';
        const truncText = entry.text.length > 40 ? entry.text.substring(0, 40) + '...' : entry.text;
        
        const isCurrentPlaying = playingKey === entry.cache_key;
        const playBtnText = isCurrentPlaying ? '⏸' : '▶';
        const playBtnClass = isCurrentPlaying ? 'btn-inline-play playing' : 'btn-inline-play';
        const eqAnim = isCurrentPlaying 
            ? `<div class="equalizer-icon" title="Playing">
                 <div class="equalizer-bar"></div>
                 <div class="equalizer-bar"></div>
                 <div class="equalizer-bar"></div>
                 <div class="equalizer-bar"></div>
               </div>`
            : '';

        let voiceName = entry.voice_id;
        if (entry.voice_id === 'default') voiceName = 'US Accent';
        else if (entry.voice_id === 'female-1') voiceName = 'British';
        else if (entry.voice_id === 'male-1') voiceName = 'Australian';
        else if (entry.voice_id === 'female-2') voiceName = 'Indian';
        else if (entry.voice_id === 'male-2') voiceName = 'Canadian';

        return `
            <tr id="row-${entry.cache_key}">
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        ${eqAnim}
                        <span class="entry-text" title="${escapeHtml(entry.text)}">${escapeHtml(truncText)}</span>
                    </div>
                </td>
                <td><span class="entry-voice">${escapeHtml(voiceName)}</span></td>
                <td>${sizeKb} KB</td>
                <td><span class="entry-saved">${saved}</span></td>
                <td><span class="entry-hits">${entry.access_count}</span></td>
                <td><span class="entry-age">${age}</span></td>
                <td>
                    <button class="${playBtnClass}" onclick="playCachedInline('${entry.cache_key}', '${escapeHtml(entry.text).replace(/'/g, "\\'")}', '${entry.voice_id}', ${entry.speed}, ${entry.pitch})">
                        ${playBtnText}
                    </button>
                </td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteEntry('${entry.cache_key}')">x</button></td>
            </tr>`;
    }).join('');
}

// ── Inline Audio Playback ────────────────────────────────────
function playCachedInline(key, text, voiceId, speed, pitch) {
    const inlinePlayer = document.getElementById('inlineAudioPlayer');
    const mainPlayer = document.getElementById('audioPlayer');
    
    // Stop main player if playing
    mainPlayer.pause();
    
    resumeAudioContext();
    
    if (playingKey === key) {
        inlinePlayer.pause();
        playingKey = null;
        filterEntries();
        return;
    }
    
    playingKey = key;
    
    // Sync UI elements to match this voice preview
    const voiceSelect = document.getElementById('voiceId');
    if ([...voiceSelect.options].some(opt => opt.value === voiceId)) {
        voiceSelect.value = voiceId;
    }
    document.getElementById('speed').value = speed;
    document.getElementById('pitch').value = pitch;
    document.getElementById('ttsText').value = text;
    
    // Load source and play
    inlinePlayer.src = `${API}/api/cache/audio/${key}`;
    inlinePlayer.load();
    inlinePlayer.play()
        .then(() => {
            // Display Cache Preview details inside tester panel card
            const area = document.getElementById('resultArea');
            const badge = document.getElementById('resultBadge');
            const latency = document.getElementById('resultLatency');
            const bar = document.getElementById('latencyBar');
            
            area.style.display = 'block';
            badge.textContent = 'CACHE PREVIEW';
            badge.className = 'result-badge hit';
            latency.textContent = 'Serving from local cache';
            latency.className = 'result-latency fast';
            bar.style.width = '100%';
            bar.className = 'latency-bar fast';
            
            // Copy source to main audio player
            mainPlayer.src = inlinePlayer.src;
            
            filterEntries();
        })
        .catch(err => {
            showToast("Playback error", "error");
            playingKey = null;
            filterEntries();
        });
        
    inlinePlayer.onended = () => {
        playingKey = null;
        filterEntries();
    };
}

// ── Smart Recommendations ─────────────────────────────────────
async function refreshRecommendations() {
    try {
        const resp = await fetch(`${API}/api/cache/recommendations`);
        if (!resp.ok) return;
        const recs = await resp.json();
        
        const recsBody = document.getElementById('recsBody');
        if (recs.length === 0) {
            recsBody.innerHTML = '<div class="recs-loading">No recommendations available. Try using the synthesizer!</div>';
            return;
        }
        
        recsBody.innerHTML = recs.map(rec => {
            const btnClass = rec.cached ? 'btn-rec-action cached' : 'btn-rec-action miss';
            const btnText = rec.cached ? 'Ready' : 'Synthesize';
            const btnAction = rec.cached ? '' : `onclick="synthesizeFromRec('${escapeHtml(rec.text).replace(/'/g, "\\'")}')"`;
            const icon = rec.cached
                ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="color:var(--accent-emerald);"><polyline points="20 6 9 17 4 12"/></svg>`
                : `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;

            return `
                <div class="rec-card">
                    <div class="rec-info">
                        <span class="rec-text" title="${escapeHtml(rec.text)}">${escapeHtml(rec.text)}</span>
                        <span class="rec-reason">${escapeHtml(rec.reason)}</span>
                    </div>
                    <button class="${btnClass}" ${btnAction}>
                        <div style="display:flex; align-items:center; gap:4px;">
                            ${icon}
                            <span>${btnText}</span>
                        </div>
                    </button>
                </div>
            `;
        }).join('');
    } catch (e) {}
}

function synthesizeFromRec(text) {
    document.getElementById('ttsText').value = text;
    synthesize();
}

// ── Cache Management ─────────────────────────────────────────
async function deleteEntry(key) {
    try {
        const resp = await fetch(`${API}/api/cache/entry/${key}`, { method: 'DELETE' });
        if (resp.ok) { showToast('Entry removed', 'success'); refreshAll(); }
    } catch (e) { showToast('Failed to remove entry', 'error'); }
}

async function clearCache() {
    if (!confirm('Clear all cached entries?')) return;
    try {
        const resp = await fetch(`${API}/api/cache/clear`, { method: 'DELETE' });
        if (resp.ok) { const d = await resp.json(); showToast(`Cleared ${d.entries_removed} entries`, 'success'); refreshAll(); }
    } catch (e) { showToast('Failed to clear cache', 'error'); }
}

async function cleanupExpired() {
    try {
        const resp = await fetch(`${API}/api/cache/cleanup`, { method: 'POST' });
        if (resp.ok) { const d = await resp.json(); showToast(`Cleaned up ${d.entries_removed} expired entries`, 'info'); refreshAll(); }
    } catch (e) { showToast('Cleanup failed', 'error'); }
}

// ── Cache Warming ────────────────────────────────────────────
async function warmupCache() {
    const btn = document.getElementById('warmupBtn');
    const result = document.getElementById('warmupResult');
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Warming up...';
    result.style.display = 'none';

    try {
        const resp = await fetch(`${API}/api/cache/warmup`, { method: 'POST' });
        if (!resp.ok) throw new Error('Warmup failed');
        const data = await resp.json();
        result.style.display = 'block';
        result.innerHTML = `Warmed <strong>${data.prompts_warmed}</strong> prompts, skipped <strong>${data.prompts_skipped}</strong> already cached. (${data.total_prompts} total)`;
        showToast(`Cache warmed with ${data.prompts_warmed} prompts!`, 'warm');
        refreshAll();
    } catch (e) { showToast('Cache warming failed', 'error'); }
    finally { btn.disabled = false; btn.innerHTML = orig; }
}

// ── Utilities ────────────────────────────────────────────────
function getAge(isoDate) {
    const diff = Math.floor((new Date() - new Date(isoDate)) / 1000);
    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
}

function escapeHtml(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function showToast(message, type = 'info') {
    document.querySelectorAll('.toast').forEach(t => t.remove());
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.ctrlKey) synthesize(); });
