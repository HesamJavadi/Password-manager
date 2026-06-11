const state = {
  csrfToken: null,
  username: null,
  entries: [],
  status: null,
};

const app = document.getElementById("app");

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (state.csrfToken && options.method && options.method !== "GET") {
    headers["X-CSRF-Token"] = state.csrfToken;
  }
  const res = await fetch(path, { credentials: "same-origin", ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

function toast(msg, type = "") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatAge(seconds) {
  if (seconds == null) return "";
  const min = Math.floor(seconds / 60);
  const rem = seconds % 60;
  if (min > 0) return `${min}m ${rem}s ago`;
  return `${rem}s ago`;
}

function formatTimeout(status) {
  if (!status?.session_timeout_seconds || status.session_age_seconds == null) return "";
  const remaining = status.session_timeout_seconds - status.session_age_seconds;
  const min = Math.floor(remaining / 60);
  return `Auto-lock in ${min}m`;
}

async function loadStatus() {
  state.status = await api("/api/status");
  return state.status;
}

async function loadEntries() {
  state.entries = await api("/api/entries");
  return state.entries;
}

function renderLogin() {
  const needsInit = state.status && !state.status.vault_exists;
  app.innerHTML = `
    <div class="login-card card">
      <h1>Password Manager</h1>
      <p class="subtitle">${needsInit ? "Create your vault" : "Unlock your vault"}</p>
      <div id="login-error" class="error hidden"></div>
      <form id="login-form">
        <label for="password">Master password</label>
        <input type="password" id="password" autocomplete="current-password" required autofocus>
        ${needsInit ? `
          <label for="confirm">Confirm password</label>
          <input type="password" id="confirm" autocomplete="new-password" required>
        ` : ""}
        <button type="submit" class="btn btn-primary">${needsInit ? "Create vault" : "Unlock"}</button>
      </form>
    </div>
  `;

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("login-error");
    errorEl.classList.add("hidden");

    if (needsInit) {
      const confirm = document.getElementById("confirm").value;
      if (password !== confirm) {
        errorEl.textContent = "Passwords do not match";
        errorEl.classList.remove("hidden");
        return;
      }
    }

    try {
      const endpoint = needsInit ? "/api/init" : "/api/login";
      const data = await api(endpoint, {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      state.csrfToken = data.csrf_token;
      state.username = data.username;
      await refresh();
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.classList.remove("hidden");
    }
  });
}

function renderMain() {
  app.innerHTML = `
    <div class="header-row">
      <div>
        <h1>Password Manager</h1>
        <p class="subtitle">Logged in as ${escapeHtml(state.username || "")}</p>
      </div>
      <div class="session-info">
        <div>${formatAge(state.status?.session_age_seconds)}</div>
        <div>${formatTimeout(state.status)}</div>
      </div>
    </div>
    <div class="card">
      <div class="toolbar">
        <input type="search" class="search" id="search" placeholder="Search entries...">
        <button class="btn btn-secondary btn-sm" id="btn-add">Add entry</button>
        <button class="btn btn-secondary btn-sm" id="btn-generate">Generate</button>
        <button class="btn btn-secondary btn-sm" id="btn-lock">Lock</button>
      </div>
      <div id="entries-container"></div>
    </div>
  `;

  document.getElementById("btn-lock").addEventListener("click", lockVault);
  document.getElementById("btn-add").addEventListener("click", () => showEntryModal());
  document.getElementById("btn-generate").addEventListener("click", showGenerateModal);

  let searchTimer;
  document.getElementById("search").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => handleSearch(e.target.value), 250);
  });

  renderEntries(state.entries);
}

