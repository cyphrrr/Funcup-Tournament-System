import { API_URL } from './config.js';

let crestCache = {};
const teamCache = {};
let crestsLoaded = false; // In-Memory-Guard: einmal pro Seitenaufruf laden

export async function loadCrests() {
  // Bewusst KEIN sessionStorage: das überlebte Reloads (auch Hard-Refresh) und
  // zeigte bis zu 10 Min veraltete Wappen. Jeder Seitenaufruf lädt jetzt frisch;
  // der In-Memory-Guard verhindert nur Doppel-Fetches innerhalb derselben Seite.
  if (crestsLoaded) return;
  try {
    crestCache = await fetch(`${API_URL}/api/teams/crests`).then(r => r.json());
    crestsLoaded = true;
  } catch (e) {
    console.warn('Crests konnten nicht geladen werden:', e);
  }
}

function escapeAttr(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function crestImg(teamId, size = 24) {
  if (!teamId) return '';
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = escapeAttr(url.startsWith('http') ? url : `${API_URL}${url}`);
  return `<img src="${src}" alt="" loading="lazy" style="width:${size}px;height:${size}px;object-fit:contain;vertical-align:middle;margin-right:4px;border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
}

export function teamName(id) {
  return teamCache[id] || `Team ${id}`;
}

export function registerTeams(groups) {
  groups.forEach(g => g.teams.forEach(t => { teamCache[t.id] = t.name; }));
}

export function registerTeam(id, name) {
  teamCache[id] = name;
}

export function registerTeamWithLogo(id, name, logo_url) {
  teamCache[id] = name;
  if (logo_url) {
    crestCache[String(id)] = logo_url;
  }
}
