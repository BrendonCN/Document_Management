from __future__ import annotations

from pathlib import Path
import sqlite3

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import api_router
from app.auth.deps import get_current_user
from app.auth.provider import get_auth_provider
from app.config import SESSION_COOKIE
from app.db import get_db
from app.models import User
from app.seed import init_db

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

app = FastAPI(title="Document Management", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    user: User | None = Depends(get_current_user),
):
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "users": ["admin", "editor", "viewer"]},
    )


@app.post("/login")
async def login_form(request: Request, db: sqlite3.Connection = Depends(get_db)):
    form = await request.form()
    username = str(form.get("username") or "").strip()
    role = str(form.get("role") or "").strip() or None
    create = form.get("create_if_missing") == "on"
    display_name = str(form.get("display_name") or "").strip() or None
    try:
        user, session_id = get_auth_provider().login(
            db,
            username=username,
            role=role,
            display_name=display_name,
            create_if_missing=create or username not in {"admin", "editor", "viewer"},
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "users": ["admin", "editor", "viewer"],
                "error": str(exc),
            },
            status_code=400,
        )
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    _ = user
    return response


@app.get("/logout")
def logout(request: Request, db: sqlite3.Connection = Depends(get_db)):
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        get_auth_provider().logout(db, session_id)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def workspace(
    request: Request,
    user: User | None = Depends(get_current_user),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        "workspace.html",
        {
            "request": request,
            "user": user,
            "can_mutate": user.role in {"admin", "editor"},
            "is_admin": user.role == "admin",
        },
    )


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    user: User | None = Depends(get_current_user),
):
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role != "admin":
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "user": user},
    )


@app.get("/health")
def health():
    return {"ok": True}
