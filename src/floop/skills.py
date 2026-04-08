"""Built-in floop skill templates.

Each skill is a dict with 'name', 'description', and 'content' (Markdown body).
The enable command adapts these to each agent platform's format.
"""

# ---------------------------------------------------------------------------
# Instruction — always-on context telling Agent that floop exists
# ---------------------------------------------------------------------------

INSTRUCTION = """\
This project uses **floop** — an AI-native prototype quality toolkit.

A `.floop/` directory exists with design tokens and prototype files.
When doing any design or prototype work, follow the floop workflow.

## Available Commands

- `floop token init` — Generate W3C DTCG token template files
- `floop token validate` — Validate token files (format + references + suggestions)
- `floop token view` — Generate HTML preview page **and `tokens.css`** for design tokens
- `floop preview` — Start a local web server to preview tokens and prototypes
- `floop init` — Initialize a floop project (creates `.floop/`)
- `floop enable <agent>` — Install floop skills
- `floop prd init` / `floop prd validate` — Create and validate `.floop/prd.md` (PRD)
- `floop sitemap init` / `floop sitemap validate` — Create and validate `.floop/sitemap.md`
- `floop prototype init` — Generate `.floop/journey-map.csv` (sitemap domain → HTML mapping) from sitemap.md
- `floop prototype validate` — Validate: every journey HTML is mapped in CSV; every CSV domain exists in sitemap
- `floop journey check <file>` — Backward-check a journey HTML for missing tokens, unused components, raw tag misuse, and missing head links
- `floop component init` / `floop component validate` / `floop component view` — Manage `.floop/components.yaml`

## Workflow

Everything is iterative — tokens, sitemap, components, and pages all grow together:

```
┌── Iteration Loop ──────────────────────────────────────────────────┐
│  Sketch    → understand current idea / change                      │
│  Token     → extend tokens if new values are needed               │
│  Sitemap   → capture or update .floop/sitemap.md                  │
│  Component → identify / update .floop/components.yaml             │
│  Build     → generate page to .floop/build/journey/<name>.html            │
│  Confirm   → show user → next iteration, adjustments, or deliver  │
└────────────────────────────────────────────────────────────────────┘
```

**Tokens are NOT one-time setup. They grow as you discover new design needs.**
**Sitemap, components, and pages accumulate — never forced upfront, never "finished".**

## Key Rules

- All colors/spacing/fonts use CSS custom properties mapped from `.floop/tokens/*.tokens.json`
- Never hardcode design values — always reference tokens
- Token files follow W3C DTCG format (Design Tokens Format Module)
- **`floop token view` outputs TWO files: `design-tokens.html` (preview) and `tokens.css` (CSS variables for use in HTML pages)**
- **Every HTML page MUST link to `.floop/build/tokens/tokens.css` — do NOT re-declare `:root` variables manually**
- **MUST run `floop token validate` after every token edit** — fix all errors before proceeding
- **MUST run `floop component validate` after every component edit** — warns if token paths are broken
- **NEVER generate page HTML without first running both `floop token validate` AND `floop component validate`**
- **NEVER generate page HTML without confirming all required components exist in `components.yaml`**
- **NEVER write a journey HTML without `<link rel="stylesheet" href="../tokens/tokens.css">` AND `<script src="../components/components.js" defer></script>` in `<head>`**
- **NEVER embed a phone/device shell INSIDE the journey HTML file itself** — the floop preview renders device frames (phone/tablet/desktop) as a wrapper around the iframe; the HTML page must be plain responsive web layout, not a div styled as a device mockup
- **NEVER add explanatory text, annotations, or section labels to journey HTML — only real UI content a user would see in production**
- **NEVER consider a journey HTML file "done" without running `floop journey check <file>` — fix all errors before showing to user**
"""

