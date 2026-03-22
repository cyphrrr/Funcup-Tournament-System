# Bereich D: Visuelle Konsistenz — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 visual inconsistencies across the public frontend pages.

**Architecture:** CSS additions to `shared.css`, minor HTML edits to individual pages, JS refactor for archiv.html KO-API migration.

**Tech Stack:** Vanilla HTML/CSS/JS, no build process.

---

### Task 1: Add header subtitle "/ Start" to index.html

**Files:**
- Modify: `frontend/index.html:88`

- [ ] **Step 1: Add subtitle span**

On line 88, after `<span style="color:var(--primary)">Pokal</span>`, add the subtitle span:

```html
<!-- Before -->
<span style="color:var(--text)">BIW</span><span style="color:var(--primary)">Pokal</span>

<!-- After -->
<span style="color:var(--text)">BIW</span><span style="color:var(--primary)">Pokal</span><span style="opacity:0.4;font-weight:400;font-size:1rem;margin-left:0.3rem">/ Start</span>
```

- [ ] **Step 2: Verify visually**

Open index.html — header should now show "BIW Pokal / Start" with the subtitle in faded text, matching all other pages.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "fix: add header subtitle '/ Start' to index.html for consistency"
```

---

### Task 2: Move `.season-item` styles to shared.css

**Files:**
- Modify: `frontend/css/shared.css` (add before Footer section)
- Modify: `frontend/turnier.html:19-21` (remove 3 `.season-item` lines)
- Modify: `frontend/ko.html:17-19` (remove 3 `.season-item` lines)

- [ ] **Step 1: Add `.season-item` rules to shared.css**

Add before the `/* === Footer === */` section (around line 350), as a new section:

```css
/* === Season Items === */
.season-item {
  padding: .5rem 1rem;
  cursor: pointer;
  border-radius: 8px;
  transition: all .2s;
  background: var(--card);
  border: 1px solid var(--border);
  font-size: .9rem;
  white-space: nowrap;
}

.season-item:hover {
  background: color-mix(in srgb, var(--primary) 10%, var(--card));
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
}

.season-item.active {
  background: color-mix(in srgb, var(--primary) 15%, var(--card));
  color: var(--primary);
  font-weight: 600;
  border-color: var(--primary);
}
```

- [ ] **Step 2: Remove `.season-item` from turnier.html**

Remove these 3 lines from the `<style>` block (lines 19-21):
```css
.season-item{padding:.5rem 1rem;cursor:pointer;border-radius:8px;transition:all .2s;background:var(--card);border:1px solid var(--border);font-size:.9rem;white-space:nowrap}
.season-item:hover{background:color-mix(in srgb,var(--primary) 10%,var(--card));border-color:var(--primary);transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
.season-item.active{background:color-mix(in srgb,var(--primary) 15%,var(--card));color:var(--primary);font-weight:600;border-color:var(--primary)}
```

- [ ] **Step 3: Remove `.season-item` from ko.html**

Remove these 3 lines from the `<style>` block (lines 17-19):
```css
.season-item{padding:.5rem;margin:.25rem 0;cursor:pointer;border-radius:6px;transition:background .2s;display:inline-block}
.season-item:hover{background:color-mix(in srgb,var(--primary) 10%,var(--card))}
.season-item.active{background:color-mix(in srgb,var(--primary) 15%,var(--card));color:var(--primary);font-weight:600}
```

- [ ] **Step 4: Verify both pages**

Open turnier.html and ko.html — season items should look identical (chips with border, lift-hover, active highlight).

- [ ] **Step 5: Commit**

```bash
git add frontend/css/shared.css frontend/turnier.html frontend/ko.html
git commit -m "fix: unify .season-item styling in shared.css"
```

---

### Task 3: Add `.btn` classes to shared.css

**Files:**
- Modify: `frontend/css/shared.css` (add after Season Items section)
- Modify: `frontend/dashboard.html:42-49` (remove 8 `.btn` lines)

- [ ] **Step 1: Add `.btn` rules to shared.css**

Add after the Season Items section, before Footer:

```css
/* === Buttons === */
.btn {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  padding: .6rem 1.25rem;
  border: none;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background .2s, opacity .2s;
}

.btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  opacity: .85;
}

