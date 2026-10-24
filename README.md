# Document Management

A server-rendered document management web app with a collapsible tree sidebar, versioned files, per-type editors, IntelliJ-style split/diff, and an audit trail.

## Stack

| Package | Version |
| --- | --- |
| FastAPI | 0.111.0 |
| Uvicorn | 0.30.1 |
| Jinja2 | 3.1.6 |
| Pydantic | 2.13.4 |

SQLite lives at `data/app.db`. Version blobs are stored under `data/storage/{node_id}/{version_id}/`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Seeded SSO stub users

On first launch the app creates:

| Username | Role |
| --- | --- |
| `admin` | admin |
| `editor` | editor |
| `viewer` | viewer |

Sign in via the local SSO stub (pick a user / optional role override). The `AuthProvider` interface is OIDC-ready; only the stub is wired today.

### Roles

- **viewer** — read, export, open PDF, history
- **editor** — create / edit / import / copy version / delete
- **admin** — editor rights + user management

## Features

- Nested tree (any node may have children); drag-and-drop reparent; search
- Versions with label/date, prev/next, copy, import, export, delete (with double confirm on nodes)
- Editors: WYSIWYG (docx/txt), spreadsheet (xlsx), Markdown edit + MD Rendering mode, PDF/object download/open
- Split/diff with line highlights and `->` / `<-` overwrite
- Audit history modal; admin user management at `/admin/users`

## Project layout

```
app/
  main.py          # FastAPI app + Jinja pages
  config.py
  db.py / models.py / schemas.py / seed.py
  auth/            # AuthProvider + stub + RBAC deps
  api/             # JSON routes under /api/...
  services/        # tree, versions, storage, content, audit
  templates/
  static/
data/
  app.db
  storage/
```

## API sketch

- `GET /api/nodes/tree`, `POST /api/nodes`, `POST /api/nodes/{id}/move`, …
- `GET /api/nodes/{id}/versions`, `POST /api/nodes/{id}/import`, `GET /api/versions/{id}/export`
- `GET|PUT /api/versions/{id}/content`, `PUT /api/versions/{id}/spreadsheet`
- `POST /api/diff`, `POST /api/diff/apply-line`
- `GET /api/audit`, `GET|POST /api/users` (admin)

## Out of scope

Real OIDC, real-time collaboration, and pixel-perfect Word/Excel fidelity.