function renderEntries(entries) {
  const container = document.getElementById("entries-container");
  if (!entries.length) {
    container.innerHTML = `<div class="empty-state">No passwords saved yet. Click "Add entry" to get started.</div>`;
    return;
  }

  container.innerHTML = `
    <table class="entries-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>Username</th>
          <th>URL</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${entries.map((e) => `
          <tr data-title="${escapeHtml(e.title)}">
            <td><strong>${escapeHtml(e.title)}</strong></td>
            <td>${escapeHtml(e.username || "—")}</td>
            <td>${e.url ? `<a href="${escapeHtml(e.url)}" target="_blank" rel="noopener">${escapeHtml(e.url)}</a>` : "—"}</td>
            <td>
              <div class="entry-actions">
                <button class="btn btn-secondary btn-sm btn-copy" data-title="${escapeHtml(e.title)}">Copy</button>
                <button class="btn btn-secondary btn-sm btn-view" data-title="${escapeHtml(e.title)}">View</button>
                <button class="btn btn-secondary btn-sm btn-edit" data-title="${escapeHtml(e.title)}">Edit</button>
                <button class="btn btn-danger btn-sm btn-delete" data-title="${escapeHtml(e.title)}">Delete</button>
              </div>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;

  container.querySelectorAll(".btn-copy").forEach((btn) => {
    btn.addEventListener("click", () => copyPassword(btn.dataset.title));
  });
  container.querySelectorAll(".btn-view").forEach((btn) => {
    btn.addEventListener("click", () => viewEntry(btn.dataset.title));
  });
  container.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", () => editEntry(btn.dataset.title));
  });
  container.querySelectorAll(".btn-delete").forEach((btn) => {
    btn.addEventListener("click", () => deleteEntry(btn.dataset.title));
  });
}

async function handleSearch(query) {
  if (!query.trim()) {
    await loadEntries();
    renderEntries(state.entries);
    return;
  }
  try {
    const results = await api(`/api/search?q=${encodeURIComponent(query)}`);
    renderEntries(results);
  } catch {
    renderEntries([]);
  }
}

async function copyPassword(title) {
  try {
    const entry = await api(`/api/entries/${encodeURIComponent(title)}`);
    await navigator.clipboard.writeText(entry.password);
    toast("Password copied", "success");
  } catch (err) {
    toast(err.message);
  }
}

async function viewEntry(title) {
  try {
    const entry = await api(`/api/entries/${encodeURIComponent(title)}`);
    showEntryModal(entry, true);
  } catch (err) {
    toast(err.message);
  }
}

async function editEntry(title) {
  try {
    const entry = await api(`/api/entries/${encodeURIComponent(title)}`);
    showEntryModal(entry);
  } catch (err) {
    toast(err.message);
  }
}

async function deleteEntry(title) {
  if (!confirm(`Delete "${title}"?`)) return;
  try {
    await api(`/api/entries/${encodeURIComponent(title)}`, { method: "DELETE" });
    toast("Entry deleted", "success");
    await refreshEntries();
  } catch (err) {
    toast(err.message);
  }
}

function showModal(html) {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `<div class="modal">${html}</div>`;
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.remove();
  });
  document.body.appendChild(overlay);
  return overlay;
}