SKILLS = {
    "prototype": {
        "name": "floop-prototype",
        "description": (
            "Complete iterative workflow for building HTML prototypes with floop. "
            "Covers the full loop: Token → Sitemap → Components → Build → Confirm → Deliver. "
            "Tokens, sitemap, and components ALL grow across iterations — nothing is one-time. "
            "Use when: user has any prototype, design, or UI request."
        ),
        "content": """\
# floop — Prototype Skill

**Everything in floop is iterative. There is no fixed sequence, no waterfall, no "done" phase.**
The loop runs as many times as needed. The user can enter or re-enter at any step.

## Workflow

```
┌── Iteration Loop ──────────────────────────────────────────────────────────┐
│                                                                            │
│  A  Sketch     → understand the request / what to build this round        │
│  B  Token      → check tokens are sufficient; extend if needed             │
│  C  Sitemap    → capture or update .floop/sitemap.md                      │
│  C2 Journey Map → run floop prototype init to rebuild journey-map.csv      │
│  D  Component  → identify needed components; update .floop/components.yaml │
│  E  Build      → generate page HTML to .floop/build/journey/<name>.html   │
│  E2 Validate   → run floop prototype validate after every new HTML         │
│  E3 Check      → run floop journey check <file> for backward gap analysis  │
│  F  Confirm    → show user → continue, refine, or deliver                 │
│                                                                            │
│  ↺  Any step can loop back to any earlier step                            │
└────────────────────────────────────────────────────────────────────────────┘
    ↓ when user is satisfied
Deliver → run floop preview → push for review
```

**Key principles:**
- First iteration: start with just enough — one sketch, one token pass, one page
- Tokens are NOT one-time setup — they grow as new components reveal new design needs
- Sitemap is a living document — add pages as understanding grows
- Components accumulate — always reuse before adding new ones
- The user may jump to any step at any time

---

## Step A — Sketch (理解当前想法)

At the start of each iteration, understand what to build:
- **First time**: "What is this product? Who uses it? What's the core flow?"
- **Returning**: "Which page or flow should we tackle next? Or refine an existing one?"
- **Stuck**: "What's the one thing a user needs to DO in this product?" → start there

**Optional PRD** — On the first iteration, capture product definition in `.floop/prd.md`:
```bash
floop prd init      # create template
floop prd validate  # check schema
```

PRD frontmatter schema:
```yaml
---
version: 1
updated_at: 2024-01-15
product: "My App"
target_users:
  - primary user type
core_flows:
  - main flow
css_framework: tailwind
status: draft   # draft | confirmed
---
```

---

## Step B — Token (确认 / 扩展 Design Token)

**Tokens are the visual source of truth. Read them before building anything.**
**They are extended throughout the project life — not just at the start.**

### First iteration — establish baseline:
1. Ask user: brand guidelines? reference URL? or describe the vibe?
2. Run `floop token init` to generate W3C DTCG template files
3. Fill in `global.tokens.json` with primitive values, `semantic.tokens.json` with aliases
4. Validate and preview:
   ```bash
   floop token validate
   floop token view
   ```
   `floop token view` generates **two files** in `.floop/build/tokens/`:
   - `design-tokens.html` — visual preview
   - `tokens.css` — CSS custom properties (use this file in every HTML page)

### Every iteration — check before building:
1. Read `.floop/tokens/*.tokens.json` to refresh current token values
2. If the current iteration needs a design value that isn't in any token file:
   - Add it to the appropriate token file (`component.tokens.json` for component-level values)
   - Run `floop token validate` — fix all errors
   - Run `floop token view` — refresh `.floop/build/tokens/design-tokens.html` and `.floop/build/tokens/tokens.css`
3. Only proceed to Step C once tokens are valid

**MUST run `floop token validate` → `floop token view` after every token edit. Both commands required. Fix all errors before continuing.**

### Token Files (W3C DTCG format — three files in `.floop/tokens/`):

`global.tokens.json` — primitive values:
```json
{
  "color": {
    "blue-500": { "$type": "color", "$value": "#2563EB" }
  },
  "fontFamily": {
    "sans": { "$type": "fontFamily", "$value": "Inter, system-ui, sans-serif" }
  }
}
```

`semantic.tokens.json` — semantic aliases using `{path}` references:
```json
{
  "color": {
    "primary": { "$type": "color", "$value": "{color.blue-500}" },
    "background": { "$type": "color", "$value": "{color.white}" }
  }
}
```

`component.tokens.json` — component-level values:
```json
{
  "button": {
    "primary-background": { "$type": "color", "$value": "{color.primary}" },
    "radius": { "$type": "dimension", "$value": "{radius.md}" }
  }
}
```

### Token → CSS (from `tokens.css`):
`floop token view` generates `.floop/build/tokens/tokens.css` with all resolved CSS custom properties.
**Always reference `tokens.css` in HTML — never re-declare `:root` manually.**

Token path `color.blue-500` becomes `--color-blue-500: #2563EB;` in the CSS file.
Use variables in components like:
```css
.btn-primary { background: var(--color-primary); color: var(--color-on-primary); }
```

---

## Step C — Sitemap (记录结构)

**Output**: `.floop/sitemap.md` (YAML frontmatter + Markdown body)

```bash
floop sitemap init      # first time only
floop sitemap validate  # after every edit
```

Frontmatter schema:
```yaml
---
version: 1
updated_at: 2024-01-15
pages:
  - id: home
    title: 首页
    file: build/home.html       # path relative to .floop/
    status: planned             # planned | building | built
  - id: pricing
    title: 定价
    file: build/pricing.html
    status: planned
---

## Home
- **Hero**: tagline + CTA
- **Features**: 3-column grid

## Pricing ← (next iteration)
```

Status lifecycle: `planned` → `building` → `built` (file must exist on disk when `built`)

**MUST run `floop sitemap validate` after every edit — fix all errors before continuing.**

**⏸ Quick check**: Show the updated sitemap. Ask "Does this match what you have in mind? What should we build this round?"

### After every sitemap update — rebuild journey-map.csv:

```bash
floop prototype init
```

This regenerates `.floop/journey-map.csv` — the domain → HTML mapping table that the preview sidebar reads.
- Domain is taken from each page's optional `domain:` field in frontmatter
- If `domain:` is absent, it is derived from the file path: `build/journey/auth/login.html` → domain `auth`
- Re-run whenever pages are added, removed, or moved in sitemap.md

**MUST run `floop prototype init` after every sitemap.md edit.**

---

## Step D — Component (本次迭代组件)

Pick **one page or flow** to build. Identify what components it needs.

```bash
floop component init      # first time only
floop component validate  # after every edit — also checks token paths
```

**If `floop component validate` warns "token path not found":**
→ Go back to Step B, add the missing token to `component.tokens.json`, validate tokens, then return here.

Component schema (`.floop/components.yaml`):
```yaml
version: 1
updated_at: 2024-01-15
css_framework: tailwind
components:
  - id: navbar
    title: 导航栏
    category: Navigation    # used for grouping in showcase — e.g. Actions / Navigation / Inputs / Containment / Feedback
    status: draft           # draft | built
    html_tag: nav           # optional — native HTML tag this component replaces;
                            # journey check flags any <nav> that has no data-component="navbar"
                            # or class="navbar" on that element
    variants:
      - default
      - scrolled
    tokens:
      background: color.surface    # maps prop → token path in *.tokens.json
      text: color.text
    notes: Sticky header with responsive hamburger menu
```

Token paths in `tokens:` cross-reference `*.tokens.json` — `floop component validate` warns if any path is missing.

**MUST run `floop component validate` after every edit — fix all errors before continuing.**

### Component Showcase (Agent 生成，非 CLI)

**This step is MANDATORY and BLOCKING — generate the showcase before proceeding to Step E.**

Generate a **Material Design-style single-page showcase** — two files total, not one file per component:

**File 1: `build/components/components.js`**
Defines all components as vanilla JS render functions. Structure:
```js
// components.js — generated by floop Agent, DO NOT EDIT manually
const COMPONENTS = [
  {
    id: "navbar",
    title: "导航栏",
    category: "Navigation",
    status: "draft",
    tokens: { background: "color.surface", text: "color.text" },
    render() {
      return `<nav style="background:var(--color-surface);color:var(--color-text)">
        <span>Logo</span><ul><li>Home</li><li>About</li></ul>
      </nav>`;
    },
    variants: [
      { label: "Default", render: () => `...` },
      { label: "Scrolled", render: () => `...` },
    ]
  },
  // ... all other components
];
```
- Each component has a `render()` for the default state and a `variants[]` array
- Use CSS custom properties (`var(--token-name)`) — never hardcode values
- Interactive states: buttons clickable, inputs focusable
- Regenerate only new or changed components — preserve existing entries

**File 2: `build/components/index.html`**
A single-page showcase shell referencing both files:
```html
<link rel="stylesheet" href="../tokens/tokens.css">
<script src="./components.js"></script>
```
Layout (Material Design sidebar pattern):
- Left sidebar: component list grouped by `category`, with status badge
- Main panel: selected component name, description, token mapping table, variants rendered side-by-side
- Header: project name, stats (total / built / draft)
- Search/filter by category or status

**Do NOT proceed to Step E until `build/components/components.js` and `build/components/index.html` are both written.**

---

## Step E — Build (生成页面)

Generate one page per iteration as a standalone `.html` file.

> **BLOCKING PREREQUISITES — in order, all required:**
>
> 1. `floop token validate` — must exit with no errors
> 2. `floop token view` — must run to regenerate `tokens.css`
> 3. `floop component validate` — must exit with no errors
> 4. Component Showcase — `build/components/components.js` and `build/components/index.html` must both exist
> 5. `floop prototype init` — journey-map.csv must be up-to-date (re-run after any sitemap change)
>
> If any step is missing, complete it first. Skipping and writing HTML directly is **wrong**.

### Before writing HTML:
1. **Analyse the page first** — list every UI element this page needs (buttons, forms, cards, nav bars, icons, modals, etc.). This is a component-gap check:
   - For each element, find the matching entry in `.floop/components.yaml`
   - If ANY element has no matching component → **STOP. Go back to Step D**, add the missing component(s), re-run `floop component validate`, confirm the Component Showcase rebuilds — THEN return here
   - Do NOT write the page HTML until every required component is accounted for in `components.yaml`
2. **Check token coverage** — for every colour, spacing, radius, or typography value the page uses, verify the token path exists in `.floop/tokens/*.tokens.json`. If a value is missing → **STOP. Go back to Step B**, add the token, re-run `floop token validate` + `floop token view`, then return here
3. Re-read `.floop/tokens/*.tokens.json` (final pass for current values)
4. Re-read `.floop/components.yaml` (final pass for component inventory)
5. Link both shared assets in `<head>` — **both are required, in this order:**
   ```html
   <link rel="stylesheet" href="../tokens/tokens.css">
   <script src="../components/components.js" defer></script>
   ```
   Paths are relative from `.floop/build/journey/<page>.html`.
   - `tokens.css` — provides all CSS custom properties; do NOT re-declare `:root` variables manually
   - `components.js` — registers all component implementations; page HTML uses the component classes/elements defined here
6. Every UI element in the page MUST use a component from `components.yaml` — if a component is missing after the check above, something was skipped; go back to Step D immediately

### Coding rules:

> ❌ **NEVER — These are hard blockers, not style suggestions:**
>
> 1. **NO device shell inside the HTML** — do NOT wrap page content in a div that looks like an iPhone, Android, or any device mockup. The floop preview already wraps the iframe in a phone/tablet/desktop frame — adding one inside the HTML creates double-framing. The HTML must be a plain responsive page that fills its viewport naturally.
> 2. **NO explanatory text inside the page** — do NOT add labels, annotations, captions, comments, section headers like "Hero Section", or any text that describes the UI rather than being part of it. The page must look exactly like what a real user would see in a production app — nothing more.

**Structure**
- Semantic HTML5: `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`
- Exactly one `<h1>` per page; headings must not skip levels
- `<button>` for actions, `<a>` for navigation

**Token Usage**
- ALWAYS use CSS custom properties — never hardcode colors, spacing, or typography
- All pages share the same `:root` token block for visual consistency
- If a value isn't in the token system → go back to Step B, add it, then return

**Responsive — REQUIRED, not optional**
- Every page MUST include `<meta name="viewport" content="width=device-width, initial-scale=1">` in `<head>`
- Design for all 3 preview device modes — the floop preview toolbar lets users switch:
  - **Phone** → 390px wide (mobile layout)
  - **Tablet** → 768px wide (tablet layout)
  - **Web** → full width (desktop layout, reference at 1440px)
- Mobile-first: start with the Phone layout, enhance with `min-width` media queries: 768px (Tablet), 1024px, 1280px (Web)
- Every major layout section must reflow gracefully at 390px — NO horizontal overflow, NO fixed-pixel widths that exceed 390px
- CSS Grid or Flexbox — no floats, no table layouts
- Test mentally at all 3 widths before writing the file; if any width breaks, fix it before output

**Accessibility**
- Meaningful `alt` text on images (or `alt=""` if decorative)
- Keyboard-accessible interactive elements with visible focus styles
- Color contrast: 4.5:1 for text, 3:1 for large text
- `aria-label` / `aria-describedby` where needed

**Code quality**
- Inline `<style>` in `<head>` for page-specific styles only — shared styles come from `tokens.css` and component styles from `components.js`; do NOT duplicate what is already defined there
- If Tailwind: CDN link in `<head>`, use utility classes
- No additional JavaScript unless interactivity is explicitly required beyond what `components.js` provides
- Valid HTML — no unclosed tags, no deprecated elements

### Output: `.floop/build/journey/<page-name>.html`

**MUST write page HTML to `.floop/build/journey/`. Run `floop prototype validate` then `floop preview` after generating.**

### After generating page HTML — validate mapping:

```bash
floop prototype validate
```

Two checks are run:
1. Every `.floop/build/journey/**/*.html` file must have a row in `journey-map.csv`
2. Every domain in `journey-map.csv` must appear as a derived domain in `sitemap.md`

**If errors are reported:**
- `journey HTML not mapped` → the page was added without updating sitemap.md → go back to Step C, add the page entry, re-run `floop prototype init`
- `domain not found in sitemap` → journey-map.csv has a stale domain → re-run `floop prototype init` to regenerate from current sitemap.md

**MUST run `floop prototype validate` after every new or moved journey HTML.**

### After prototype validate — backward gap check:

```bash
floop journey check .floop/build/journey/<page-name>.html
```

Three checks are run:
1. **Head links** — `tokens.css` and `components.js` must be referenced in the HTML
2. **Token references** — every `var(--xxx)` must map to a leaf token in `*.tokens.json`
3. **Component coverage** — components defined in `components.yaml` but not referenced in the HTML are flagged
4. **Raw tag detection** — if a component declares `html_tag`, every native tag occurrence of that type is checked for a component reference. A tag is only flagged if it has **neither** `data-component="comp_id"` nor `class="comp_id"` on that specific element. Preferred pattern: `data-component="comp_id"` (invokes `components.js`) over bare CSS class.

**If errors are reported:**
- `missing <link> to tokens.css` → add `<link rel="stylesheet" href="../tokens/tokens.css">` to `<head>`
- `missing <script> for components.js` → add `<script src="../components/components.js" defer></script>` to `<head>`
- `token --xxx not found` → the HTML uses a token that doesn't exist → go back to Step B, add the token
- `found raw <tag> without component 'xxx'` → the HTML has a bare native tag with no component wiring → add `data-component="xxx"` or `class="xxx"` to that element
- `components defined but not referenced` → consider whether the page should use these components → if yes, refactor HTML to use them

**MUST run `floop journey check` after every new or modified journey HTML. Fix all errors before proceeding to Step F.**

---

## Step F — Confirm & Continue

1. Run `floop preview` — user opens browser to see the result
2. Ask: "Does this look right? What should we do next?"
3. Route based on answer:
   - **Refine this page** → back to Step E
   - **Tokens need adjustment** → back to Step B
   - **New component** → back to Step D
   - **New page/flow** → back to Step C
   - **Ready to deliver** → Deliver phase below

---

## Deliver

When the user is ready to share or request review:

1. Run `floop preview` — confirm everything renders correctly
2. Summarize: pages built, components defined, iterations completed
3. If floop-server is configured:
   ```bash
   floop push          # push to floop-server for review
   floop push index.html   # single file
   ```
4. floop-server generates a review link — reviewers annotate by clicking on elements
5. AI generates DOM-level patches:
   ```json
   {
     "selector": "#hero .cta-button",
     "action": "style",
     "property": "background-color",
     "old": "#3B82F6",
     "new": "#EF4444"
   }
   ```
   Supported actions: `style`, `text`, `attribute`, `add`, `remove`, `move`
6. Author reviews patches → approve / reject / merge → next round or approved
""",
    },
}
