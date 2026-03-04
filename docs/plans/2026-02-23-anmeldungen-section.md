# Anmeldungen-Section Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bestehende "Discord Users"-Section im Admin Panel durch eine neue "Anmeldungen"-Section ersetzen, die Turnier-Anmeldungen mit Inline-Aktionen zeigt und die Sidebar logisch neu ordnet.

**Architecture:** 4 neue Backend-Endpoints unter `/api/admin/anmeldungen` (JWT-geschützt) + 1 neuer PATCH-Endpoint für Team-Zuweisung. Frontend: alte `discord-users`-Section wird durch `anmeldungen`-Section mit Tab-UI ersetzt – bestehende Discord-User-Tabelle und Registrierungsformular in neue Section migriert.

**Tech Stack:** FastAPI + SQLAlchemy (Backend), Vanilla JS/HTML (Frontend), SQLite

---

### Task 1: Backend – GET /api/admin/anmeldungen

**Files:**
- Modify: `backend/app/api.py` (am Ende, vor dem letzten Discord-Block, ca. Zeile 1173)

**Step 1: Endpoint hinzufügen**

Am Ende von `api.py`, nach dem `participation-report`-Endpoint (nach Zeile 1617), einfügen:

```python
# ADMIN ANMELDUNGEN ENDPOINTS

@router.get("/admin/anmeldungen")
def get_anmeldungen(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Admin-Endpoint: Alle Discord User mit Anmeldestatus.
    Gibt is_complete, has_profile, team_name zurück.
    Sortierung: incomplete zuerst, dann alphabetisch.
    """
    users = db.query(models.UserProfile).all()

    result = []
    for user in users:
        team_name = None
        if user.team_id:
            team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
            if team:
                team_name = team.name

        has_profile = bool(user.profile_url and user.profile_url.strip())
        is_complete = (
            has_profile
            and user.team_id is not None
            and user.participating_next is True
        )

        result.append({
            "discord_id": user.discord_id,
            "discord_username": user.discord_username,
            "team_id": user.team_id,
            "team_name": team_name,
            "profile_url": user.profile_url,
            "has_profile": has_profile,
            "participating_next": user.participating_next or False,
            "is_complete": is_complete,
        })

    # is_complete DESC, dann alphabetisch
    result.sort(key=lambda x: (not x["is_complete"], x["discord_username"].lower()))
    return result
```

**Step 2: Manuell testen**

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
# JWT holen:
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"biw2026!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
# Endpoint testen:
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/admin/anmeldungen | python3 -m json.tool | head -40
```

Erwartetes Ergebnis: JSON-Array (kann leer sein wenn keine User).

**Step 3: Commit**

```bash
git add backend/app/api.py
git commit -m "feat(backend): add GET /api/admin/anmeldungen endpoint"
```

---

### Task 2: Backend – POST & DELETE /api/admin/anmeldungen/{discord_id}/season

**Files:**
- Modify: `backend/app/api.py` (direkt nach Task 1 Endpoint)

**Step 1: POST-Endpoint hinzufügen**

```python
@router.post("/admin/anmeldungen/{discord_id}/season")
def add_to_season(
    discord_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Fügt User-Team zur aktiven Saison hinzu (kleinste Gruppe)."""
    # Aktive Saison laden
    season = db.query(models.Season).filter(models.Season.status == "active").first()
    if not season:
        raise HTTPException(status_code=404, detail="Keine aktive Saison gefunden")

    # User und team_id laden
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    if not user.team_id:
        raise HTTPException(status_code=400, detail="User hat kein Team zugewiesen")

    # Doppeleintrag prüfen
    existing = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season.id,
        models.SeasonTeam.team_id == user.team_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Team bereits in aktiver Saison")

    # Kleinste Gruppe finden
    groups = db.query(models.Group).filter(models.Group.season_id == season.id).all()
    if not groups:
        raise HTTPException(status_code=400, detail="Keine Gruppen in aktiver Saison")

    group_sizes = {}
    for g in groups:
        count = db.query(models.SeasonTeam).filter(
            models.SeasonTeam.group_id == g.id
        ).count()
        group_sizes[g.id] = count

    smallest_group_id = min(group_sizes, key=group_sizes.get)

    # SeasonTeam erstellen
    st = models.SeasonTeam(
        season_id=season.id,
        team_id=user.team_id,
        group_id=smallest_group_id
    )
    db.add(st)
    db.commit()
    db.refresh(st)

    return {"ok": True, "season_team_id": st.id}


@router.delete("/admin/anmeldungen/{discord_id}/season")
def remove_from_season(
    discord_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Entfernt User-Team aus der aktiven Saison."""
    season = db.query(models.Season).filter(models.Season.status == "active").first()
    if not season:
        raise HTTPException(status_code=404, detail="Keine aktive Saison gefunden")

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    if not user.team_id:
        raise HTTPException(status_code=400, detail="User hat kein Team")

    st = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season.id,
        models.SeasonTeam.team_id == user.team_id
    ).first()
    if not st:
        raise HTTPException(status_code=404, detail="Team nicht in aktiver Saison")

    db.delete(st)
    db.commit()
    return {"ok": True}
