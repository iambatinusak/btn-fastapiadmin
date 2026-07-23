"""FastAPI router for admin panel."""
from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import URLSafeSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from .admin import AdminSite

PACKAGE_DIR = Path(__file__).parent

_jinja_env = Environment(
    loader=FileSystemLoader(str(PACKAGE_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)


# ─────────────────────────── helpers ────────────────────────────


def _flash(request: Request, admin: "AdminSite", msg: str, kind: str = "success"):
    signer = URLSafeSerializer(admin.secret_key, salt="flash")
    payload = signer.dumps({"msg": msg, "kind": kind})
    request.state._flash_cookie = payload  # type: ignore[attr-defined]


def _get_flash(request: Request, admin: "AdminSite") -> dict | None:
    raw = request.cookies.get("_fadmin_flash")
    if not raw:
        return None
    try:
        signer = URLSafeSerializer(admin.secret_key, salt="flash")
        return signer.loads(raw)
    except Exception:
        return None


def _check_auth(request: Request, admin: "AdminSite") -> bool:
    if not admin.auth_enabled:
        return True
    signer = URLSafeSerializer(admin.secret_key, salt="session")
    token = request.cookies.get("_fadmin_session")
    if not token:
        return False
    try:
        data = signer.loads(token)
        return data.get("auth") is True
    except Exception:
        return False


def _auth_redirect(admin: "AdminSite") -> RedirectResponse:
    return RedirectResponse(f"{admin.prefix}/login", status_code=302)


def _set_response_cookies(response, request: Request, admin: "AdminSite"):
    if hasattr(request.state, "_flash_cookie"):
        response.set_cookie(
            "_fadmin_flash",
            request.state._flash_cookie,
            max_age=10,
            httponly=True,
            samesite="lax",
        )


def _ctx(admin: "AdminSite", request: Request, **extra) -> dict:
    """Build common template context (request NOT included — passed to TemplateResponse directly)."""
    flash = _get_flash(request, admin)
    return {
        "admin": admin,
        "registry": admin._registry,
        "flash": flash,
        **extra,
    }


def _render(request: Request, name: str, ctx: dict, status_code: int = 200) -> HTMLResponse:
    """Render a Jinja2 template directly — bypasses Starlette's version-sensitive wrapper."""
    ctx["request"] = request
    html = _jinja_env.get_template(name).render(ctx)
    return HTMLResponse(html, status_code=status_code)


# ─────────────────────────── builder ────────────────────────────


def build_router(admin: "AdminSite") -> APIRouter:
    router = APIRouter()

    # ── Custom pages ─────────────────────────────────────────────
    # Registered FIRST so their slugs beat /{model_name} pattern.

    @router.get("/pages/{page_slug}", response_class=HTMLResponse)
    async def custom_page(request: Request, page_slug: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        cp = admin._pages.get(page_slug)
        if cp is None:
            return HTMLResponse("Custom page not found", status_code=404)

        import inspect as _inspect
        if _inspect.iscoroutinefunction(cp.handler):
            result = await cp.handler(request)
        else:
            result = cp.handler(request)

        # If the handler returned a plain string, wrap it in the admin layout
        if isinstance(result, str):
            ctx = _ctx(admin, request, page=cp, page_content=result)
            return _render(request, "custom_page.html", ctx)
        return result

    # ── Login ────────────────────────────────────────────────────

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if not admin.auth_enabled:
            return RedirectResponse(f"{admin.prefix}/", status_code=302)
        return _render(request, "login.html", _ctx(admin, request))

    @router.post("/login")
    async def login_submit(request: Request):
        form = await request.form()
        user = form.get("username", "")
        pwd = form.get("password", "")
        if user == admin.username and pwd == admin.password:
            signer = URLSafeSerializer(admin.secret_key, salt="session")
            token = signer.dumps({"auth": True})
            resp = RedirectResponse(f"{admin.prefix}/", status_code=302)
            resp.set_cookie("_fadmin_session", token, httponly=True, samesite="lax")
            return resp
        ctx = _ctx(admin, request, error="Invalid username or password.")
        return _render(request, "login.html", ctx, status_code=401)

    @router.get("/logout")
    async def logout(request: Request):
        resp = RedirectResponse(f"{admin.prefix}/login", status_code=302)
        resp.delete_cookie("_fadmin_session")
        return resp

    # ── Dashboard ────────────────────────────────────────────────

    @router.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        db = admin.get_session()
        try:
            stats = []
            for key, ma in admin._registry.items():
                try:
                    count = db.query(ma.model).count()
                except Exception:
                    count = "—"
                stats.append({"key": key, "name": ma.verbose_name_plural, "count": count})
        finally:
            db.close()
        ctx = _ctx(admin, request, stats=stats)
        resp = _render(request, "dashboard.html", ctx)
        _clear_flash(resp)
        return resp

    # ── List view ────────────────────────────────────────────────

    @router.get("/{model_name}", response_class=HTMLResponse)
    async def list_view(request: Request, model_name: str, page: int = 1, q: str = ""):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)

        db = admin.get_session()
        try:
            qs = ma.get_queryset(db, search=q)
            total = qs.count()
            pages = max(1, math.ceil(total / ma.per_page))
            page = max(1, min(page, pages))
            offset = (page - 1) * ma.per_page
            items = qs.offset(offset).limit(ma.per_page).all()

            from .fields import format_cell
            rows = []
            for item in items:
                pk = getattr(item, ma._pk_name)
                cells = [format_cell(getattr(item, col, None)) for col in ma.list_display]
                rows.append({"pk": pk, "cells": cells})
        finally:
            db.close()

        ctx = _ctx(
            admin, request,
            ma=ma, model_name=model_name,
            headers=ma.list_display, rows=rows,
            total=total, page=page, pages=pages,
            q=q,
            page_range=_page_range(page, pages),
        )
        resp = _render(request, "list.html", ctx)
        _clear_flash(resp)
        return resp

    # ── Create ───────────────────────────────────────────────────

    @router.get("/{model_name}/new", response_class=HTMLResponse)
    async def create_form(request: Request, model_name: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)
        fields = ma.get_form_fields()
        ctx = _ctx(admin, request, ma=ma, model_name=model_name, fields=fields, obj=None, errors={})
        return _render(request, "form.html", ctx)

    @router.post("/{model_name}/new")
    async def create_submit(request: Request, model_name: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)

        form = dict(await request.form())
        db = admin.get_session()
        try:
            obj = ma.model()
            ma.save_object(db, obj, form)
        except Exception as e:
            db.rollback()
            fields = ma.get_form_fields()
            ctx = _ctx(admin, request, ma=ma, model_name=model_name,
                       fields=fields, obj=None, errors={"__all__": str(e)}, form_data=form)
            return _render(request, "form.html", ctx, status_code=422)
        finally:
            db.close()

        _flash(request, admin, f"New {ma.model.__name__} created successfully.")
        resp = RedirectResponse(f"{admin.prefix}/{model_name}", status_code=303)
        _set_response_cookies(resp, request, admin)
        return resp

    # ── Edit ─────────────────────────────────────────────────────

    @router.get("/{model_name}/{item_id}/edit", response_class=HTMLResponse)
    async def edit_form(request: Request, model_name: str, item_id: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)

        db = admin.get_session()
        try:
            obj = ma.get_object(db, _coerce_pk(item_id))
            if obj is None:
                return HTMLResponse("Object not found", status_code=404)
            obj_dict = {c.name: getattr(obj, c.name) for c in ma._columns}
        finally:
            db.close()

        fields = ma.get_form_fields()
        ctx = _ctx(admin, request, ma=ma, model_name=model_name,
                   fields=fields, obj=obj_dict, item_id=item_id, errors={})
        return _render(request, "form.html", ctx)

    @router.post("/{model_name}/{item_id}/edit")
    async def edit_submit(request: Request, model_name: str, item_id: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)

        form = dict(await request.form())
        db = admin.get_session()
        try:
            obj = ma.get_object(db, _coerce_pk(item_id))
            if obj is None:
                return HTMLResponse("Object not found", status_code=404)
            ma.save_object(db, obj, form)
        except Exception as e:
            db.rollback()
            fields = ma.get_form_fields()
            obj_dict = {**form, ma._pk_name: item_id}
            ctx = _ctx(admin, request, ma=ma, model_name=model_name,
                       fields=fields, obj=obj_dict, item_id=item_id,
                       errors={"__all__": str(e)})
            return _render(request, "form.html", ctx, status_code=422)
        finally:
            db.close()

        _flash(request, admin, f"{ma.model.__name__} updated successfully.")
        resp = RedirectResponse(f"{admin.prefix}/{model_name}", status_code=303)
        _set_response_cookies(resp, request, admin)
        return resp

    # ── Delete ───────────────────────────────────────────────────

    @router.get("/{model_name}/{item_id}/delete", response_class=HTMLResponse)
    async def delete_confirm(request: Request, model_name: str, item_id: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)

        db = admin.get_session()
        try:
            obj = ma.get_object(db, _coerce_pk(item_id))
            if obj is None:
                return HTMLResponse("Object not found", status_code=404)
            obj_repr = str(obj) if hasattr(obj, "__str__") else f"#{item_id}"
        finally:
            db.close()

        ctx = _ctx(admin, request, ma=ma, model_name=model_name,
                   item_id=item_id, obj_repr=obj_repr)
        return _render(request, "delete.html", ctx)

    @router.post("/{model_name}/{item_id}/delete")
    async def delete_submit(request: Request, model_name: str, item_id: str):
        if not _check_auth(request, admin):
            return _auth_redirect(admin)
        ma = admin._registry.get(model_name)
        if ma is None:
            return HTMLResponse("Model not found", status_code=404)

        db = admin.get_session()
        try:
            obj = ma.get_object(db, _coerce_pk(item_id))
            if obj is None:
                return HTMLResponse("Object not found", status_code=404)
            db.delete(obj)
            db.commit()
        finally:
            db.close()

        _flash(request, admin, f"{ma.model.__name__} deleted.", kind="error")
        resp = RedirectResponse(f"{admin.prefix}/{model_name}", status_code=303)
        _set_response_cookies(resp, request, admin)
        return resp

    return router


# ─────────────────────────── utils ──────────────────────────────


def _coerce_pk(value: str):
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


def _page_range(current: int, total: int) -> list[int | str]:
    if total <= 7:
        return list(range(1, total + 1))
    pages: list[int | str] = [1]
    if current > 3:
        pages.append("…")
    for p in range(max(2, current - 1), min(total, current + 2)):
        pages.append(p)
    if current < total - 2:
        pages.append("…")
    if total not in pages:
        pages.append(total)
    return pages


def _clear_flash(response):
    response.delete_cookie("_fadmin_flash")
