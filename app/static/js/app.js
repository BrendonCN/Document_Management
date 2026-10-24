(() => {
  const root = document.getElementById("app");
  if (!root) return;

  const state = {
    canMutate: root.dataset.canMutate === "true",
    isAdmin: root.dataset.isAdmin === "true",
    role: root.dataset.role,
    tree: [],
    expanded: new Set(),
    selectedId: null,
    selectedNode: null,
    versions: [],
    versionId: null,
    viewMode: "normal",
    editor: null,
    dirty: false,
    compareVersionId: null,
  };

  const els = {
    sidebar: document.getElementById("sidebar"),
    tree: document.getElementById("tree"),
    search: document.getElementById("tree-search"),
    toggle: document.getElementById("sidebar-toggle"),
    name: document.getElementById("doc-name"),
    kind: document.getElementById("doc-kind"),
    format: document.getElementById("format-bar"),
    verPrev: document.getElementById("ver-prev"),
    verNext: document.getElementById("ver-next"),
    verLabel: document.getElementById("ver-label"),
    verDate: document.getElementById("ver-date"),
    empty: document.getElementById("empty-state"),
    editorHost: document.getElementById("editor-host"),
    diffHost: document.getElementById("diff-host"),
    modal: document.getElementById("modal"),
    modalTitle: document.getElementById("modal-title"),
    modalBody: document.getElementById("modal-body"),
    fileImport: document.getElementById("file-import"),
  };

  function toast(msg) {
    console.log(msg);
  }

  async function refreshTree() {
    state.tree = await DMApi.tree();
    DMTree.renderTree(els.tree, state.tree, state, {
      refresh: () => DMTree.renderTree(els.tree, state.tree, state, thisHandlers()),
      select: (node) => selectNode(node),
      move: async (srcId, parentId) => {
        await DMApi.moveNode(srcId, { parent_id: parentId, sort_order: 0 });
        await refreshTree();
      },
    });
  }

  function thisHandlers() {
    return {
      refresh: () => DMTree.renderTree(els.tree, state.tree, state, thisHandlers()),
      select: (node) => selectNode(node),
      move: async (srcId, parentId) => {
        await DMApi.moveNode(srcId, { parent_id: parentId, sort_order: 0 });
        await refreshTree();
      },
    };
  }

  async function selectNode(node) {
    if (state.dirty && state.canMutate) {
      // auto-save already debounced; continue
    }
    state.selectedId = node.id;
    state.selectedNode = await DMApi.getNode(node.id);
    state.expanded.add(node.id);
    DMTree.renderTree(els.tree, state.tree, state, thisHandlers());
    els.name.value = state.selectedNode.name;
    els.kind.textContent = state.selectedNode.kind;
    state.versions = await DMApi.versions(node.id);
    const currentId =
      state.selectedNode.current_version_id ||
      (state.versions.length ? state.versions[state.versions.length - 1].id : null);
    state.versionId = currentId;
    await loadVersion();
  }

  function toLocalInput(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  async function loadVersion() {
    if (!state.selectedNode || !state.versionId) {
      showEmpty();
      return;
    }
    const version = state.versions.find((v) => v.id === state.versionId) ||
      (await DMApi.neighbors(state.versionId)).current;
    els.verLabel.value = version.version_label;
    els.verDate.value = toLocalInput(version.version_date);

    const neigh = await DMApi.neighbors(state.versionId);
    els.verPrev.disabled = !neigh.prev;
    els.verNext.disabled = !neigh.next;
    state._prev = neigh.prev;
    state._next = neigh.next;

    if (state.viewMode === "split") {
      await showDiff();
      return;
    }
    await showEditor();
  }

  function showEmpty() {
    els.empty.classList.remove("hidden");
    els.editorHost.classList.add("hidden");
    els.diffHost.classList.add("hidden");
  }

  async function showEditor() {
    els.empty.classList.add("hidden");
    els.diffHost.classList.add("hidden");
    els.editorHost.classList.remove("hidden");
    const data = await DMApi.content(state.versionId);
    const kind = state.selectedNode.kind;
    const canEdit = state.canMutate && state.viewMode !== "md_render";
    const saveText = async (content) => {
      if (!state.canMutate) return;
      await DMApi.saveContent(state.versionId, { content });
      state.dirty = false;
    };
    const saveSheet = async (sheets) => {
      if (!state.canMutate) return;
      await DMApi.saveSheet(state.versionId, { sheets });
      state.dirty = false;
    };

    if (kind === "docx") {
      state.editor = DMEditors.mountWysiwyg(
        els.editorHost,
        els.format,
        data.content,
        canEdit,
        (c) => {
          state.dirty = true;
          saveText(c);
        }
      );
    } else if (kind === "txt" || kind === "folder") {
      state.editor = DMEditors.mountText(
        els.editorHost,
        els.format,
        data.content,
        canEdit,
        (c) => {
          state.dirty = true;
          saveText(c);
        }
      );
    } else if (kind === "md") {
      state.editor = DMEditors.mountMarkdown(
        els.editorHost,
        els.format,
        data.content,
        canEdit,
        state.viewMode,
        (c) => {
          state.dirty = true;
          saveText(c);
        }
      );
    } else if (kind === "xlsx") {
      state.editor = DMEditors.mountSpreadsheet(
        els.editorHost,
        els.format,
        data.sheets,
        canEdit,
        (sheets) => {
          state.dirty = true;
          saveSheet(sheets);
        }
      );
    } else if (kind === "pdf" || kind === "object") {
      state.editor = DMEditors.mountBinary(els.editorHost, els.format, data);
    } else {
      state.editor = DMEditors.mountText(
        els.editorHost,
        els.format,
        data.content || "",
        canEdit,
        (c) => saveText(c)
      );
    }
  }

  async function showDiff() {
    els.empty.classList.add("hidden");
    els.editorHost.classList.add("hidden");
    els.diffHost.classList.remove("hidden");
    els.format.innerHTML = "";

    if (state.versions.length < 2) {
      els.diffHost.innerHTML =
        "<p class='lede'>Need at least two versions to diff. Use Copy to create one.</p>";
      return;
    }
    const idx = state.versions.findIndex((v) => v.id === state.versionId);
    const left = state.versions[Math.max(0, idx - 1)] || state.versions[0];
    const right = state.versions[idx] || state.versions[state.versions.length - 1];
    state.compareVersionId = left.id;
    const diff = await DMApi.diff(left.id, right.id);
    DMDiff.renderDiff(els.diffHost, diff, state.canMutate, async (direction, lineIndex) => {
      await DMApi.applyDiffLine({
        left_version_id: left.id,
        right_version_id: right.id,
        direction,
        line_index: lineIndex,
      });
      await showDiff();
    });
  }

  function openModal(title, bodyHtml, { confirmLabel = "OK", onConfirm } = {}) {
    return new Promise((resolve) => {
      els.modalTitle.textContent = title;
      els.modalBody.innerHTML = bodyHtml;
      const confirmBtn = document.getElementById("modal-confirm");
      confirmBtn.textContent = confirmLabel;
      const form = document.getElementById("modal-form");
      const handler = (e) => {
        form.removeEventListener("close", handler);
        const val = els.modal.returnValue;
        if (val === "confirm") {
          if (onConfirm) onConfirm();
          resolve(true);
        } else resolve(false);
      };
      // dialog form method=dialog sets returnValue from submit button
      els.modal.addEventListener("close", handler, { once: true });
      els.modal.showModal();
    });
  }

  // Sidebar toggle
  els.toggle.addEventListener("click", () => {
    root.classList.toggle("sidebar-collapsed");
  });

  // Search
  let searchTimer;
  els.search.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      const q = els.search.value.trim();
      if (!q) {
        await refreshTree();
        return;
      }
      const results = await DMApi.search(q);
      const fakeTree = results.map((n) => ({ ...n, children: [] }));
      DMTree.renderTree(els.tree, fakeTree, state, thisHandlers());
    }, 250);
  });

  // Name rename
  els.name.addEventListener("change", async () => {
    if (!state.selectedNode || !state.canMutate) return;
    await DMApi.updateNode(state.selectedNode.id, { name: els.name.value });
    await refreshTree();
  });

  // Version nav
  els.verPrev.addEventListener("click", async () => {
    if (state._prev) {
      state.versionId = state._prev.id;
      await loadVersion();
    }
  });
  els.verNext.addEventListener("click", async () => {
    if (state._next) {
      state.versionId = state._next.id;
      await loadVersion();
    }
  });

  els.verLabel.addEventListener("change", async () => {
    if (!state.versionId || !state.canMutate) return;
    await DMApi.updateVersion(state.versionId, { version_label: els.verLabel.value });
    state.versions = await DMApi.versions(state.selectedNode.id);
  });

  els.verDate.addEventListener("change", async () => {
    if (!state.versionId || !state.canMutate) return;
    const iso = new Date(els.verDate.value).toISOString();
    await DMApi.updateVersion(state.versionId, { version_date: iso });
  });

  // View modes
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.viewMode = btn.dataset.mode;
      await loadVersion();
    });
  });

  // New node
  const btnNew = document.getElementById("btn-new");
  if (btnNew) {
    btnNew.addEventListener("click", async () => {
      const body = `
        <div class="modal-body-stack">
          <label>Name<input id="m-name" required /></label>
          <label>Type
            <select id="m-kind">
              <option value="folder">folder</option>
              <option value="txt">txt</option>
              <option value="md">md</option>
              <option value="docx">docx</option>
              <option value="xlsx">xlsx</option>
              <option value="pdf">pdf</option>
              <option value="object">object</option>
            </select>
          </label>
        </div>`;
      els.modalTitle.textContent = "New node";
      els.modalBody.innerHTML = body;
      document.getElementById("modal-confirm").textContent = "Create";
      const form = document.getElementById("modal-form");
      const onClose = async () => {
        if (els.modal.returnValue !== "confirm") return;
        const name = document.getElementById("m-name").value.trim();
        const kind = document.getElementById("m-kind").value;
        if (!name) return;
        const created = await DMApi.createNode({
          name,
          kind,
          parent_id: state.selectedId || null,
        });
        await refreshTree();
        await selectNode(created);
      };
      els.modal.addEventListener("close", onClose, { once: true });
      els.modal.showModal();
    });
  }

  // Delete with double confirm
  const btnDelete = document.getElementById("btn-delete");
  if (btnDelete) {
    btnDelete.addEventListener("click", async () => {
      if (!state.selectedNode) return;
      els.modalTitle.textContent = "Delete node?";
      els.modalBody.innerHTML = `<p>Delete <strong>${state.selectedNode.name}</strong> and all children/versions?</p>`;
      document.getElementById("modal-confirm").textContent = "Continue";
      els.modal.addEventListener(
        "close",
        async () => {
          if (els.modal.returnValue !== "confirm") return;
          els.modalTitle.textContent = "Confirm again";
          els.modalBody.innerHTML = `<p>This cannot be undone. Type <code>DELETE</code> to confirm.</p>
            <input id="m-confirm-text" />`;
          document.getElementById("modal-confirm").textContent = "Delete";
          els.modal.addEventListener(
            "close",
            async () => {
              if (els.modal.returnValue !== "confirm") return;
              const typed = document.getElementById("m-confirm-text")?.value;
              if (typed !== "DELETE") {
                alert("Confirmation text did not match.");
                return;
              }
              await DMApi.deleteNode(state.selectedNode.id);
              state.selectedId = null;
              state.selectedNode = null;
              state.versionId = null;
              showEmpty();
              await refreshTree();
            },
            { once: true }
          );
          els.modal.showModal();
        },
        { once: true }
      );
      els.modal.showModal();
    });
  }

  // Copy version
  const btnCopy = document.getElementById("btn-copy-ver");
  if (btnCopy) {
    btnCopy.addEventListener("click", async () => {
      if (!state.selectedNode || !state.versionId) return;
      const v = await DMApi.createVersion(state.selectedNode.id, {
        copy_from_version_id: state.versionId,
      });
      state.versions = await DMApi.versions(state.selectedNode.id);
      state.versionId = v.id;
      await loadVersion();
    });
  }

  // Import / Export
  const btnImport = document.getElementById("btn-import");
  if (btnImport) {
    btnImport.addEventListener("click", () => {
      if (!state.selectedNode) return alert("Select a node first");
      els.fileImport.click();
    });
  }
  els.fileImport.addEventListener("change", async () => {
    const file = els.fileImport.files?.[0];
    if (!file || !state.selectedNode) return;
    const v = await DMApi.importFile(state.selectedNode.id, file);
    state.versions = await DMApi.versions(state.selectedNode.id);
    state.versionId = v.id;
    els.fileImport.value = "";
    await loadVersion();
  });

  document.getElementById("btn-export").addEventListener("click", () => {
    if (!state.versionId) return;
    window.location.href = `/api/versions/${state.versionId}/export`;
  });

  // History / audit
  document.getElementById("btn-history").addEventListener("click", async () => {
    const events = await DMApi.audit(state.selectedId || undefined);
    const html = `<div class="history-list">${events
      .map(
        (e) => `<div class="history-item">
        <strong>${e.action}</strong>
        <div class="history-meta">${e.username} · ${new Date(e.created_at).toLocaleString()}</div>
        <div>${e.path_snapshot || ""}</div>
      </div>`
      )
      .join("") || "<p>No events</p>"}</div>`;
    els.modalTitle.textContent = "Audit history";
    els.modalBody.innerHTML = html;
    document.getElementById("modal-confirm").textContent = "Close";
    els.modal.showModal();
  });

  // Allow drop on empty sidebar root
  els.tree.addEventListener("dragover", (e) => e.preventDefault());
  els.tree.addEventListener("drop", async (e) => {
    if (!state.canMutate) return;
    e.preventDefault();
    if (e.target !== els.tree) return;
    const srcId = Number(e.dataTransfer.getData("text/plain"));
    if (!srcId) return;
    await DMApi.moveNode(srcId, { parent_id: null, sort_order: 0 });
    await refreshTree();
  });

  refreshTree().catch((err) => {
    console.error(err);
    els.tree.innerHTML = `<p class="error-banner">${err.message}</p>`;
  });
})();
