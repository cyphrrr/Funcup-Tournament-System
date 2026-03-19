# Bereich C: `<fts-layout>` Web Component — Design Spec

## Goal

Eliminate ~540 lines of duplicated HTML/JS boilerplate across 9 public pages by extracting Header, Nav, Footer, and shared initialization into a single Web Component `<fts-layout>`.

## Architecture

A single file `js/fts-layout.js` defines a Custom Element `<fts-layout>` using Light DOM (no Shadow DOM). Each page imports it and wraps its content. The component renders the complete page structure and initializes all shared UI functions.

**No build step.** No framework. Browser-native Custom Elements API.

## Component API

### Usage

```html
<head>
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

## What the Component Renders

```
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
  <slot></slot>  <!-- Page content goes here via Light DOM -->
</main>
<footer>
  Backend-Status | Copyright + Impressum + Datenschutz | Version + Theme-Selector
</footer>
```

### Active Nav Link

Automatically determined by comparing `window.location.pathname` against nav link `href` values:

```javascript
const currentPath = window.location.pathname.split('/').pop() || 'index.html';
// Match against each <a href="..."> in nav
```

No manual `class="active"` needed per page.

## Light DOM — No Shadow DOM

The component uses Light DOM so that:
- `shared.css` and CSS variables (`--primary`, `--card`, etc.) apply directly
- Seitenspezifische `<style>` blocks can target elements inside the component
- No style encapsulation issues
- Existing JS (themes.js, tracking.js, version.js) works unchanged

Implementation: The component moves its children into a `<main>` wrapper and prepends/appends header/nav/footer around it using `connectedCallback()`.

## What the Component Initializes

On `connectedCallback()`:
1. Renders Header + Nav + Footer HTML
2. Moves existing children into `<main>` slot area
3. Imports and calls from `shared-ui.js`: `initBurgerMenu()`, `initAdminLink()`, `initBackendStatus()`
4. Loads `js/version.js` functionality (footer version display)
5. Loads `js/tracking.js` functionality (page view tracking)

## Impact on Existing Files

### Per page — removed boilerplate:
- Header HTML (~20 lines)
- Nav HTML (~15 lines)
- Menu overlay div
- Footer HTML (~16 lines)
- `import { initBurgerMenu, initAdminLink, ... } from './js/shared-ui.js'` and their calls
- Footer `<script type="module">` block for `initBackendStatus()`
- `<script src="js/version.js">` and `<script src="js/tracking.js">` tags

### Per page — what remains:
- `<head>` with page title, meta tags, seitenspezifische `<style>`
- `<fts-layout page-title="/ ...">` wrapper
- Page-specific content (sections, cards, etc.)
- Page-specific `<script type="module">` with data loading logic

### shared-ui.js
- Stays as-is. `fts-layout.js` imports from it.
- Pages that use `setBackendStatus()` still import it directly in their own script blocks.

### New file
- `js/fts-layout.js` — Custom Element definition (~80-100 lines)

## Affected Pages (9 total)

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

Note: That's 10 pages. admin.html is excluded (own UI system).

## Edge Cases

### Pages with `setBackendStatus()` calls
Pages like index.html, turnier.html etc. still need to import `setBackendStatus` from `shared-ui.js` in their own script blocks. The component handles `initBackendStatus()` (30s polling), but pages signal success/failure from their own data fetches.

### Dashboard page
Has its own `initBackendStatus()` call pattern. After migration, the component handles the interval, dashboard just calls `setBackendStatus()` from its init function.

### Scripts loading order
`fts-layout.js` is loaded as `type="module"` in `<head>`. The component's `connectedCallback` fires when the browser parses `<fts-layout>` in the body. Page-specific scripts run after, so all IDs (backend-status-dot, etc.) are already in the DOM.

## Not In Scope

- admin.html (separate UI system, stays as-is)
- Shadow DOM / style encapsulation
- Build steps or SSR
- Refactoring page-specific JS logic
