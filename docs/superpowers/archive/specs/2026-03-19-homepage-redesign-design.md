# Homepage Redesign — Design Spec

**Date:** 2026-03-19
**Status:** Approved

## Goal

Replace the current two-column News + Standings layout with a more informative, dashboard-like homepage that adapts automatically between group phase and KO phase.

## Architecture Overview

The homepage consists of three vertical zones:

1. **Hero Dashboard Bar** — compact status overview
2. **Main Content Area** — two-column grid: Tabs (2/3) + Sidebar (1/3)
3. **Footer** — unchanged

No backend changes required. All data comes from existing API endpoints.

### Data Sources

All API endpoints used by the homepage:

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /api/seasons` | Active season info | Public |
| `GET /api/seasons/{id}/groups-with-teams` | Groups, teams, and all matches | Public |
| `GET /api/groups/{id}/standings` | Per-group standings | Public |
| `GET /api/seasons/{id}/ko-brackets` | KO bracket data (all bracket types) | Public |
| `GET /api/news` | Published news articles | Public |
| `GET /api/teams/crests` | Team ID → crest URL mapping | Public |

### Active Season Resolution

From `GET /api/seasons`, find the season where `status == "active"`. If multiple active seasons exist, use the most recently created one (`max(created_at)`). If none is active, fall back to the first season in the list.

## 1. Hero Dashboard Bar

A horizontal bar directly below the header showing key tournament stats at a glance.

### Group Phase

| Stat | Source | Display |
|------|--------|---------|
| Season name | Active season `.name` | Plain text |
| Phase | Derived via phase detection (see Section 4) | Colored badge (green for group, red for KO) |
| Matchday | Derived via matchday calculation (see Section 5), shown as "SPx / SPy" (current/total) | Bold text |
| Teams | Active season `.participant_count` | Number |

### KO Phase

| Stat | Change |
|------|--------|
| Phase | Badge switches to "KO-Phase" (red) |
| Matchday → Runde | Derived from KO bracket: name of the lowest round number that has at least one match with `status != "played"` (e.g., round 2 = "Halbfinale") |
| Teams → Teams übrig | Count of distinct team IDs assigned to matches in the current (unfinished) round × 2, excluding byes |

### Responsive

- Desktop: single horizontal row with dividers
- Mobile (≤768px): 2×2 grid of stat cards

## 2. Tab System (Main Content Left — 2/3)

Two tabs during group phase: **Ergebnisse** | **News**
During KO phase: **KO-Ergebnisse** | **News**

### Tab: Ergebnisse (Group Phase)

- Results organized **by matchday**, newest first
- Current matchday expanded by default, showing all matches across all groups
- Each match row: `HomeTeam [crest] score AwayTeam [crest]`
  - Crests loaded from `GET /api/teams/crests` mapping, matched by `home_team_id`/`away_team_id`
- Played matches show score in primary-color badge; scheduled matches show `-:-` in muted style
- Older matchdays shown as collapsible accordions: "▸ Spieltag X (Y Spiele)"
  - Multiple accordions can be open simultaneously
  - Current matchday accordion is also closable
  - Simple toggle with no animation (CSS `display: none/block`)

**Data source:** `GET /api/seasons/{id}/groups-with-teams` → extract all matches from all groups, group by `matchday` field, sort descending.

### Tab: KO-Ergebnisse (KO Phase)

- Same layout but organized by KO round instead of matchday
- Current round expanded, previous rounds as accordions
- Shows bracket type label (Meister-Bracket, Lucky Loser, Loser)

**Data source:** `GET /api/seasons/{id}/ko-brackets` → iterate brackets, group matches by `round`.

### Tab: News

- Unchanged from current implementation
- News cards with title, date, author, content (with markdown rendering and match embeds)
- No parent card wrapper — news cards render directly

**Data source:** `GET /api/news`

### Tab Behavior

- Active tab stored in URL hash (`#ergebnisse`, `#news`) for shareability
- Default tab: Ergebnisse
- Tab state persists across page loads via hash

## 3. Sidebar (Right — 1/3)

### Group Phase: Compact Standings

- All group standings displayed vertically
- Each group: header "Gruppe X", then table with columns:
  - `#` — position (1-based index)
  - `Team` — team name with crest (from crests mapping)
  - `S` — Siege (wins) = `won` field from standings response
  - `U` — Unentschieden (draws) = `draw` field
  - `N` — Niederlagen (losses) = `lost` field
  - `Pkt` — Punkte (points) = `points` field
- Leader row (index 0) highlighted in primary color
- Team names link to `team.html?id=X`

**Data source:** `GET /api/groups/{id}/standings` for each group. Response fields: `team_id`, `played`, `won`, `draw`, `lost`, `goals_for`, `goals_against`, `points`.

### KO Phase: Mini Bracket

- Compact visual bracket for each bracket type (Meister, Lucky Loser, Loser)
- Shows match pairings with scores, winners highlighted
- Connected rounds with arrow indicators
- Links to full bracket on `ko.html`

**Data source:** `GET /api/seasons/{id}/ko-brackets`

### Responsive

- Mobile (≤768px): sidebar drops below tabs, full width

## 4. Phase Detection Logic

```
1. Resolve active season (see "Active Season Resolution" above)
2. Try GET /api/seasons/{id}/ko-brackets
3. If brackets exist (non-empty response) → KO phase
4. Else → Group phase
```

Bracket existence alone triggers KO phase — even if no KO matches have been played yet, the bracket structure should be visible.

This determines:
- Hero bar content (phase badge, matchday vs round, team count)
- Tab labels ("Ergebnisse" vs "KO-Ergebnisse")
- Tab content (group matches vs KO matches)
- Sidebar content (standings tables vs mini bracket)

## 5. Current Matchday Derivation

No dedicated API endpoint exists. Derived client-side:

```
1. Collect all matches from groups-with-teams response
2. Group by matchday
3. Find highest matchday that has at least one match with status="played"
   → That is the "current" matchday (SPx)
4. Total matchdays = max(matchday) across all matches (SPy)
5. Hero displays "SPx / SPy"
```

If no matches are played yet, show "SP0 / SPy".

## 6. Loading and Error States

### Loading

- Hero bar: stat values show "..." while loading
- Tabs: show `<em>Lade Ergebnisse...</em>` / `<em>Lade News...</em>`
- Sidebar: show `<em>Lade Tabellen...</em>`

### Errors

- If any API call fails, show inline error message in the affected section: "Fehler beim Laden" in `var(--danger)` color
- Other sections continue to work independently (partial failure is fine)
- No retry logic — user can reload the page

## 7. Files Changed

- `frontend/index.html` — complete rewrite of `<main>` section and `<script>` block
- No new files needed
- No backend changes
- No CSS file changes (styles remain inline in index.html)

## 8. What Stays Unchanged

- Header (logo, burger menu, dark mode toggle)
- Footer (backend status, copyright, theme selector)
- Navigation menu
- Theme system
- All other pages (turnier.html, ko.html, etc.)

## 9. Edge Cases

| Case | Behavior |
|------|----------|
| No active season | Hero shows "Keine aktive Saison", tabs and sidebar show placeholder messages |
| Multiple active seasons | Use most recently created one |
| Season with no matches yet | Ergebnisse tab shows "Noch keine Ergebnisse", standings show teams with 0 points |
| Season with no teams | Show "Keine Teams zugeordnet" in both tabs and sidebar |
| KO bracket generated but no matches played | Show bracket structure with `-:-` scores, phase is KO |
| API failure | Affected section shows error, other sections work independently |
