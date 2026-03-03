// init.js — DOMContentLoaded + Event-Listener (API_URL muss vorher geladen sein)

// Enter key on login
document.getElementById('login-pass')?.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') doLogin();
});

// Navigation
document.querySelectorAll('.sidebar nav a').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    showSection(link.dataset.section);
  });
});

// Tab-Events für Anmeldungen
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.anm-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.anm-tab-content').forEach(c => c.style.display = 'none');
      document.getElementById(`anm-tab-${btn.dataset.tab}`).style.display = '';
      document.querySelectorAll('.anm-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (btn.dataset.tab === 'alle-user') loadAlleDiscordUser();
    });
  });

  document.querySelectorAll('.anm-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.anm-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyAnmFilter();
    });
  });

  const modal = document.getElementById('team-assign-modal');
  if (modal) {
    modal.addEventListener('click', e => {
      if (e.target === e.currentTarget) closeTeamAssignModal();
    });
  }
});

// Init
checkAuth();
