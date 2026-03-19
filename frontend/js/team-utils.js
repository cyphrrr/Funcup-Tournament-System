import { API_URL } from './config.js';

let crestCache = {};
const teamCache = {};

export async function loadCrests() {
  try {
    crestCache = await fetch(`${API_URL}/api/teams/crests`).then(r => r.json());
  } catch (e) {
    console.warn('Crests konnten nicht geladen werden:', e);
  }
}

export function crestImg(teamId, size = 24) {
  if (!teamId) return '';
  const url = crestCache[String(teamId)];
  if (!url) return '';
  const src = url.startsWith('http') ? url : `${API_URL}${url}`;
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
