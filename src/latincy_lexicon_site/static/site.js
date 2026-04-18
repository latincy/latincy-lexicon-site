// Chevron toggle for per-token expanders on /sentence.
//
// First click: HTMX fetches the fragment; htmx:afterSwap flips the button
// from ▸ to ▾. Second click on the same ▾: we intercept htmx:beforeRequest,
// cancel the refetch, and clear the target so it visibly collapses.
//
// Intercepting via htmx:beforeRequest (rather than a plain document click
// listener) is the only reliable way — a click listener fires after HTMX's
// element-level handler has already scheduled the request, producing a
// jitter where the panel clears then instantly re-populates.

document.addEventListener("htmx:beforeRequest", (e) => {
  const btn = e.detail.elt;
  if (!btn.classList || !btn.classList.contains("expand-btn")) return;
  const target = document.getElementById(btn.dataset.target);
  if (target && target.innerHTML.trim()) {
    // Panel is already populated — second click means "collapse".
    e.preventDefault();
    target.innerHTML = "";
    btn.textContent = "▸";
    btn.setAttribute("aria-expanded", "false");
  }
});

document.addEventListener("htmx:afterSwap", (e) => {
  const btn = document.querySelector(
    `.expand-btn[data-target="${e.target.id}"]`,
  );
  if (btn) {
    btn.textContent = "▾";
    btn.setAttribute("aria-expanded", "true");
  }
});
