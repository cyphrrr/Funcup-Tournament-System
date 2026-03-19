# Bereich C: `<fts-layout>` Web Component — Design Spec

## Goal

Eliminate ~540 lines of duplicated HTML/JS boilerplate across 10 public pages by extracting Header, Nav, Footer, and shared initialization into a single Web Component `<fts-layout>`.

## Architecture

A single file `js/fts-layout.js` defines a Custom Element `<fts-layout>` using Light DOM (no Shadow DOM). Each page imports it and wraps its content. The component renders the complete page structure and initializes all shared UI functions.

**No build step.** No framework. Browser-native Custom Elements API.

## Component API

### Usage

```html
<head>
  <script src="js/themes.js"></script>
  <script type="module" src="js/background.js"></script>
  <script type="module" src="js/fts-layout.js"></script>
</head>
<body>
  <fts-layout page-title="/ Archiv">
    <section>
      <!-- Page-specific content only -->
    </section>
  </fts-layout>
</body>
```

### Attributes

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `page-title` | Yes | Subtitle shown in header after "BIW Pokal" | `/ Archiv`, `/ Start` |

`page-title` is read once in `connectedCallback()` and is not observed (no `attributeChangedCallback`). If omitted, the subtitle area renders empty (no error).

## What the Component Renders

The component uses **DOM manipulation, not `<slot>`** (slots are a Shadow DOM concept). In `connectedCallback()`:

1. Collect all existing children of `<fts-layout>`
2. Create header, menu-overlay, nav, `<main>`, footer elements
3. Move collected children into `<main>`
4. Append all elements in order: header, overlay, nav, main, footer
5. Guard against double-init (if `connectedCallback` fires again, skip)

**Rendered structure:**

```
<fts-layout page-title="/ Archiv">
  <header>
    Logo + "BIW Pokal" + page-title + Dark-Mode-Toggle + Burger-Button
  </header>
  <div class="menu-overlay" id="menu-overlay"></div>
  <nav id="nav-menu">
    <ul>
      Start | Regeln | Mein Profil | Gruppenphase | KO-Phase | Ewige Tabelle | Archiv | Admin (hidden)
    </ul>
  </nav>
  <main>
    <!-- Original children moved here -->
  </main>
  <footer>
    Backend-Status | Copyright + Impressum + Datenschutz | Version + Theme-Selector
  </footer>
</fts-layout>
```

### Active Nav Link

Automatically determined by comparing `window.location.pathname` against nav link `href` values:

```javascript
const currentPath = window.location.pathname.split('/').pop() || 'index.html';
this.querySelectorAll('nav a').forEach(link => {
  if (link.getAttribute('href') === currentPath) link.classList.add('active');
});
```

No manual `class="active"` needed per page.

## Light DOM — No Shadow DOM

The component uses Light DOM so that:
- `shared.css` and CSS variables (`--primary`, `--card`, etc.) apply directly
- Page-specific `<style>` blocks can target elements inside the component (e.g. `team.html` overrides `header` styles)
- No style encapsulation issues
- Existing JS (themes.js, tracking.js, version.js) works unchanged

## Script Loading Order & themes.js

**Critical timing detail:** `themes.js` is loaded as a synchronous (non-module) script in `<head>`. It registers a `DOMContentLoaded` listener via:

```javascript
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initThemeSystem);
} else {
  initThemeSystem();
}
```

The execution order is:
1. `themes.js` loads synchronously in `<head>` → registers DOMContentLoaded listener
2. `fts-layout.js` loads as module (deferred)
3. HTML parsing completes
4. **Module scripts execute** → `customElements.define()` → `connectedCallback()` fires → DOM rendered (toggle, dropdown exist)
5. **DOMContentLoaded fires** → `initThemeSystem()` runs → finds `#dark-mode-toggle` and `#theme-select` ✓

This works because module scripts execute after HTML parsing but **before** DOMContentLoaded. CSS variables are applied to `document.documentElement` immediately (no flash), theme controls are initialized after the component renders.

