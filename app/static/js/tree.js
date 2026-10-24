const KIND_ICONS = {
  folder: "📁",
  docx: "📄",
  xlsx: "📊",
  md: "📝",
  txt: "📃",
  pdf: "📕",
  object: "📦",
};

function renderTree(container, nodes, state, handlers) {
  container.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const node of nodes) {
    frag.appendChild(renderTreeItem(node, state, handlers, 0));
  }
  container.appendChild(frag);
}

function renderTreeItem(node, state, handlers, depth) {
  const wrap = document.createElement("div");
  wrap.className = "tree-item";
  wrap.dataset.id = String(node.id);

  const row = document.createElement("div");
  row.className = "tree-row";
  row.draggable = state.canMutate;
  row.dataset.id = String(node.id);
  if (state.selectedId === node.id) row.classList.add("active");

  const hasChildren = node.children && node.children.length;
  const expanded = state.expanded.has(node.id) || depth === 0;

  const twist = document.createElement("span");
  twist.className = "tree-twist";
  twist.textContent = hasChildren ? (expanded ? "▼" : "▶") : "·";
  if (hasChildren) {
    twist.addEventListener("click", (e) => {
      e.stopPropagation();
      if (state.expanded.has(node.id)) state.expanded.delete(node.id);
      else state.expanded.add(node.id);
      handlers.refresh();
    });
  }

  const icon = document.createElement("span");
  icon.className = "tree-icon";
  icon.textContent = KIND_ICONS[node.kind] || "📄";

  const label = document.createElement("span");
  label.className = "tree-label";
  label.textContent = node.name;

  row.append(twist, icon, label);
  row.addEventListener("click", () => handlers.select(node));

  if (state.canMutate) {
    row.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", String(node.id));
      e.dataTransfer.effectAllowed = "move";
      state.draggingId = node.id;
    });
    row.addEventListener("dragover", (e) => {
      e.preventDefault();
      row.classList.add("drag-over");
    });
    row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
    row.addEventListener("drop", async (e) => {
      e.preventDefault();
      row.classList.remove("drag-over");
      const srcId = Number(e.dataTransfer.getData("text/plain"));
      if (!srcId || srcId === node.id) return;
      await handlers.move(srcId, node.id);
    });
  }

  wrap.appendChild(row);

  if (hasChildren && expanded) {
    const kids = document.createElement("div");
    kids.className = "tree-children";
    for (const child of node.children) {
      kids.appendChild(renderTreeItem(child, state, handlers, depth + 1));
    }
    wrap.appendChild(kids);
  }

  return wrap;
}

window.DMTree = { renderTree, KIND_ICONS };
