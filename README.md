# BIW Pokal

Offenes, automatisierbares Turnier‑System für Pokal‑ und Ligawettbewerbe.

Dieses Projekt ist aus einem realen, über mehrere Saisons gewachsenen Setup entstanden und ersetzt **WordPress + SportPress** durch ein **klares, nachvollziehbares System**.

---

## 🎯 Ziel

- Verwaltung von Pokal‑Saisons (Gruppenphase + KO‑Phase)
- Vollautomatisierter Ergebnis‑Import
- Spieltags‑Posts + Discord‑Benachrichtigungen
- Offene Datenformate (CSV / XLSX / JSON)
- **Keine Paywalls, keine Plugins, kein CMS**

---

## 🧱 Architektur (Kurzfassung)

```
onlineliga.de
     ↓
    n8n        ← Orchestrierung & Automatisierung
     ↓ (API)
  Backend      ← Logik & Daten
     ↓
  Frontend     ← Read‑only Webapp
```

Details siehe:
- `docs/LOGIC.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`

---

## 📁 Projektstruktur

```
biw-pokal/
├─ backend/          # API (noch leer – Skeleton folgt)
├─ frontend/         # Webapp (read‑only)
├─ n8n-flows/        # Exportierte n8n‑Workflows
├─ docs/             # Fachliche & technische Dokumentation
│  ├─ LOGIC.md
│  ├─ ARCHITECTURE.md
│  └─ DATA_MODEL.md
└─ README.md
```

---

## 🔁 Automatisierung (n8n)

n8n übernimmt:
- Import von Ergebnissen (z. B. onlineliga.de)
- Normalisierung & Validierung
- Matchday‑Abschluss
- Auto‑Exports
- Discord‑Webhooks

Die Flows liegen unter `n8n-flows/` und sind **versionierbar**.

---

## 🗂️ Saisons

- Jede Saison ist **vollständig isoliert**
- Historische Saisons sind **read‑only**
- Neue Saisons werden nativ angelegt

---

## 🚀 Status

🟡 Architektur & Datenmodell definiert  
🟡 Implementierung startet

---

## 📜 Lizenz

Geplant: MIT License (offen & frei nutzbar)

---

> Dieses Projekt ist bewusst **klein, offen und ehrlich** gehalten.
> Es soll verstanden, erweitert und geteilt werden können.
