// admin/dashboard.js — Dashboard-Statistiken

async function loadDashboard() {
  try {
    const seasons = await fetch(`${API_URL}/api/seasons`).then(r => r.json());
    document.getElementById('stat-seasons').textContent = seasons.length;

    let totalTeams = 0, played = 0, pending = 0;
    const allGroups = await Promise.all(
      seasons.map(s => fetch(`${API_URL}/api/seasons/${s.id}/groups-with-teams`).then(r => r.json()))
    );
    allGroups.forEach(groups => {
      groups.forEach(g => {
        totalTeams += g.teams.length;
        g.matches.forEach(m => {
          if (m.status === 'played') played++;
          else pending++;
        });
      });
    });
    document.getElementById('stat-teams').textContent = totalTeams;
    document.getElementById('stat-matches').textContent = played;
    document.getElementById('stat-pending').textContent = pending;
  } catch (e) {
    console.error(e);
  }

  loadTrafficStats(7);
}

// Traffic Stats
let trafficChart = null;

async function loadTrafficStats(days) {
  // Toggle active button
  document.querySelectorAll('.stats-period').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.days) === days);
    if (parseInt(b.dataset.days) === days) {
      b.style.background = 'var(--accent-dark)';
      b.style.color = '#fff';
    } else {
      b.style.background = '';
      b.style.color = '';
    }
  });

  try {
    const res = await authFetch(`${API_URL}/api/admin/stats?days=${days}`);
    const data = await res.json();

    // Summary numbers (for selected period)
    const periodKey = days <= 7 ? 'last_7_days' : 'last_30_days';
    document.getElementById('traffic-visitors').textContent = data.summary[periodKey].visitors;
    document.getElementById('traffic-views').textContent = data.summary[periodKey].views;

    // Chart
    const labels = data.daily.map(d => {
      const dt = new Date(d.date);
      return dt.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
    });
    const visitorsData = data.daily.map(d => d.visitors);
    const viewsData = data.daily.map(d => d.views);

    const ctx = document.getElementById('traffic-chart').getContext('2d');
    if (trafficChart) trafficChart.destroy();

    trafficChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Besucher',
            data: visitorsData,
            borderColor: '#7c7cff',
            backgroundColor: 'rgba(124,124,255,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
          },
          {
            label: 'Aufrufe',
            data: viewsData,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#aaaabc', font: { size: 12 } },
          },
        },
        scales: {
          x: {
            ticks: { color: '#aaaabc', font: { size: 11 } },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y: {
            beginAtZero: true,
            ticks: { color: '#aaaabc', font: { size: 11 }, precision: 0 },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
      },
    });

    // Table
    const s = data.summary;
    const rows = [
      ['Heute', s.today],
      ['Gestern', s.yesterday],
      ['Letzte 7 Tage', s.last_7_days],
      ['Letzte 30 Tage', s.last_30_days],
      ['Gesamt', s.total],
    ];
    document.getElementById('traffic-table').innerHTML = rows.map(([label, v]) =>
      `<tr><td>${label}</td><td>${v.visitors}</td><td>${v.views}</td></tr>`
    ).join('');
  } catch (e) {
    console.error('Traffic stats error:', e);
  }
}