function showEntryModal(entry = null, readonly = false) {
  const isEdit = entry && !readonly;
  const overlay = showModal(`
    <h2>${readonly ? "View entry" : isEdit ? "Edit entry" : "Add entry"}</h2>
    <form id="entry-form">
      <label>Title</label>
      <input type="text" id="f-title" value="${escapeHtml(entry?.title || "")}" ${isEdit || readonly ? "readonly" : ""} required>
      <label>Username</label>
      <input type="text" id="f-username" value="${escapeHtml(entry?.username || "")}" ${readonly ? "readonly" : ""}>
      <label>Password</label>
      <div class="password-field">
        <input type="${readonly ? "text" : "password"}" id="f-password" value="${escapeHtml(entry?.password || "")}" ${readonly ? "readonly" : ""} required>
        ${!readonly ? `<button type="button" class="btn btn-secondary btn-sm" id="toggle-pass">Show</button>` : ""}
      </div>
      <label>URL</label>
      <input type="url" id="f-url" value="${escapeHtml(entry?.url || "")}" ${readonly ? "readonly" : ""}>
      <label>Notes</label>
      <textarea id="f-notes" ${readonly ? "readonly" : ""}>${escapeHtml(entry?.notes || "")}</textarea>
      <div class="modal-actions">
        ${readonly ? `<button type="button" class="btn btn-secondary" id="btn-close">Close</button>` : `
          <button type="button" class="btn btn-secondary" id="btn-cancel">Cancel</button>
          <button type="submit" class="btn btn-primary">${isEdit ? "Save" : "Add"}</button>
        `}
      </div>
    </form>
  `);

  overlay.querySelector("#btn-close, #btn-cancel")?.addEventListener("click", () => overlay.remove());

  const passInput = overlay.querySelector("#f-password");
  overlay.querySelector("#toggle-pass")?.addEventListener("click", () => {
    const show = passInput.type === "password";
    passInput.type = show ? "text" : "password";
    overlay.querySelector("#toggle-pass").textContent = show ? "Hide" : "Show";
  });

  if (!readonly) {
    overlay.querySelector("#entry-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        title: overlay.querySelector("#f-title").value,
        username: overlay.querySelector("#f-username").value,
        password: overlay.querySelector("#f-password").value,
        url: overlay.querySelector("#f-url").value,
        notes: overlay.querySelector("#f-notes").value,
      };
      try {
        if (isEdit) {
          await api(`/api/entries/${encodeURIComponent(entry.title)}`, {
            method: "PATCH",
            body: JSON.stringify({
              username: body.username,
              password: body.password,
              url: body.url,
              notes: body.notes,
            }),
          });
          toast("Entry updated", "success");
        } else {
          await api("/api/entries", { method: "POST", body: JSON.stringify(body) });
          toast("Entry added", "success");
        }
        overlay.remove();
        await refreshEntries();
      } catch (err) {
        toast(err.message);
      }
    });
  }
}

function showGenerateModal() {
  const overlay = showModal(`
    <h2>Generate password</h2>
    <form id="gen-form">
      <label>Length</label>
      <input type="number" id="g-length" value="16" min="1" max="128" required>
      <label><input type="checkbox" id="g-digits" checked> Include digits</label><br><br>
      <label><input type="checkbox" id="g-symbols" checked> Include symbols</label><br><br>
      <label>Save as (optional)</label>
      <input type="text" id="g-title" placeholder="Entry title">
      <div id="gen-result" class="hidden" style="margin: 1rem 0;">
        <label>Generated password</label>
        <div class="password-field">
          <input type="text" id="g-password" readonly>
          <button type="button" class="btn btn-secondary btn-sm" id="g-copy">Copy</button>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" id="btn-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Generate</button>
      </div>
    </form>
  `);

  overlay.querySelector("#btn-cancel").addEventListener("click", () => overlay.remove());

  overlay.querySelector("#gen-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const data = await api("/api/generate", {
        method: "POST",
        body: JSON.stringify({
          length: parseInt(overlay.querySelector("#g-length").value, 10),
          digits: overlay.querySelector("#g-digits").checked,
          symbols: overlay.querySelector("#g-symbols").checked,
          title: overlay.querySelector("#g-title").value,
        }),
      });
      overlay.querySelector("#gen-result").classList.remove("hidden");
      overlay.querySelector("#g-password").value = data.password;
      overlay.querySelector("#g-copy").onclick = () => {
        navigator.clipboard.writeText(data.password);
        toast("Copied", "success");
      };
      if (data.saved) {
        toast(`Saved as "${data.title}"`, "success");
        await refreshEntries();
      } else {
        toast("Password generated", "success");
      }
    } catch (err) {
      toast(err.message);
    }
  });
}

async function lockVault() {
  try {
    await api("/api/logout", { method: "POST" });
  } catch {
    // session may already be expired
  }
  state.csrfToken = null;
  state.username = null;
  state.entries = [];
  await refresh();
}

async function refreshEntries() {
  await loadEntries();
  const container = document.getElementById("entries-container");
  if (container) renderEntries(state.entries);
}

async function refresh() {
  await loadStatus();
  if (state.status.logged_in) {
    state.csrfToken = state.status.csrf_token;
    state.username = state.status.username;
    await loadEntries();
    renderMain();
  } else {
    state.csrfToken = null;
    state.username = null;
    renderLogin();
  }
}

refresh().catch(() => renderLogin());