**`themes.js` stays unchanged.** No refactoring needed.

## What the Component Initializes

On `connectedCallback()`:
1. Renders Header + Nav + Footer HTML via DOM manipulation
2. Moves existing children into `<main>` wrapper
3. Sets active nav link based on URL
4. Imports and calls from `shared-ui.js`: `initBurgerMenu()`, `initAdminLink()`, `initBackendStatus()`
5. Loads version display (`js/version.js` functionality)
6. Loads page tracking (`js/tracking.js` functionality)

**`initBackendStatus()` is called exclusively by the component.** Pages must NOT call it themselves after migration. Pages that need to signal backend status from their data fetches only import and call `setBackendStatus(true/false)`.

## Scripts managed by pages (not the component)

- **`themes.js`** — stays in `<head>` as synchronous script (timing-critical for theme flash prevention)
- **`background.js`** — stays in `<head>` as module script (loads custom background image, independent of layout)

## Impact on Existing Files

### Per page — removed boilerplate:
- Header HTML (~20 lines)
- Nav HTML (~15 lines)
- Menu overlay div
- Footer HTML (~16 lines)
- `initBurgerMenu()`, `initAdminLink()` imports and calls
- `initBackendStatus()` imports and calls (component handles this now)
- Footer `<script type="module">` block for `initBackendStatus()`
- `<script src="js/version.js">` and `<script src="js/tracking.js">` tags

### Per page — what remains:
- `<head>` with page title, meta, `themes.js`, `background.js`, `fts-layout.js`, page-specific `<style>`
- `<fts-layout page-title="/ ...">` wrapper
- Page-specific content (sections, cards, etc.)
- Page-specific `<script type="module">` with data loading logic
- `setBackendStatus()` import (only on pages that do data fetches)

### shared-ui.js
- Stays as-is. `fts-layout.js` imports from it.
- Pages still import `setBackendStatus` directly where needed.

### New file
- `js/fts-layout.js` — Custom Element definition (~80-100 lines)

## Affected Pages (10 total)

| Page | page-title |
|------|-----------|
| `index.html` | `/ Start` |
| `turnier.html` | `/ Turnier` |
| `ko.html` | `/ KO-Phase` |
| `archiv.html` | `/ Archiv` |
| `ewige-tabelle.html` | `/ Ewige Tabelle` |
| `dashboard.html` | `/ Mein Profil` |
| `team.html` | `/ Team` |
| `regeln.html` | `/ Regeln` |
| `datenschutz.html` | `/ Datenschutz` |
| `impressum.html` | `/ Impressum` |

admin.html is excluded (own UI system).

## Edge Cases

### Pages with `setBackendStatus()` calls
Pages like index.html, turnier.html etc. still import `setBackendStatus` from `shared-ui.js` in their own script blocks. The component handles `initBackendStatus()` (30s polling), pages only signal success/failure from their data fetches.

### Dashboard page
Currently calls `initBackendStatus()` in its own script. After migration, the component handles the interval. Dashboard only calls `setBackendStatus()` from its init function.

### index.html hero-bar
`index.html` has a `<div class="hero-bar">` that currently sits between `</nav>` and `<main>`. After migration, it becomes part of the children moved into `<main>`. This is fine — the hero-bar uses class-based styling with no positional CSS selectors (`body > .hero-bar` etc.), so moving it inside `<main>` has no visual effect.

### Page-specific header style overrides
`team.html` overrides header styles in its `<style>` block (`header{background:var(--card);...}`). This works with Light DOM because page-specific styles apply directly to the component's rendered elements.

### Double connectedCallback guard
If the element is moved in the DOM, `connectedCallback` fires again. The component checks an `_initialized` flag and skips rendering if already initialized.

## Not In Scope

- admin.html (separate UI system, stays as-is)
- Shadow DOM / style encapsulation
- Build steps or SSR
- Refactoring page-specific JS logic
- `<head>` boilerplate deduplication (favicon, viewport, fonts) — a Web Component cannot control `<head>`, this remains manual
