import { API_URL } from './config.js';

let crestCache = {};
const teamCache = {};
const CREST_CACHE_KEY = 'biw_crests';
const CREST_CACHE_TTL = 10 * 60 * 1000; // 10 minutes

export async function loadCrests() {
  // Check sessionStorage first
  try {
    const cached = sessionStorage.getItem(CREST_CACHE_KEY);
    if (cached) {
      const { data, ts } = JSON.parse(cached);
      if (Date.now() - ts < CREST_CACHE_TTL) {
        crestCache = data;
        return;
      }
    }
  } catch (e) { /* ignore parse errors */ }

  // Cache miss or expired — fetch
  try {
    crestCache = await fetch(`${API_URL}/api/teams/crests`).then(r => r.json());
    sessionStorage.setItem(CREST_CACHE_KEY, JSON.stringify({ data: crestCache, ts: Date.now() }));
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

export function registerTeamWithLogo(id, name, logo_url) {
  teamCache[id] = name;
  if (logo_url) {
    crestCache[String(id)] = logo_url;
  }
}
