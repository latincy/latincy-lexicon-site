// On the landing page the lookup input is autofocused with a prefilled
// example, which puts the caret at the end and scrolls narrow inputs past
// the start of the value. Reset to the start so the example reads "Poeta…"
// rather than "…scribit." on mobile.
{
  const input = document.querySelector("form.lookup input[type='text']");
  if (input && input.value) {
    input.setSelectionRange(0, 0);
    input.scrollLeft = 0;
  }
}

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

// Flag-report submission — inline panel that appears below the ⚑ button,
// posts to /flags/submit, swaps to a thank-you on success. Buttons are
// guarded by {% if flags_enabled %} in the templates, so this code only
// engages when the env var is flipped on.
const FLAG_ISSUES = [
  ["wrong-lemma", "Wrong lemma"],
  ["wrong-pos", "Wrong part of speech"],
  ["wrong-gloss", "Wrong or misleading gloss"],
  ["wrong-principal-parts", "Wrong principal parts"],
  ["missing-sense", "Missing sense / entry"],
  ["other", "Something else"],
];

function buildFlagPanel(btn) {
  const panel = document.createElement("div");
  panel.className = "flag-panel";
  const options = FLAG_ISSUES.map(
    ([v, label]) => `<option value="${v}">${label}</option>`,
  ).join("");
  panel.innerHTML = `
    <label>
      Issue
      <select class="flag-issue" required>${options}</select>
    </label>
    <label>
      Detail (optional)
      <textarea class="flag-note" rows="2" maxlength="1000"
        placeholder="What's wrong? Any correction?"></textarea>
    </label>
    <div class="flag-actions">
      <button type="button" class="flag-submit">Report</button>
      <button type="button" class="flag-cancel">Cancel</button>
      <span class="flag-status" aria-live="polite"></span>
    </div>
  `;
  return panel;
}

async function submitFlag(btn, panel) {
  const status = panel.querySelector(".flag-status");
  const issue = panel.querySelector(".flag-issue").value;
  const note = panel.querySelector(".flag-note").value.trim();
  const payload = {
    target_type: btn.dataset.targetType,
    subject: btn.dataset.subject,
    issue,
    target_ref: btn.dataset.targetRef || null,
    note: note || null,
  };
  status.textContent = "sending…";
  try {
    const res = await fetch("/flags/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    // Update the live region (don't replace the whole panel) so AT actually
    // announces the success message instead of seeing the live region vanish.
    status.textContent = `Thanks — logged as #${body.id}.`;
    panel.querySelector(".flag-issue").disabled = true;
    panel.querySelector(".flag-note").disabled = true;
    panel.querySelector(".flag-submit").disabled = true;
    btn.disabled = true;
  } catch (err) {
    status.textContent = `couldn't send (${err.message})`;
  }
}

// Flag-btn lives inline inside narrow table cells on /sentence, so
// when we're in a <tr> we inject a dedicated colspan row below for the
// panel. Outside tables we just append the panel after the button.
function openFlagPanel(btn) {
  const panel = buildFlagPanel(btn);
  panel.dataset.flagPanelFor = btn.dataset.targetRef || btn.dataset.subject;
  const cell = btn.closest("td");
  if (cell) {
    const row = cell.closest("tr");
    const newRow = document.createElement("tr");
    newRow.className = "flag-panel-row";
    const colspanCell = document.createElement("td");
    colspanCell.colSpan = cell.parentElement.children.length;
    colspanCell.appendChild(panel);
    newRow.appendChild(colspanCell);
    row.after(newRow);
  } else {
    btn.after(panel);
  }
  btn._flagPanel = panel;
  panel._flagBtn = btn;
  btn.setAttribute("aria-expanded", "true");
  panel.querySelector(".flag-issue").focus();
}

function closeFlagPanel(panel) {
  const btn = panel._flagBtn;
  const row = panel.closest("tr.flag-panel-row");
  if (row) row.remove();
  else panel.remove();
  if (btn) {
    btn.setAttribute("aria-expanded", "false");
    btn._flagPanel = null;
  }
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".flag-btn");
  if (btn) {
    e.preventDefault();
    if (btn._flagPanel && btn._flagPanel.isConnected) {
      closeFlagPanel(btn._flagPanel);
      return;
    }
    openFlagPanel(btn);
    return;
  }
  const cancel = e.target.closest(".flag-cancel");
  if (cancel) {
    const panel = cancel.closest(".flag-panel");
    if (panel) closeFlagPanel(panel);
    return;
  }
  const submit = e.target.closest(".flag-submit");
  if (submit) {
    const panel = submit.closest(".flag-panel");
    if (panel && panel._flagBtn) submitFlag(panel._flagBtn, panel);
  }
});
