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

// Init
checkAuth();

// Version anzeigen
fetch(`${API_URL}/api/version`)
  .then(r => r.json())
  .then(data => {
    const el = document.getElementById('admin-version');
    if (el) el.textContent = `${data.app} v${data.version}`;
  })
  .catch(() => {});
