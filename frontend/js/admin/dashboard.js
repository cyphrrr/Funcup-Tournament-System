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
}
