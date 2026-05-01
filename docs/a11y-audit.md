# Accessibility audit — latincy-lexicon-site

**Baseline:** WCAG 2.1 Level AA + general best practices.
**Scope:** the whole user-facing surface — `templates/*.html` + `static/site.{css,js}`.
**Method:** source review + computed contrast ratios. No automated scan, no assistive-tech smoke test yet.
**Date:** 2026-05-01

## Findings by priority

### Tier 1 — Blockers

**1. Brand color `--accent: #67abe4` fails WCAG 1.4.3 / 1.4.11 in every load-bearing role** (text, button, border, focus accent).
Computed contrast against white: **2.46:1**. Required: 4.5:1 for normal text, 3:1 for large-bold text, 3:1 for non-text UI components.

Where it fails:
- `static/site.css:33-34` — `.lookup button { background: var(--accent); color: #fff }`. White-on-accent at 2.46:1 on the primary "Look up" CTA. Normal-size text — straight 4.5:1 fail.
- `static/site.css:10` — `.brand` link in the header at 1.3rem 700 weight (≥18.66px bold = "large text" threshold). 2.46:1 still fails the relaxed 3:1 large-text minimum.
- `static/site.css:52` — `.expand-btn[aria-expanded="true"] { color: var(--accent); border-color: var(--accent); }` (active state of every per-token expander on `/sentence`).
- `static/site.css:61, 66` — `.entry--top-sense` border, `.pos-match-badge` color.
- `static/site.css:78` — `.paradigm-table td.paradigm-hit { border: 2px solid var(--accent); }` (the queried-form highlight). At 2.46:1 the border itself fails the 3:1 non-text-contrast minimum.

**Fix:** darken `--accent` by ~30% to about `#2a73c8` (≈5.2:1 against white — verify with measurement before adopting). Optionally keep the lighter shade as `--accent-light` for decorative gradients/backgrounds where text contrast doesn't apply. Verify the deployed site still feels "LatinCy blue" at the darker value.

---

**2. Lookup form input has no programmatic label** (WCAG 1.3.1 / 4.1.2 / 3.3.2).
*Files:* `templates/index.html:10-15`.
The textarea has `id="text"` but no `<label for="text">`. The `<p class="lede">` paragraph above describes what to enter, but there's no programmatic association — a screen reader lands on the input and announces only "edit text, Poeta bonus carmina scribit" with no purpose stated.

**Fix:** wrap or precede with a real label. Visually hidden is fine if you don't want to disturb the layout:
```html
<label for="text" class="visually-hidden">Latin sentence or word to look up</label>
```
Add a `.visually-hidden` utility class (clipped, not `display: none`).

---

**3. Icon-only buttons and links have no accessible name** (WCAG 4.1.2).
*Files:*
- `templates/sentence.html:41` — `<a href="/word/{{ tok.text }}">↗</a>`. Just the unicode arrow. Screen readers announce "northeast arrow link" — opaque.
- `templates/sentence.html:43-49` — `<button class="flag-btn">⚑</button>`. The flag glyph alone. No `aria-label`, no `title`. Same problem on `_word_entries.html:40-46` ("⚑ Flag this entry" — that one has visible text, OK).

**Fix:** add `aria-label="Open dedicated page for {{ tok.text }}"` to the `↗` link and `aria-label="Flag this entry"` to bare-glyph flag buttons. (The expand-btn at `sentence.html:32-40` already has `aria-label="Toggle entry for {{ tok.text }}"` — model the others on it.)

---

**4. Non-top-sense entry text uses `#bfbfbf`, contrast 1.84:1.**
*Files:* `static/site.css:53-59` — `.entry { color: #bfbfbf }` is the *base* state; only `.entry--top-sense` overrides to `color: inherit`. So every dictionary entry that isn't the WSD pick is rendered in body text at 1.84:1 — well below any threshold including AAA's 3:1 floor.

**Fix:** the visual goal is "dim non-top entries." Achieve it without sacrificing contrast: either keep text at the normal `#222`-ish color and dim *only* the border + headword color, or use `color: #6b6b6b` (~5:1) for the body text. The semantic-emphasis cue can still come through the border / `.pos-match-badge`. Don't use `opacity: 0.5` as a substitute — it multiplies and usually still fails contrast against a non-white background.

