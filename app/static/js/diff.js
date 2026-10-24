function renderDiff(host, diff, canEdit, onApply) {
  host.innerHTML = "";
  const layout = document.createElement("div");
  layout.className = "diff-layout";

  const left = document.createElement("div");
  left.className = "diff-pane";
  left.innerHTML = `<h3>Left · v#${diff.left_version_id}</h3>`;

  const mid = document.createElement("div");
  mid.className = "diff-actions";

  const right = document.createElement("div");
  right.className = "diff-pane";
  right.innerHTML = `<h3>Right · v#${diff.right_version_id}</h3>`;

  const leftMarks = new Map();
  const rightMarks = new Map();
  for (const op of diff.opcodes || []) {
    if (op.tag === "equal") continue;
    const mark = op.tag === "insert" ? "add" : op.tag === "delete" ? "del" : "chg";
    for (let i = op.left_start; i < op.left_end; i++) leftMarks.set(i, mark);
    for (let i = op.right_start; i < op.right_end; i++) rightMarks.set(i, mark);
  }

  (diff.left_lines || []).forEach((line, i) => {
    const row = document.createElement("div");
    row.className = "diff-line" + (leftMarks.has(i) ? ` ${leftMarks.get(i)}` : "");
    row.innerHTML = `<span class="ln">${i + 1}</span><span>${escapeHtml(line)}</span>`;
    left.appendChild(row);
  });

  (diff.right_lines || []).forEach((line, i) => {
    const row = document.createElement("div");
    row.className = "diff-line" + (rightMarks.has(i) ? ` ${rightMarks.get(i)}` : "");
    row.innerHTML = `<span class="ln">${i + 1}</span><span>${escapeHtml(line)}</span>`;
    right.appendChild(row);
  });

  const max = Math.max(diff.left_lines?.length || 0, diff.right_lines?.length || 0);
  for (let i = 0; i < max; i++) {
    if (!leftMarks.has(i) && !rightMarks.has(i)) continue;
    if (!canEdit) continue;
    const group = document.createElement("div");
    group.style.display = "grid";
    group.style.gap = "2px";
    const toRight = document.createElement("button");
    toRight.type = "button";
    toRight.className = "btn ghost";
    toRight.textContent = "->";
    toRight.title = `Overwrite right line ${i + 1} from left`;
    toRight.addEventListener("click", () => onApply("to_right", i));
    const toLeft = document.createElement("button");
    toLeft.type = "button";
    toLeft.className = "btn ghost";
    toLeft.textContent = "<-";
    toLeft.title = `Overwrite left line ${i + 1} from right`;
    toLeft.addEventListener("click", () => onApply("to_left", i));
    group.append(toRight, toLeft);
    mid.appendChild(group);
  }

  layout.append(left, mid, right);
  host.appendChild(layout);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

window.DMDiff = { renderDiff };
