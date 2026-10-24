async function api(path, options = {}) {
  const opts = { ...options };
  opts.headers = { ...(options.headers || {}) };
  if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch (_) {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

window.DMApi = {
  tree: () => api("/api/nodes/tree"),
  search: (q) => api(`/api/nodes/search?q=${encodeURIComponent(q)}`),
  getNode: (id) => api(`/api/nodes/${id}`),
  createNode: (body) => api("/api/nodes", { method: "POST", body }),
  updateNode: (id, body) => api(`/api/nodes/${id}`, { method: "PATCH", body }),
  moveNode: (id, body) => api(`/api/nodes/${id}/move`, { method: "POST", body }),
  deleteNode: (id) => api(`/api/nodes/${id}`, { method: "DELETE" }),
  versions: (nodeId) => api(`/api/nodes/${nodeId}/versions`),
  neighbors: (versionId) => api(`/api/versions/${versionId}/neighbors`),
  createVersion: (nodeId, body) =>
    api(`/api/nodes/${nodeId}/versions`, { method: "POST", body }),
  updateVersion: (id, body) => api(`/api/versions/${id}`, { method: "PATCH", body }),
  deleteVersion: (id) => api(`/api/versions/${id}`, { method: "DELETE" }),
  importFile: async (nodeId, file, label) => {
    const fd = new FormData();
    fd.append("file", file);
    if (label) fd.append("version_label", label);
    return api(`/api/nodes/${nodeId}/import`, { method: "POST", body: fd });
  },
  content: (versionId) => api(`/api/versions/${versionId}/content`),
  saveContent: (versionId, body) =>
    api(`/api/versions/${versionId}/content`, { method: "PUT", body }),
  saveSheet: (versionId, body) =>
    api(`/api/versions/${versionId}/spreadsheet`, { method: "PUT", body }),
  diff: (left, right) =>
    api("/api/diff", { method: "POST", body: { left_version_id: left, right_version_id: right } }),
  applyDiffLine: (body) => api("/api/diff/apply-line", { method: "POST", body }),
  audit: (nodeId) =>
    api(nodeId ? `/api/audit?node_id=${nodeId}` : "/api/audit"),
  users: () => api("/api/users"),
  createUser: (body) => api("/api/users", { method: "POST", body }),
  updateUser: (id, body) => api(`/api/users/${id}`, { method: "PATCH", body }),
  deleteUser: (id) => api(`/api/users/${id}`, { method: "DELETE" }),
};
