// admin/dashboard.js — Dashboard: Traffic + Aktive Saison + Anmeldungen

// ─── Utility ────────────────────────────────────────────────────────────────

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ─── loadDashboard ──────────────────────────────────────────────────────────

async function loadDashboard() {
  // Alle drei Bereiche parallel laden
  await Promise.all([
    loadTrafficStats(7),
    loadSeasonWidget(),
    loadAnmeldungenWidget(),
  ]);
}

// ─── Traffic ────────────────────────────────────────────────────────────────

let trafficChart = null;

async function loadTrafficStats(days) {
  // Buttons aktualisieren
  document.querySelectorAll('.stats-period').forEach(b => {
    const active = parseInt(b.dataset.days) === days;
    b.classList.toggle('active', active);
    b.style.background = active ? 'var(--accent-dark, #5b5bf0)' : '';
    b.style.color = active ? '#fff' : '';
  });

  try {
    const res = await authFetch(`${API_URL}/api/admin/stats?days=${days}`);
    const data = await res.json();

    // Headline-Zahlen (passend zum gewählten Zeitraum)
    const periodKey = days <= 7 ? 'last_7_days' : 'last_30_days';
    document.getElementById('traffic-visitors').textContent = data.summary[periodKey].visitors;
    document.getElementById('traffic-views').textContent = data.summary[periodKey].views;

    // Chart
    const labels = data.daily.map(d =>
      new Date(d.date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
    );

    const ctx = document.getElementById('traffic-chart').getContext('2d');
    if (trafficChart) trafficChart.destroy();

    trafficChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Besucher',
            data: data.daily.map(d => d.visitors),
            borderColor: '#7c7cff',
            backgroundColor: 'rgba(124,124,255,0.1)',
            fill: true, tension: 0.3, pointRadius: 3,
          },
          {
            label: 'Aufrufe',
            data: data.daily.map(d => d.views),
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.1)',
            fill: true, tension: 0.3, pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#aaaabc', font: { size: 12 } } } },
        scales: {
          x: { ticks: { color: '#aaaabc', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { beginAtZero: true, ticks: { color: '#aaaabc', font: { size: 11 }, precision: 0 }, grid: { color: 'rgba(255,255,255,0.05)' } },
        },
      },
    });

    // Tabelle
    const s = data.summary;
    document.getElementById('traffic-table').innerHTML = [
      ['Heute', s.today],
      ['Gestern', s.yesterday],
      ['Letzte 7 Tage', s.last_7_days],
      ['Letzte 30 Tage', s.last_30_days],
      ['Gesamt', s.total],
    ].map(([label, v]) =>
      `<tr><td>${label}</td><td>${v.visitors}</td><td>${v.views}</td></tr>`
    ).join('');

  } catch (e) {
    console.error('Traffic stats error:', e);
  }
}

// ─── Aktive Saison Widget ────────────────────────────────────────────────────

async function loadSeasonWidget() {
  const el = document.getElementById('dashboard-season-content');

  try {
    const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());
    const active = seasons.find(s => s.status === 'active');

    if (!active) {
      el.innerHTML = `<p style="color:var(--text-muted);font-size:.9rem">Keine aktive Saison.</p>`;
      return;
    }

    // Gruppen + Matches der aktiven Saison laden
    const groups = await fetch(`${API_URL}/api/seasons/${active.id}/groups-with-teams`).then(r => r.json());

    // KO-Status prüfen
    let isKO = false;
    try {
      const koRes = await fetch(`${API_URL}/api/seasons/${active.id}/ko-brackets`);
      const koData = await koRes.json();
      isKO = Array.isArray(koData) && koData.length > 0;
    } catch (_) {}

    // Team-Map aufbauen (id → name) aus allen Gruppen
    const teamMap = {};
    groups.forEach(g => (g.teams || []).forEach(t => { teamMap[t.id] = t.name; }));

    // Alle Matches aggregieren
    const allMatches = groups.flatMap(g => (g.matches || []).map(m => ({ ...m, groupName: g.group.name })));

    // Spieltag-Stand ermitteln
    const matchdays = [...new Set(allMatches.map(m => m.matchday).filter(Boolean))].sort((a, b) => a - b);
    const totalMatchdays = matchdays.length > 0 ? Math.max(...matchdays) : 0;
    const playedMatchdays = matchdays.filter(md => allMatches.some(m => m.matchday === md && m.status === 'played'));
    const currentMatchday = playedMatchdays.length > 0 ? Math.max(...playedMatchdays) : 0;

    // Offene Matches (status !== 'played'), sortiert nach Gruppe
    const openMatches = allMatches
      .filter(m => m.status !== 'played' && m.home_team_id && m.away_team_id)
      .sort((a, b) => a.groupName.localeCompare(b.groupName));

    // Phase-Badge
    const phaseBadge = isKO
      ? `<span style="background:#4a1f6e;color:#c084fc;padding:.2rem .6rem;border-radius:12px;font-size:.8rem;font-weight:600">🏆 KO-Phase</span>`
      : `<span style="background:#1a3a1a;color:#4ade80;padding:.2rem .6rem;border-radius:12px;font-size:.8rem;font-weight:600">🟢 Gruppenphase</span>`;

    // Spieltag-Zeile (nur in Gruppenphase sinnvoll)
    const spieltagHtml = !isKO && totalMatchdays > 0
      ? `<div style="color:var(--text-muted);font-size:.85rem;margin-top:.4rem">Spieltag <strong style="color:var(--text-primary)">SP${currentMatchday}</strong> / SP${totalMatchdays}</div>`
      : '';

    // Offene Ergebnisse
    let openHtml = '';
    if (openMatches.length === 0) {
      openHtml = `<div style="color:#4ade80;font-size:.85rem;margin-top:.75rem">✅ Alle Ergebnisse aktuell</div>`;
    } else {
      const MAX_SHOW = 8;
      const shown = openMatches.slice(0, MAX_SHOW);
      const rest = openMatches.length - MAX_SHOW;
      const homeName = (m) => teamMap[m.home_team_id] || '?';
      const awayName = (m) => teamMap[m.away_team_id] || '?';
      openHtml = `
        <div style="margin-top:.75rem">
          <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:.4rem;text-transform:uppercase;letter-spacing:.04em">⏳ Offene Ergebnisse (${openMatches.length})</div>
          <div style="display:flex;flex-direction:column;gap:.3rem">
            ${shown.map(m => `
              <div style="font-size:.85rem;display:flex;gap:.4rem;align-items:center">
                <span style="color:var(--text-muted);font-size:.75rem;min-width:1.4rem">Gr.${escapeHtml(m.groupName)}</span>
                <span style="color:var(--text-primary)">${escapeHtml(homeName(m))} – ${escapeHtml(awayName(m))}</span>
              </div>
            `).join('')}
            ${rest > 0 ? `<div style="font-size:.8rem;color:var(--text-muted)">… und ${rest} weitere</div>` : ''}
          </div>
        </div>`;
    }

    el.innerHTML = `
      <div style="font-size:1.1rem;font-weight:600;color:var(--text-primary);margin-bottom:.4rem">${escapeHtml(active.name)}</div>
      <div style="display:flex;align-items:center;gap:.5rem">${phaseBadge}${spieltagHtml}</div>
      ${openHtml}
    `;

  } catch (e) {
    el.innerHTML = `<p style="color:var(--danger);font-size:.85rem">Fehler beim Laden.</p>`;
    console.error('Season widget error:', e);
  }
}