```

**Step 2: Testen**

```bash
# POST testen (erwartet 404 wenn User kein Team hat, oder 409 wenn schon dabei)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/admin/anmeldungen/DISCORD_ID_HERE/season
```

**Step 3: Commit**

```bash
git add backend/app/api.py
git commit -m "feat(backend): add POST/DELETE /api/admin/anmeldungen/{id}/season"
```

---

### Task 3: Backend – PATCH /api/discord/users/{discord_id}/team

**Files:**
- Modify: `backend/app/api.py` (im Discord-Block, nach dem bestehenden PATCH-Endpoint für `/discord/users/{discord_id}`)

**Step 1: Prüfen ob der Endpoint schon existiert**

```bash
grep -n "discord_id}/team" backend/app/api.py
```

Falls vorhanden: Task überspringen. Falls nicht:

**Step 2: Endpoint hinzufügen** (direkt nach dem `update_user_profile` Endpoint, ca. Zeile 1430):

```python
@router.patch("/discord/users/{discord_id}/team")
def assign_team_to_user(
    discord_id: str,
    update: dict,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Admin-Endpoint: Team einem Discord-User zuweisen.
    Body: {"team_id": 42}
    """
    team_id = update.get("team_id")

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    if team_id is not None:
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_id} nicht gefunden")

    user.team_id = team_id
    db.commit()
    db.refresh(user)

    return {
        "discord_id": user.discord_id,
        "discord_username": user.discord_username,
        "team_id": user.team_id,
        "profile_url": user.profile_url,
        "participating_next": user.participating_next,
    }
```

**Step 3: Testen**

```bash
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"team_id": 1}' \
  http://localhost:8000/api/discord/users/DISCORD_ID_HERE/team
```

**Step 4: Commit**

```bash
git add backend/app/api.py
git commit -m "feat(backend): add PATCH /api/discord/users/{id}/team endpoint"
```

---

### Task 4: Frontend – Sidebar umstrukturieren

**Files:**
- Modify: `frontend/admin.html` (Zeilen 123–131)

**Step 1: Sidebar-Nav ersetzen**

Alten Block (Zeile 123–131):
```html
        <a href="#dashboard" class="active" data-section="dashboard">📊 Dashboard</a>
        <a href="#matches" data-section="matches">🎮 Ergebnisse</a>
        <a href="#ko-phase" data-section="ko-phase">🏆 KO-Phase</a>
        <a href="#teams" data-section="teams">👥 Teams</a>
        <a href="#seasons" data-section="seasons">📅 Saisons</a>
        <a href="#discord-users" data-section="discord-users">👤 Discord User</a>
        <a href="#news" data-section="news">📰 News</a>
        <a href="#saison-setup" data-section="saison-setup" style="margin-top:.75rem;border-top:1px solid rgba(255,255,255,.1);padding-top:.75rem">🏆 Saison-Setup</a>
```

Neuen Block einsetzen:
```html
        <a href="#dashboard" class="active" data-section="dashboard">📊 Dashboard</a>
        <a href="#anmeldungen" data-section="anmeldungen">📋 Anmeldungen</a>
        <a href="#matches" data-section="matches">🎮 Ergebnisse</a>
        <a href="#ko-phase" data-section="ko-phase">🏆 KO-Phase</a>
        <a href="#teams" data-section="teams">👥 Teams</a>
        <a href="#seasons" data-section="seasons">📅 Saisons</a>
        <a href="#news" data-section="news">📰 News</a>
        <a href="#saison-setup" data-section="saison-setup" style="margin-top:.75rem;border-top:1px solid rgba(255,255,255,.1);padding-top:.75rem">🏆 Saison-Setup</a>
```

**Step 2: Commit**

```bash
git add frontend/admin.html
git commit -m "feat(frontend): reorder sidebar, add Anmeldungen link"
```

---

### Task 5: Frontend – Neue Anmeldungen-Section HTML

**Files:**
- Modify: `frontend/admin.html`

**Step 1: Alte discord-users Section suchen**

```bash
grep -n 'id="discord-users"' frontend/admin.html
```

**Step 2: Alte Section komplett ersetzen** durch neue Section.

Den gesamten Block `<div id="discord-users" class="section">...</div>` (inkl. schließendem `</div>`) ersetzen mit:

```html
      <!-- Anmeldungen -->
      <div id="anmeldungen" class="section">
        <h1>📋 Anmeldungen</h1>

        <!-- Statistik-Banner -->
        <div class="anmeldungen-stats">
          <div class="stat-badge stat-total">Gesamt: <span id="anm-stat-total">–</span></div>
          <div class="stat-badge stat-dabei">Dabei: <span id="anm-stat-dabei">–</span></div>
          <div class="stat-badge stat-incomplete">Unvollständig: <span id="anm-stat-incomplete">–</span></div>
        </div>

        <!-- Tab-Bar -->
        <div class="anm-tab-bar">
          <button class="anm-tab-btn active" data-tab="aktive-saison">🏆 Aktive Saison</button>
          <button class="anm-tab-btn" data-tab="alle-user">👤 Alle Discord User</button>
          <button class="anm-tab-btn" data-tab="registrieren">➕ Registrieren</button>
        </div>

        <!-- Tab: Aktive Saison -->
        <div id="anm-tab-aktive-saison" class="anm-tab-content">
          <div class="anm-filter-bar">
            <button class="anm-filter-btn active" data-filter="all">Alle</button>
            <button class="anm-filter-btn" data-filter="ready">✅ Ready</button>
            <button class="anm-filter-btn" data-filter="incomplete">⚠️ Unvollständig</button>
          </div>
          <div class="card" style="padding:0">
            <div style="overflow-x:auto">
              <table>
                <thead>
                  <tr>
                    <th>Discord</th>
                    <th>Team</th>
                    <th>Profil</th>
                    <th>Dabei</th>
                    <th>Status</th>
                    <th style="text-align:right">Aktionen</th>
                  </tr>
                </thead>
                <tbody id="anm-aktive-saison-tbody">
                  <tr><td colspan="6" style="text-align:center;color:var(--muted)">Lade...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Tab: Alle Discord User -->
        <div id="anm-tab-alle-user" class="anm-tab-content" style="display:none">
          <div class="card">
            <div class="form-row">
              <div class="form-group">
                <label>Suche nach Username</label>
                <input type="text" id="anm-user-search" placeholder="Username eingeben..." oninput="debounceAnmUserSearch()">
              </div>
              <div class="form-group" style="display:flex;align-items:flex-end">
                <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer;padding:.5rem 0">
                  <input type="checkbox" id="anm-filter-no-team" onchange="loadAlleDiscordUser()">
                  <span>Nur ohne Team</span>
                </label>
              </div>
              <div class="form-group" style="flex:0">
                <button class="btn btn-primary" onclick="loadAlleDiscordUser()">🔄 Neu laden</button>
              </div>
            </div>
          </div>
          <div class="card" style="padding:0">
            <div style="overflow-x:auto">
              <table>
                <thead>
                  <tr>
                    <th>Discord Username</th>
                    <th>Team</th>
                    <th>Profil URL</th>
                    <th>Teilnahme</th>
                    <th>Registriert</th>
                    <th style="text-align:right">Aktionen</th>
                  </tr>
                </thead>
                <tbody id="anm-alle-user-tbody">
                  <tr><td colspan="6" style="text-align:center;color:var(--muted)">Lade...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Tab: Registrieren -->
        <div id="anm-tab-registrieren" class="anm-tab-content" style="display:none">
          <div class="card">
            <h2>➕ User manuell registrieren</h2>
            <div class="form-row">
              <div class="form-group">
                <label>Discord ID</label>
                <input type="text" id="register-discord-id" placeholder="272170332125659137">
              </div>
              <div class="form-group">
                <label>Discord Username</label>
                <input type="text" id="register-username" placeholder="Julian">
              </div>
              <div class="form-group" style="display:flex;align-items:flex-end">
                <label style="display:flex;align-items:center;gap:.5rem;cursor:pointer;padding:.5rem 0">
                  <input type="checkbox" id="register-participating" checked>
                  <span>Teilnahme aktiv</span>
                </label>
              </div>
              <div class="form-group" style="flex:0;display:flex;align-items:flex-end">
                <button class="btn btn-primary" onclick="registerDiscordUser()">Registrieren</button>
              </div>
            </div>
            <div id="register-result" style="margin-top:1rem"></div>
          </div>
        </div>

        <!-- Team-Assign Modal -->
        <div id="team-assign-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1000;align-items:center;justify-content:center">
          <div class="card" style="width:400px;max-width:90vw">
            <h3>Team zuweisen</h3>
            <input type="hidden" id="team-assign-discord-id">
            <div class="form-group">
              <label>Team suchen</label>
              <input type="text" id="team-assign-search" placeholder="Teamname..." oninput="searchTeamsForAssign()">
            </div>
            <div id="team-assign-results" style="max-height:200px;overflow-y:auto;margin-top:.5rem"></div>
            <div style="display:flex;gap:.5rem;margin-top:1rem;justify-content:flex-end">
              <button class="btn" onclick="closeTeamAssignModal()">Abbrechen</button>
            </div>
          </div>
        </div>
      </div>
```

**Wichtig:** Prüfen ob `registerDiscordUser()` Funktion noch an alter Stelle referenziert wird – sie bleibt bestehen, wird nur aus der migrierten Section aufgerufen.

**Step 3: Commit**

```bash
git add frontend/admin.html
git commit -m "feat(frontend): add Anmeldungen section HTML, remove old discord-users section"
```

---

### Task 6: Frontend – CSS für neue Section

**Files:**
- Modify: `frontend/admin.html` (im `<style>`-Block am Anfang)

**Step 1: CSS am Ende des `<style>`-Blocks einfügen** (vor dem schließenden `</style>`):

```css
/* Anmeldungen Section */
.anmeldungen-stats { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
.stat-badge { padding:6px 14px; border-radius:20px; font-size:.9rem; font-weight:600; }
.stat-total { background:#2a2a3d; color:#aaa; }
.stat-dabei { background:#1a3a1a; color:#4caf50; }
.stat-incomplete { background:#3a2a1a; color:#ff9800; }

.anm-tab-bar { display:flex; gap:4px; margin-bottom:16px; border-bottom:1px solid var(--border,#e5e7eb); padding-bottom:4px; }
.anm-tab-btn { padding:7px 16px; border-radius:6px 6px 0 0; border:1px solid transparent; background:transparent; color:var(--muted,#6b7280); cursor:pointer; font-size:.9rem; }
.anm-tab-btn.active { background:var(--primary,#3b82f6); color:#fff; border-color:var(--primary,#3b82f6); }
.anm-tab-btn:hover:not(.active) { background:rgba(0,0,0,.05); }

.anm-filter-bar { display:flex; gap:8px; margin-bottom:12px; }
.anm-filter-btn { padding:5px 12px; border-radius:4px; border:1px solid #d1d5db; background:#fff; color:#6b7280; cursor:pointer; font-size:.85rem; }
.anm-filter-btn.active { background:var(--primary,#3b82f6); color:#fff; border-color:var(--primary,#3b82f6); }

.badge-ready { color:#4caf50; font-weight:600; }
.badge-warn  { color:#ff9800; font-weight:600; }
.badge-inactive { color:#9ca3af; font-weight:600; }
.missing     { color:#9ca3af; font-style:italic; }

tr.row-incomplete td:first-child { border-left:3px solid #ff9800; }
tr.row-complete td:first-child   { border-left:3px solid #4caf50; }
tr.row-inactive td:first-child   { border-left:3px solid #d1d5db; }

.toggle-participation-btn { padding:3px 8px; border-radius:4px; border:none; cursor:pointer; background:#f3f4f6; color:#374151; font-size:.85rem; }
.toggle-participation-btn.is-dabei { background:#dcfce7; color:#166534; }
```

**Step 2: Commit**

```bash
git add frontend/admin.html
git commit -m "feat(frontend): add CSS for Anmeldungen section"
```

---

### Task 7: Frontend – JavaScript loadAnmeldungen()

**Files:**
- Modify: `frontend/admin.html` (JS-Block, nach den vorhandenen Funktionen)

**Step 1: Tab-Switch und Statistik-Logik hinzufügen**

Im `<script>`-Block, neue Funktion `loadAnmeldungen()` und Hilfsfunktionen:

```javascript
// ===== ANMELDUNGEN SECTION =====

let anmeldungenData = [];

async function loadAnmeldungen() {
  try {
    anmeldungenData = await fetchAPI('/admin/anmeldungen');
  } catch(e) {
    console.error('Fehler beim Laden der Anmeldungen:', e);
    anmeldungenData = [];
  }

  // Statistiken
  const total = anmeldungenData.length;
  const dabei = anmeldungenData.filter(u => u.participating_next).length;
  const incomplete = anmeldungenData.filter(u => u.participating_next && !u.is_complete).length;
  document.getElementById('anm-stat-total').textContent = total;
  document.getElementById('anm-stat-dabei').textContent = dabei;
  document.getElementById('anm-stat-incomplete').textContent = incomplete;

  // Aktive-Saison-Tab rendern
  renderAnmeldungenTable(anmeldungenData.filter(u => u.participating_next));
}

function renderAnmeldungenTable(users) {
  const tbody = document.getElementById('anm-aktive-saison-tbody');
  if (!users.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted)">Keine Einträge</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  users.forEach(user => {
    const rowClass = user.is_complete ? 'row-complete' : 'row-incomplete';
    const statusBadge = user.is_complete
      ? '<span class="badge-ready">✅ Ready</span>'
      : '<span class="badge-warn">⚠️ Unvollständig</span>';

    const tr = document.createElement('tr');
    tr.className = rowClass;
    tr.dataset.complete = user.is_complete ? '1' : '0';
    tr.innerHTML = `
      <td><strong>${escapeHtml(user.discord_username)}</strong></td>
      <td>${user.team_name ? escapeHtml(user.team_name) : '<span class="missing">—</span>'}</td>
      <td>${user.has_profile ? '✅' : '❌'}</td>
      <td>
        <button class="toggle-participation-btn is-dabei" onclick="toggleDabei('${user.discord_id}', false)">
          ✅ Ja
        </button>
      </td>
      <td>${statusBadge}</td>
      <td style="text-align:right">
        <button class="btn btn-sm" onclick="openTeamAssignModal('${user.discord_id}')" title="Team zuweisen" style="margin-right:4px">🔗 Team</button>
        <button class="btn btn-sm btn-danger" onclick="removeFromSeason('${user.discord_id}', '${escapeHtml(user.discord_username)}')" title="Aus Saison entfernen">✕</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Filter neu anwenden
  applyAnmFilter();
}

function applyAnmFilter() {
  const activeBtn = document.querySelector('.anm-filter-btn.active');
  const filter = activeBtn ? activeBtn.dataset.filter : 'all';
  document.querySelectorAll('#anm-aktive-saison-tbody tr').forEach(tr => {
    if (filter === 'all') {
      tr.style.display = '';
    } else if (filter === 'ready') {
      tr.style.display = tr.dataset.complete === '1' ? '' : 'none';
    } else if (filter === 'incomplete') {
      tr.style.display = tr.dataset.complete === '0' ? '' : 'none';
    }
  });
}

async function toggleDabei(discordId, newStatus) {
  try {
    await fetchAPI(`/discord/users/${discordId}/participation`, {
      method: 'PATCH',
      body: JSON.stringify({ participating: newStatus })
    });
    loadAnmeldungen();
  } catch(e) {
    alert('Fehler: ' + (e.message || e));
  }
}

async function removeFromSeason(discordId, username) {
  if (!confirm(`${username} wirklich aus der aktiven Saison entfernen?`)) return;
  try {
    await fetchAPI(`/admin/anmeldungen/${discordId}/season`, { method: 'DELETE' });
    loadAnmeldungen();
  } catch(e) {
    alert('Fehler: ' + (e.message || e));
  }
}

function openTeamAssignModal(discordId) {
  document.getElementById('team-assign-discord-id').value = discordId;
  document.getElementById('team-assign-search').value = '';
  document.getElementById('team-assign-results').innerHTML = '';
  const modal = document.getElementById('team-assign-modal');
  modal.style.display = 'flex';
}

function closeTeamAssignModal() {
  document.getElementById('team-assign-modal').style.display = 'none';
}

async function searchTeamsForAssign() {
  const q = document.getElementById('team-assign-search').value.trim();
  if (q.length < 2) {
    document.getElementById('team-assign-results').innerHTML = '';
    return;
  }
  try {
    const teams = await fetchAPI(`/teams/search?name=${encodeURIComponent(q)}`);
    const results = document.getElementById('team-assign-results');
    results.innerHTML = '';
    teams.forEach(t => {
      const btn = document.createElement('div');
      btn.style.cssText = 'padding:8px;cursor:pointer;border-bottom:1px solid #e5e7eb;hover:background:#f3f4f6';
      btn.textContent = t.name;
      btn.onclick = () => assignTeam(t.id, t.name);
      results.appendChild(btn);
    });
    if (!teams.length) results.innerHTML = '<div style="padding:8px;color:#9ca3af">Keine Teams gefunden</div>';
  } catch(e) {
    console.error(e);
  }
}

async function assignTeam(teamId, teamName) {
  const discordId = document.getElementById('team-assign-discord-id').value;
  try {
    await fetchAPI(`/discord/users/${discordId}/team`, {
      method: 'PATCH',
      body: JSON.stringify({ team_id: teamId })
    });
    closeTeamAssignModal();
    loadAnmeldungen();
  } catch(e) {
    alert('Fehler: ' + (e.message || e));
  }
}

// Hilfsfunktion (nur hinzufügen falls noch nicht vorhanden)
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Tab-Events für Anmeldungen
document.addEventListener('DOMContentLoaded', () => {
  // Tab-Buttons
  document.querySelectorAll('.anm-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.anm-tab-content').forEach(c => c.style.display = 'none');
      document.getElementById(`anm-tab-${btn.dataset.tab}`).style.display = '';
      document.querySelectorAll('.anm-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (btn.dataset.tab === 'alle-user') loadAlleDiscordUser();
    });
  });

  // Filter-Buttons
  document.querySelectorAll('.anm-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.anm-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyAnmFilter();
    });
  });

  // Modal schließen bei Klick außen
  document.getElementById('team-assign-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeTeamAssignModal();
  });
});

// Alle Discord User Tab
async function loadAlleDiscordUser() {
  const search = document.getElementById('anm-user-search')?.value || '';
  const noTeam = document.getElementById('anm-filter-no-team')?.checked || false;

  let url = '/discord/users';
  const params = [];
  if (search) params.push(`search=${encodeURIComponent(search)}`);
  if (noTeam) params.push('has_team=false');
  if (params.length) url += '?' + params.join('&');

  const users = await fetchAPI(url);
  const tbody = document.getElementById('anm-alle-user-tbody');
  tbody.innerHTML = '';

  if (!users.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted)">Keine User</td></tr>';
    return;
  }

  users.forEach(user => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(user.discord_username)}</td>
      <td>${user.team_name ? escapeHtml(user.team_name) : '<span class="missing">—</span>'}</td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${user.profile_url ? `<a href="${user.profile_url}" target="_blank" style="color:var(--primary)">${escapeHtml(user.profile_url)}</a>` : '<span class="missing">—</span>'}</td>
      <td>${user.participating_next ? '✅' : '❌'}</td>
      <td style="color:var(--muted);font-size:.85rem">${user.created_at ? new Date(user.created_at).toLocaleDateString('de-DE') : '—'}</td>
      <td style="text-align:right">
        <button class="btn btn-sm" onclick="openTeamAssignModal('${user.discord_id}')" title="Team zuweisen" style="margin-right:4px">🔗 Team</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

let anmUserSearchTimeout;
function debounceAnmUserSearch() {
  clearTimeout(anmUserSearchTimeout);
  anmUserSearchTimeout = setTimeout(loadAlleDiscordUser, 300);
}
```

**Step 2: Commit**

```bash
git add frontend/admin.html
git commit -m "feat(frontend): add Anmeldungen JS logic (tabs, filters, team assign modal)"
```

---

### Task 8: Frontend – Navigation verknüpfen

**Files:**
- Modify: `frontend/admin.html` (im Navigation-Switch, ca. Zeile 748)

**Step 1: Den bestehenden `data-section`-Switch suchen**

```bash
grep -n "discord-users\|loadDiscordUsers\|data-section" frontend/admin.html | head -20
```

**Step 2: Im Switch-Block `discord-users` durch `anmeldungen` ersetzen**

Stelle finden (ca. Zeile 748):
```javascript
  if (name === 'discord-users') loadDiscordUsers();
```

Ersetzen durch:
```javascript
  if (name === 'anmeldungen') loadAnmeldungen();
```

**Step 3: Commit**

```bash
git add frontend/admin.html
git commit -m "feat(frontend): wire Anmeldungen section to navigation"
```

---

### Task 9: Cleanup – alte loadDiscordUsers()-Funktion entfernen / deaktivieren

**Files:**
- Modify: `frontend/admin.html`

**Step 1: Prüfen ob loadDiscordUsers() noch an anderer Stelle aufgerufen wird**

```bash
grep -n "loadDiscordUsers\|discord-users-list" frontend/admin.html
```

Falls nur noch in der alten Funktion selbst: komplette `loadDiscordUsers()`-Funktion und zugehörige `debounceUserSearch()`-Funktion entfernen.

Falls noch anderweitig referenziert: stattdessen `loadDiscordUsers` als Alias auf `loadAlleDiscordUser` umleiten:
```javascript
function loadDiscordUsers() { loadAlleDiscordUser(); }
```

**Step 2: Commit**

```bash
git add frontend/admin.html
git commit -m "chore(frontend): remove legacy loadDiscordUsers function"
```

---

### Task 10: Vollständiger Funktionstest

**Checklist:**
- [ ] Backend läuft: `uvicorn app.main:app --reload --port 8000`
- [ ] Frontend läuft: `python -m http.server 5500` im `frontend/`-Ordner
- [ ] Login funktioniert
- [ ] Sidebar zeigt "Anmeldungen" an Position 2
- [ ] Klick auf Anmeldungen: Section öffnet, Statistiken laden
- [ ] Tab "Aktive Saison": Tabelle zeigt participating_next-User
- [ ] Filter "⚠️ Unvollständig" filtert korrekt
- [ ] Button "✕" öffnet Confirm → API-Call → Tabelle aktualisiert
- [ ] "🔗 Team" öffnet Modal → Suche → Auswahl setzt team_id
- [ ] Tab "Alle Discord User": Tabelle lädt per AJAX
- [ ] Suche im "Alle User"-Tab filtert
- [ ] Tab "Registrieren": Formular funktioniert (registerDiscordUser() unverändert)
- [ ] Keine JS-Errors in der Browser-Konsole

**Step 1: Backend-Neustart und testen**

```bash
pkill -f uvicorn; cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

Öffne Browser: `http://localhost:5500/admin.html`

**Step 2: Abschließender Commit falls nötig**

```bash
git add -p  # nur geänderte Dateien
git commit -m "fix(frontend): anmeldungen section final adjustments"
```