---

### Tier 2 — Significant

**5. Skip-link to main content missing** (WCAG 2.4.1).
*File:* `templates/base.html:15-22`.
Keyboard users hit the brand link, then the "API docs" nav link, then the form on every page load. A skip-link is one line and lets them jump straight in.

**Fix:** add at the top of `<body>`:
```html
<a class="skip-link" href="#main-content">Skip to main content</a>
```
Add `id="main-content"` on the `<main>` element and a `.skip-link` rule that visually-hides until `:focus`.

---

**6. Touch targets below the 24px AA floor** (WCAG 2.5.8).
*Files:*
- `static/site.css:43-44` — `.expand-btn { padding: 0.15rem 0.5rem; font-size: 1rem }` → ~22px tall.
- `static/site.css:135` — `.flag-btn { padding: 0 0.3rem }` → ~17px tall.

**Fix:** add `min-height: 24px` (AA) or ideally `min-height: 44px` (AAA / mobile-friendly) to both. Visually-small glyphs can stay if the hit area is padded to the target size.

---

**7. Latin content not marked with `lang="la"`** (WCAG 3.1.2).
*Files:* `templates/sentence.html:12` (`<blockquote>{{ result.text }}</blockquote>`), every paradigm cell in `_paradigm_table.html`, every headword in `_word_entries.html`, every gloss containing Latin examples.
The whole document says `<html lang="en">` — correct for the chrome, wrong for the Latin. Screen readers will pronounce *amat* as English, *carmen* as the English car-name, etc.

**Fix:** wrap Latin spans in a `lang="la"` attribute. Pragmatic version: add `lang="la"` on the `<blockquote>` for sentence input, on `<h1>` of `paradigm.html`/`word.html`, on `_paradigm_table.html` cells, and on the headword `<h3>` in `_word_entries.html`. Glosses stay in English.

---

**8. Dynamic content swaps are silent** (WCAG 4.1.3).
*Files:* `templates/sentence.html:32-51` (htmx fragment swaps for per-token entry). The target `<td id="entry-{{ loop.index }}">` is just a container; nothing is announced when the fragment lands.
The flag-status live region (`site.js:79`) is correct, but on success the panel is replaced wholesale (`site.js:105`) — the live region disappears, and the new "Thanks — logged as #N" sits in a static `<p>`. A screen reader user may or may not catch the announcement depending on swap timing.

**Fix:** add `aria-live="polite"` to the htmx target container, or `role="status"`. For the flag-success swap, leave the live region in place and update its text rather than replacing the whole panel.

---

**9. `.flag-btn` missing `aria-haspopup` and initial `aria-expanded="false"`.**
*Files:* `templates/sentence.html:43-49`, `templates/_word_entries.html:40-46`. The button opens an inline disclosure panel; only `site.js:134` sets `aria-expanded` after open. Before any interaction, assistive tech sees a plain button with no indication it controls anything.

**Fix:** render the buttons with `aria-expanded="false"` and `aria-haspopup="dialog"` (or `="true"`) by default. The JS already toggles `aria-expanded`; this just makes the initial state explicit.

---

**10. `:focus-visible` styles not defined.**
*Files:* `static/site.css` — no `:focus`/`:focus-visible` rules anywhere.
Browser defaults supply *something*, but several buttons (`.lookup button`, `.flag-submit`) override `border: none` and rely on the UA outline, which can be inconsistent or visually clash with the dark accent.

**Fix:** add an explicit accent-aware focus style:
```css
:focus-visible {
  outline: 2px solid var(--accent);  /* once #1 is fixed and accent passes 3:1 */
  outline-offset: 2px;
}
```

---

### Tier 3 — Nice-to-have

**11. `<meta name="description">` missing** (WCAG/best practice + SEO). One line in `base.html`.

**12. `autofocus` on the lookup input** (`templates/index.html:13`) can disorient screen reader users who land mid-page on a form. Consider removing or scoping to non-mobile.

**13. Footer wraps in `<small>`** (`templates/base.html:26`). Multiple browsers render this at ~13px which is at the readability floor. Consider explicit `font-size: 0.875rem` (14px) or remove the `<small>`.

