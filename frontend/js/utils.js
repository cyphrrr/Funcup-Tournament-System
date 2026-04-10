// utils.js — Toast, escapeHtml, insertAtCursor, showSection

function toast(msg, type = 'success') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function insertAtCursor(textarea, text) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const before = textarea.value.substring(0, start);
  const after = textarea.value.substring(end);

  textarea.value = before + text + after;

  const newPos = start + text.length;
  textarea.setSelectionRange(newPos, newPos);
  textarea.focus();
}

function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
  document.getElementById(name)?.classList.add('active');
  document.querySelector(`[data-section="${name}"]`)?.classList.add('active');

  if (name === 'matches') loadMatchSeasons();
  if (name === 'teams') loadAllTeams();
  if (name === 'discord-users') loadDiscordUsersList();
  if (name === 'news') {
    loadNews();
    loadMatchInserterSeasons();
  }
  if (name === 'ko-phase') loadKOSeasons();
  if (name === 'design') loadBackgrounds();
  if (name === 'saison-setup') initSaisonSetup();
}