.btn-danger {
  background: var(--danger, #dc2626);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  opacity: .85;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}

.btn-outline:hover:not(:disabled) {
  background: var(--card-alt);
}
```

- [ ] **Step 2: Remove `.btn` block from dashboard.html**

Remove these 8 lines from the `<style>` block (lines 42-49):
```css
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.6rem 1.25rem;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;transition:background .2s,opacity .2s}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover:not(:disabled){background:#059669}
.btn-danger{background:var(--danger);color:#fff}
.btn-danger:hover:not(:disabled){background:#b91c1c}
.btn-outline{background:transparent;border:1px solid var(--border);color:var(--text)}
.btn-outline:hover:not(:disabled){background:var(--card-alt)}
```

- [ ] **Step 3: Verify dashboard.html**

Open dashboard.html — all buttons should render identically. Check: Discord login button, save buttons, danger buttons.

- [ ] **Step 4: Commit**

```bash
git add frontend/css/shared.css frontend/dashboard.html
git commit -m "fix: add global .btn classes to shared.css, remove from dashboard.html"
```

---

### Task 4: Migrate archiv.html KO-API from `/ko-bracket` to `/ko-brackets`

**Files:**
- Modify: `frontend/archiv.html` (JS: lines 238-346)

**Context:** The new `/ko-brackets` API returns a different structure:
```json
{
  "season_id": 1,
  "brackets": {
    "meister": {
      "bracket_id": 1, "status": "completed",
      "rounds": {
        "runde_1": [
          { "match_id": 1, "round": "Halbfinale",
            "home_team": {"id": 1, "name": "Team A"}, "away_team": {"id": 2, "name": "Team B"},
            "home_goals": 2, "away_goals": 1, "winner_id": 1,
            "is_bye": false, "is_third_place": false, "status": "played" }
        ]
      }
    },
    "lucky_loser": { ... },
    "loser": { ... }
  }
}
```

Key differences from old API:
- Teams are objects `{id, name}` instead of plain IDs (`home_team_id`)
- Rounds are keyed by `runde_N` strings, not numeric
- Each match has a `round` field with display name (e.g., "Finale")
- 3 separate brackets instead of one flat list

**Important:** Archived seasons (pre-v2) may not have data in the new API. The code must try `/ko-brackets` first, and fall back to `/ko-bracket` (old) if the new one returns empty or 404.

- [ ] **Step 1: Rewrite the KO-Phase fetch block (lines 238-266)**

Replace the existing KO-Phase try/catch block with:

```javascript
// KO-Phase (v2: 3-Bracket-System, fallback auf v1 für alte Saisons)
try {
  let koHtml = '';
  const bResp = await fetch(`${API}/api/seasons/${seasonId}/ko-brackets`);
  const bData = bResp.ok ? await bResp.json() : null;
  const hasBrackets = bData && bData.brackets && Object.values(bData.brackets).some(b => b && b.rounds && Object.keys(b.rounds).length > 0);

  if (hasBrackets) {
    // v2: Multiple brackets
    const bracketLabels = {meister: 'Meister-Bracket', lucky_loser: 'Lucky Loser', loser: 'Verlierer-Bracket'};
    for (const [type, label] of Object.entries(bracketLabels)) {
      const b = bData.brackets[type];
      if (!b || !b.rounds || Object.keys(b.rounds).length === 0) continue;
      koHtml += `<div class="card" style="margin-top:1.5rem"><h3 style="margin:0 0 .75rem;font-size:1rem">KO: ${label}</h3>`;
      koHtml += renderCompactBracketV2(b);
      koHtml += '</div>';
    }
    // Champion from meister bracket finale
    const meister = bData.brackets.meister;
    if (meister && meister.rounds) {
      const allMatches = Object.values(meister.rounds).flat();
      const finale = allMatches.find(m => m.round === 'Finale' && m.status === 'played');
      if (finale && finale.winner_id) {
        const winnerTeam = finale.home_team && finale.winner_id === finale.home_team.id ? finale.home_team : finale.away_team;
        const winnerName = winnerTeam ? winnerTeam.name : teamName(finale.winner_id);
        html = `<div class="champion-badge">🏆 Pokalsieger: ${winnerName}</div>` + html;
      }
    }
  } else {
    // v1 fallback for archived seasons
    const bracket = await fetch(`${API}/api/seasons/${seasonId}/ko-bracket`).then(r => {
      if (r.status === 404) return null;
      return r.json();
    });
    if (bracket) {
      koHtml += '<div class="card" style="margin-top:1.5rem"><h3 style="margin:0 0 .75rem;font-size:1rem">KO-Phase</h3>';
      koHtml += renderCompactBracket(bracket);
      koHtml += '</div>';
      const finalMatch = bracket.matches.find(m => m.round === bracket.total_rounds);
      if (finalMatch && finalMatch.status === 'played') {
        const winnerId = finalMatch.home_goals > finalMatch.away_goals ? finalMatch.home_team_id : finalMatch.away_team_id;
        html = `<div class="champion-badge">🏆 Pokalsieger: ${teamName(winnerId)}</div>` + html;
      }
    }
  }

  if (koHtml) {
    html += koHtml;
  } else {
    html += '<div class="card" style="margin-top:1.5rem"><h3 style="margin:0 0 .75rem;font-size:1rem">KO-Phase</h3>';
    html += '<p style="color:var(--muted)">Noch nicht gestartet</p></div>';
  }
} catch (e) {
  html += '<div class="card" style="margin-top:1.5rem"><h3 style="margin:0 0 .75rem;font-size:1rem">KO-Phase</h3>';
  html += '<p style="color:var(--muted)">Noch nicht gestartet</p></div>';
}
```

- [ ] **Step 2: Add `renderCompactBracketV2()` function**

Add this new function after the existing `renderCompactBracket()` function (after line 346):

```javascript
function renderCompactBracketV2(bracket) {
  if (!bracket || !bracket.rounds) return '';
  const roundKeys = Object.keys(bracket.rounds).sort((a,b) => {
    const numA = parseInt(a.replace('runde_',''));
    const numB = parseInt(b.replace('runde_',''));
    return numA - numB;
  });

  let html = '<div class="ko-bracket-compact">';
  let thirdPlaceMatch = null;

  for (const key of roundKeys) {
    const matches = bracket.rounds[key];
    if (!matches || matches.length === 0) continue;
    const roundLabel = matches[0].round || key;

    html += `<div class="ko-round-compact">
      <div class="ko-round-header-compact">${roundLabel}</div>`;

    for (const m of matches) {
      if (m.is_third_place) { thirdPlaceMatch = m; continue; }
      if (m.is_bye) {
        const byeName = m.home_team ? m.home_team.name : (m.home_team_id ? teamName(m.home_team_id) : '?');
        const byeCrest = m.home_team ? crestImg(m.home_team.id) : (m.home_team_id ? crestImg(m.home_team_id) : '');
        html += `<div class="ko-match-compact" style="opacity:.6">
          <div style="text-align:center;font-size:.75rem">${byeCrest}${byeName} – Freilos</div></div>`;
      } else if (!m.home_team && !m.away_team) {
        html += `<div class="ko-match-compact"><div style="text-align:center;color:var(--muted);font-size:.75rem">TBD</div></div>`;
      } else {
        const cls = m.status === 'played' ? 'played' : '';
        const hasResult = m.home_goals !== null && m.away_goals !== null;
        const homeWin = hasResult && m.home_goals > m.away_goals;
        const awayWin = hasResult && m.away_goals > m.home_goals;
        const homeName = m.home_team ? m.home_team.name : '?';
        const awayName = m.away_team ? m.away_team.name : '?';
        const homeId = m.home_team ? m.home_team.id : null;
        const awayId = m.away_team ? m.away_team.id : null;

        html += `<div class="ko-match-compact ${cls}">
          <div class="ko-team-compact ${homeWin ? 'winner' : ''}">
            <span>${homeId ? crestImg(homeId) + homeName : homeName}</span>
            <span>${hasResult ? m.home_goals : ''}</span>
          </div>
          <div class="ko-team-compact ${awayWin ? 'winner' : ''}">
            <span>${awayId ? crestImg(awayId) + awayName : awayName}</span>
            <span>${hasResult ? m.away_goals : ''}</span>
          </div>
        </div>`;
      }
    }
    html += '</div>';
  }

  // Spiel um Platz 3
  if (thirdPlaceMatch) {
    const m = thirdPlaceMatch;
    const hasResult = m.home_goals !== null && m.away_goals !== null;
    const homeWin = hasResult && m.home_goals > m.away_goals;
    const awayWin = hasResult && m.away_goals > m.home_goals;
    const cls = m.status === 'played' ? 'played' : '';
    const homeName = m.home_team ? m.home_team.name : '?';
    const awayName = m.away_team ? m.away_team.name : '?';
    const homeId = m.home_team ? m.home_team.id : null;
    const awayId = m.away_team ? m.away_team.id : null;
    html += `<div class="ko-round-compact" style="border-left:2px dashed var(--border);padding-left:1rem">
      <div class="ko-round-header-compact" style="font-style:italic">Platz 3</div>
      <div class="ko-match-compact ${cls}">
        <div class="ko-team-compact ${homeWin ? 'winner' : ''}">
          <span>${homeId ? crestImg(homeId) + homeName : homeName}</span>
          <span>${hasResult ? m.home_goals : ''}</span>
        </div>
        <div class="ko-team-compact ${awayWin ? 'winner' : ''}">
          <span>${awayId ? crestImg(awayId) + awayName : awayName}</span>
          <span>${hasResult ? m.away_goals : ''}</span>
        </div>
      </div>
    </div>`;
  }

  html += '</div>';
  return html;
}
```

- [ ] **Step 3: Verify archiv.html**

Test with:
1. An active/current season (should use v2 API, show 3 brackets)
2. An archived season (may fall back to v1 API, show single bracket)
3. A season with no KO phase (should show "Noch nicht gestartet")

- [ ] **Step 4: Commit**

```bash
git add frontend/archiv.html
git commit -m "fix: migrate archiv.html KO-API from /ko-bracket to /ko-brackets with v1 fallback"
```

---

### Task 5: Update frontend-todo.md

**Files:**
- Modify: `docs/frontend-todo.md`

- [ ] **Step 1: Mark Bereich D items as done**

Check off the completed items in the Bereich D section:
```markdown
- [x] Header-Subtitel-Konvention klären (mit/ohne auf Index?)
- [x] `.season-item`-Styling vereinheitlichen (turnier vs. ko)
- [ ] Tabellen-Alignment konsistent machen (kein Handlungsbedarf — verschiedene Spaltentypen)
- [x] Button-Klassen (`.btn`, `.btn-primary`) in `shared.css` global verfügbar machen
- [x] Archiv: KO-API auf neues Format (`/ko-brackets`) migrieren
```

- [ ] **Step 2: Add Umsetzungslog entry**

Add to the Umsetzungslog:
```markdown
- **2026-03-19: Bereich D (Visuelle Konsistenz) abgeschlossen** — Header-Subtitel auf index.html, .season-item und .btn in shared.css vereinheitlicht, archiv.html KO-API auf /ko-brackets migriert.
```

- [ ] **Step 3: Commit**

```bash
git add docs/frontend-todo.md
git commit -m "docs: mark Bereich D (visual consistency) as complete"
```
