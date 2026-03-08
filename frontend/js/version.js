// Version aus API laden und anzeigen
(function() {
  const el = document.getElementById('app-version');
  if (!el) return;

  const API = window.API_BASE || '';

  fetch(`${API}/api/version`)
    .then(r => r.json())
    .then(data => {
      el.textContent = `v${data.version}`;
      el.title = `${data.app} ${data.version} (${data.status})`;
    })
    .catch(() => {
      el.textContent = '';
    });
})();
