function clearHost(host) {
  host.innerHTML = "";
  return host;
}

function renderFormatBar(bar, editable) {
  bar.innerHTML = "";
  if (!editable) return;
  const cmds = [
    ["Bold", "bold"],
    ["Italic", "italic"],
    ["Underline", "underline"],
    ["H1", "formatBlock", "h1"],
    ["H2", "formatBlock", "h2"],
    ["• List", "insertUnorderedList"],
    ["1. List", "insertOrderedList"],
  ];
  const wrap = document.createElement("div");
  wrap.className = "format-bar";
  for (const [label, cmd, val] of cmds) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("mousedown", (e) => e.preventDefault());
    b.addEventListener("click", () => document.execCommand(cmd, false, val || null));
    wrap.appendChild(b);
  }
  bar.appendChild(wrap);
}

function mountWysiwyg(host, formatBar, content, canEdit, onChange) {
  clearHost(host);
  renderFormatBar(formatBar, canEdit);
  const ed = document.createElement("div");
  ed.className = "wysiwyg";
  ed.contentEditable = canEdit ? "true" : "false";
  ed.innerHTML = content || "<p></p>";
  let timer;
  ed.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => onChange(ed.innerHTML), 600);
  });
  host.appendChild(ed);
  return {
    getContent: () => ed.innerHTML,
    setContent: (html) => {
      ed.innerHTML = html || "<p></p>";
    },
  };
}

function mountText(host, formatBar, content, canEdit, onChange) {
  clearHost(host);
  formatBar.innerHTML = "";
  const ta = document.createElement("textarea");
  ta.className = "md-editor";
  ta.style.height = "calc(100vh - 120px)";
  ta.value = content || "";
  ta.readOnly = !canEdit;
  let timer;
  ta.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => onChange(ta.value), 600);
  });
  host.appendChild(ta);
  return {
    getContent: () => ta.value,
    setContent: (t) => {
      ta.value = t || "";
    },
  };
}

function mountMarkdown(host, formatBar, content, canEdit, mode, onChange) {
  clearHost(host);
  formatBar.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "md-split";

  const preview = document.createElement("div");
  preview.className = "md-preview";

  function render(md) {
    preview.innerHTML = window.marked ? marked.parse(md || "") : md;
  }

  if (mode === "md_render") {
    preview.classList.add("full");
    render(content);
    wrap.appendChild(preview);
    host.appendChild(wrap);
    return {
      getContent: () => content,
      setContent: (t) => {
        content = t;
        render(t);
      },
    };
  }

  const ta = document.createElement("textarea");
  ta.className = "md-editor";
  ta.value = content || "";
  ta.readOnly = !canEdit;
  let timer;
  ta.addEventListener("input", () => {
    render(ta.value);
    clearTimeout(timer);
    timer = setTimeout(() => onChange(ta.value), 600);
  });
  render(ta.value);
  wrap.append(ta, preview);
  host.appendChild(wrap);
  return {
    getContent: () => ta.value,
    setContent: (t) => {
      ta.value = t || "";
      render(ta.value);
    },
  };
}

function mountSpreadsheet(host, formatBar, sheets, canEdit, onChange) {
  clearHost(host);
  formatBar.innerHTML = "";
  const data = sheets && Object.keys(sheets).length ? sheets : { Sheet: [[""]] };
  const sheetName = Object.keys(data)[0];
  let rows = data[sheetName].map((r) => [...r]);

  // pad
  const cols = Math.max(8, ...rows.map((r) => r.length));
  while (rows.length < 12) rows.push(Array(cols).fill(""));
  rows = rows.map((r) => {
    const copy = [...r];
    while (copy.length < cols) copy.push("");
    return copy;
  });

  const wrap = document.createElement("div");
  wrap.className = "sheet-wrap";
  const table = document.createElement("table");
  table.className = "sheet-table";

  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  hr.appendChild(document.createElement("th"));
  for (let c = 0; c < cols; c++) {
    const th = document.createElement("th");
    th.textContent = String.fromCharCode(65 + (c % 26));
    hr.appendChild(th);
  }
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  function emit() {
    onChange({ [sheetName]: rows });
  }

  rows.forEach((row, rIdx) => {
    const tr = document.createElement("tr");
    const rh = document.createElement("th");
    rh.textContent = String(rIdx + 1);
    tr.appendChild(rh);
    row.forEach((cell, cIdx) => {
      const td = document.createElement("td");
      const input = document.createElement("input");
      input.value = cell == null ? "" : String(cell);
      input.readOnly = !canEdit;
      let timer;
      input.addEventListener("input", () => {
        rows[rIdx][cIdx] = input.value;
        clearTimeout(timer);
        timer = setTimeout(emit, 700);
      });
      td.appendChild(input);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  host.appendChild(wrap);

  return {
    getContent: () => ({ [sheetName]: rows }),
    setContent: () => {},
  };
}

function mountBinary(host, formatBar, meta) {
  clearHost(host);
  formatBar.innerHTML = "";
  const panel = document.createElement("div");
  panel.className = "binary-panel";
  const icon = document.createElement("div");
  icon.className = "binary-icon";
  icon.textContent = meta.kind === "pdf" ? "📕" : "📦";
  const name = document.createElement("div");
  name.textContent = meta.filename || "file";
  const actions = document.createElement("div");
  actions.className = "binary-actions";
  const dl = document.createElement("a");
  dl.className = "btn primary";
  dl.href = meta.download_url;
  dl.textContent = "Download";
  actions.appendChild(dl);
  if (meta.kind === "pdf") {
    const open = document.createElement("a");
    open.className = "btn";
    open.href = meta.open_url;
    open.target = "_blank";
    open.rel = "noopener";
    open.textContent = "Open";
    actions.appendChild(open);
  }
  panel.append(icon, name, actions);
  host.appendChild(panel);
  return { getContent: () => null, setContent: () => {} };
}

window.DMEditors = {
  mountWysiwyg,
  mountText,
  mountMarkdown,
  mountSpreadsheet,
  mountBinary,
};
