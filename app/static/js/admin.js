async function loadUsers() {
  const users = await DMApi.users();
  const tbody = document.querySelector("#user-table tbody");
  tbody.innerHTML = "";
  for (const u of users) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${u.username}</td>
      <td><input data-field="display_name" value="${escapeAttr(u.display_name)}" /></td>
      <td>
        <select data-field="role">
          ${["admin", "editor", "viewer"]
            .map((r) => `<option value="${r}" ${r === u.role ? "selected" : ""}>${r}</option>`)
            .join("")}
        </select>
      </td>
      <td><input type="checkbox" data-field="is_active" ${u.is_active ? "checked" : ""} /></td>
      <td>${u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "—"}</td>
      <td>
        <button type="button" class="btn small" data-save>Save</button>
        <button type="button" class="btn small danger" data-del>Delete</button>
      </td>`;
    tr.querySelector("[data-save]").addEventListener("click", async () => {
      const display_name = tr.querySelector('[data-field="display_name"]').value;
      const role = tr.querySelector('[data-field="role"]').value;
      const is_active = tr.querySelector('[data-field="is_active"]').checked;
      await DMApi.updateUser(u.id, { display_name, role, is_active });
      await loadUsers();
    });
    tr.querySelector("[data-del]").addEventListener("click", async () => {
      if (!confirm(`Delete ${u.username}?`)) return;
      await DMApi.deleteUser(u.id);
      await loadUsers();
    });
    tbody.appendChild(tr);
  }
}

function escapeAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

document.getElementById("create-user").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  await DMApi.createUser({
    username: fd.get("username"),
    display_name: fd.get("display_name"),
    role: fd.get("role"),
  });
  e.target.reset();
  await loadUsers();
});

loadUsers().catch((err) => alert(err.message));