// ─── Anmeldungen Widget ──────────────────────────────────────────────────────

async function loadAnmeldungenWidget() {
  const el = document.getElementById('dashboard-anmeldungen-content');

  try {
    // /api/admin/anmeldungen benötigt Auth → authFetch nutzen
    const res = await authFetch(`${API_URL}/api/admin/anmeldungen`);
    const teams = await res.json();

    const total = teams.length;
    const dabei = teams.filter(t => t.participating_next).length;
    const nichtDabei = teams.filter(t => !t.participating_next).slice(0, 8);
    const nichtDabeiCount = teams.filter(t => !t.participating_next).length;

    // Progress Bar
    const pct = total > 0 ? Math.round((dabei / total) * 100) : 0;
    const progressColor = pct >= 80 ? '#4ade80' : pct >= 50 ? '#facc15' : '#f87171';

    // Nicht-Dabei-Liste
    let nichtDabeiHtml = '';
    if (nichtDabeiCount === 0) {
      nichtDabeiHtml = `<div style="color:#4ade80;font-size:.85rem;margin-top:.75rem">✅ Alle Teams angemeldet</div>`;
    } else {
      nichtDabeiHtml = `
        <div style="margin-top:.75rem">
          <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:.4rem;text-transform:uppercase;letter-spacing:.04em">Nicht bestätigt (${nichtDabeiCount})</div>
          <div style="display:flex;flex-direction:column;gap:.25rem">
            ${nichtDabei.map(t => `
              <div style="font-size:.85rem;color:var(--text-primary);display:flex;align-items:center;gap:.4rem">
                <span style="color:#f87171;font-size:.7rem">●</span>
                ${escapeHtml(t.team_name)}
              </div>
            `).join('')}
            ${nichtDabeiCount > 8 ? `<div style="font-size:.8rem;color:var(--text-muted)">… und ${nichtDabeiCount - 8} weitere</div>` : ''}
          </div>
        </div>`;
    }

    el.innerHTML = `
      <div style="font-size:1.4rem;font-weight:700;color:var(--text-primary)">${dabei} <span style="font-size:1rem;font-weight:400;color:var(--text-muted)">/ ${total} dabei</span></div>
      <div style="margin:.6rem 0 0;background:var(--bg-elevated);border-radius:6px;height:8px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${progressColor};border-radius:6px;transition:width .4s ease"></div>
      </div>
      <div style="font-size:.8rem;color:var(--text-muted);margin-top:.3rem">${pct}% bestätigt</div>
      ${nichtDabeiHtml}
      <div style="margin-top:1rem">
        <a href="#" onclick="showSection('teams');return false" style="font-size:.85rem;color:var(--primary)">→ Alle Teams verwalten</a>
      </div>
    `;

  } catch (e) {
    el.innerHTML = `<p style="color:var(--danger);font-size:.85rem">Fehler beim Laden.</p>`;
    console.error('Anmeldungen widget error:', e);
  }
}