**14. Form input borders fail 3:1 non-text contrast.**
- `static/site.css:27` — `.lookup input { border: 1px solid #bbb }` → 1.92:1.
- `static/site.css:43` — `.expand-btn { border: 1px solid #ccc }` → 1.61:1.

Fix is `#999` (2.85:1, still fails) → `#767676` (4.54:1, passes). Touch this when you address Tier 1 contrast.

**15. `paradigm-hit` `border-radius: 6px` doesn't render visibly because the table is `border-collapse: collapse`.**
Pre-existing visual nit; raised earlier this session. Switching just the paradigm-table to `border-collapse: separate; border-spacing: 0` would let the radius show — at the cost of re-adding the row-bottom borders manually. Not strictly an a11y issue.

---

### Already correct ✓

- `<html lang="en">` on the document, charset and viewport meta present (`base.html:2-5`).
- Per-page `<title>` blocks override the default — descriptive and unique.
- Real semantic landmarks: `<header>`, `<nav>`, `<main>`, `<footer>` (`base.html:16-33`).
- Heading hierarchy is orderly: one `<h1>` per page; `<h2>` for paradigm-homonym sections; `<h3>` for entry blocks and paradigm sub-sections (Indicative, Subjunctive, Participles…); `<h4>` for voice/participle subdivisions.
- `<ul>` / `<ol>` used for actual lists (alternates, glosses); not faked with `<div>`.
- Real `<button>` and `<a>` elements throughout — no `<div onClick>`.
- `.expand-btn` already carries `aria-expanded` (initialized in template) plus `aria-label` (`templates/sentence.html:32-40`). Good model for fixing #3 and #9.
- `.flag-status` uses `aria-live="polite"` (`site.js:79`) — correct for routine status messages.
- Tables on small screens (`/sentence`) flatten to stacked cards using `data-label::before` — preserves column-header context for screen readers. The paradigm tables stay tabular but pin the row-label column with `position: sticky` for legibility while panning. (`static/site.css:210-269`.)
- Cache-busted static assets (`?v={{ site_version }}`) — operationally important for a11y fixes that touch CSS.
- No CSS animations, transitions, or auto-playing media → `prefers-reduced-motion` is N/A.
- No third-party rich widgets (maps, editors, charts) — htmx is the only client lib and handles real anchor/button semantics.

## Suggested fix order

1. **Tier 1 in one PR**: contrast (#1, #4) + missing labels and accessible names (#2, #3). Touches `site.css`, `templates/index.html`, `templates/sentence.html`, `templates/_word_entries.html`. Also bumps the deployed `--accent` value, so test the brand reads correctly before merging.
2. **Tier 2 a11y polish PR**: skip-link (#5), touch-target sizing (#6), `lang="la"` annotations (#7), htmx live regions (#8), flag-btn ARIA defaults (#9), `:focus-visible` rule (#10).
3. **Tier 3 in a follow-up**: meta description (#11), autofocus reconsideration (#12), small-tag footer (#13), input border contrast (#14), paradigm-hit border-radius (#15).

Wire `axe-core` into the pytest suite (`@axe-core` doesn't have a Python flavor, but `pa11y-ci` does CLI HTTP checks against the running uvicorn server) before the next round so regressions get caught earlier than this audit.

## Open questions for the team

- Is there an institutional or vendor a11y standard that should layer on top of WCAG 2.1 AA? (None mentioned during this session — proceeding with WCAG AA baseline.)
- Preferred screen-reader stack to manually verify against once Tier 1 fixes ship — VoiceOver+Safari on macOS? NVDA+Firefox on Windows?
- Is the current brand color `#67abe4` intentionally fixed, or open to darkening for contrast? (Affects scope of #1.)

## Out of scope (this audit)

- API docs at `/docs` (FastAPI's auto-generated Swagger UI — third-party, separate audit needed).
- The `/healthz` JSON endpoint and any other non-HTML routes.
- Performance, SEO, PWA — overlapping concerns but separate disciplines.
- Latin content correctness (paradigms, glosses) — handled by the linguistic test suite.
- Mobile-only quirks beyond what source review can catch (iOS Safari rendering, Android keyboard behaviors) — needs device testing.
