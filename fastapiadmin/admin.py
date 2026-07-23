"""Core AdminSite and ModelAdmin classes."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Type

import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

PACKAGE_DIR = Path(__file__).parent


# ─────────────────────────────────────────────────────────────────
# Built-in sidebar icons (named shortcuts → inline SVG path data)
# ─────────────────────────────────────────────────────────────────

_ICONS: dict[str, str] = {
    "server": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v5c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 10v5c0 1.66 4.03 3 9 3s9-1.34 9-3v-5"/><path d="M3 15v4c0 1.66 4.03 3 9 3s9-1.34 9-3v-4"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "bolt": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "mail": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
    "terminal": '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
    "package": '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    "page": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
}


def _icon_svg(name_or_svg: str, size: int = 16) -> str:
    """Return a full <svg> tag from a named icon or raw SVG string."""
    if name_or_svg.strip().startswith("<"):
        return name_or_svg
    paths = _ICONS.get(name_or_svg, _ICONS["page"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )


# ─────────────────────────────────────────────────────────────────
# Custom page registry
# ─────────────────────────────────────────────────────────────────

@dataclass
class CustomPage:
    slug: str
    label: str
    icon: str = "page"
    handler: Callable | None = None

    def icon_svg(self, size: int = 16) -> str:
        return _icon_svg(self.icon, size)


# ─────────────────────────────────────────────────────────────────
# ModelAdmin
# ─────────────────────────────────────────────────────────────────

class ModelAdmin:
    """Override this class to customise how a model is displayed in the admin."""

    list_display: list[str] | None = None
    search_fields: list[str] = []
    exclude: list[str] = []
    readonly_fields: list[str] = []
    per_page: int = 20
    verbose_name_plural: str | None = None

    def __init__(self, model, admin_site: "AdminSite"):
        self.model = model
        self.admin_site = admin_site
        mapper = sa_inspect(model)
        self._columns: list[sa.Column] = [c for c in mapper.mapper.columns]
        self._pk_name: str = mapper.mapper.primary_key[0].name

        if self.verbose_name_plural is None:
            self.verbose_name_plural = model.__name__ + "s"

        if self.list_display is None:
            self.list_display = [c.name for c in self._columns[:6]]

    def get_queryset(self, session: Session, search: str = "") -> Any:
        q = session.query(self.model)
        if search and self.search_fields:
            filters = [
                sa.cast(getattr(self.model, f), sa.String).ilike(f"%{search}%")
                for f in self.search_fields
                if hasattr(self.model, f)
            ]
            if filters:
                q = q.filter(sa.or_(*filters))
        return q

    def get_object(self, session: Session, pk):
        return session.get(self.model, pk)

    def save_object(self, session: Session, obj, form_data: dict):
        from .fields import coerce_value
        mapper = sa_inspect(self.model)
        for col in mapper.mapper.columns:
            if col.name == self._pk_name:
                continue
            if col.name in self.readonly_fields:
                continue
            if col.name in self.exclude:
                continue
            raw = form_data.get(col.name)
            if isinstance(col.type, sa.Boolean):
                raw = form_data.get(col.name, "off")
            val = coerce_value(raw if raw != "" else None, col)
            setattr(obj, col.name, val)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    def get_form_fields(self):
        from .fields import get_field_info
        fields = []
        for col in self._columns:
            if col.name == self._pk_name:
                continue
            if col.name in self.exclude:
                continue
            info = get_field_info(col)
            info["readonly"] = col.name in self.readonly_fields
            fields.append(info)
        return fields


# ─────────────────────────────────────────────────────────────────
# AdminSite
# ─────────────────────────────────────────────────────────────────

class AdminSite:
    """Mount this on your FastAPI app to add the admin panel."""

    def __init__(
        self,
        app: FastAPI,
        *,
        engine: sa.Engine,
        prefix: str = "/admin",
        title: str = "Admin",
        username: str | None = None,
        password: str | None = None,
        secret_key: str = "change-me-in-production",
        brand_color: str = "#6366f1",
    ):
        self.app = app
        self.engine = engine
        self.prefix = prefix.rstrip("/")
        self.title = title
        self.username = username
        self.password = password
        self.secret_key = secret_key
        self.brand_color = brand_color
        self._registry: dict[str, ModelAdmin] = {}
        self._pages: dict[str, CustomPage] = {}

        app.mount(
            f"{self.prefix}/static",
            StaticFiles(directory=str(PACKAGE_DIR / "static")),
            name="fastapiadmin-static",
        )

        from .router import build_router
        router = build_router(self)
        app.include_router(router, prefix=self.prefix)

    # ------------------------------------------------------------------
    # Model registration
    # ------------------------------------------------------------------

    def register(self, model, *, admin_class: Type[ModelAdmin] | None = None):
        """Register a SQLAlchemy model.

            @admin.register(User)
            class UserAdmin(ModelAdmin):
                list_display = ["id", "name"]
        """
        def _register(cls_or_none):
            klass = cls_or_none if cls_or_none is not None else ModelAdmin
            instance = klass(model, self)
            self._registry[model.__name__.lower()] = instance
            return cls_or_none

        if admin_class is not None:
            _register(admin_class)
            return self
        return lambda cls: _register(cls) or cls

    # ------------------------------------------------------------------
    # Custom page registration
    # ------------------------------------------------------------------

    def page(self, slug: str, *, label: str, icon: str = "page"):
        """Register a custom sidebar page.

        The decorated async function receives ``request: Request`` and must
        return either:

        * A plain HTML string — automatically wrapped in the admin layout.
        * A FastAPI ``Response`` object — returned as-is (full control).

        Available icon names: server, chart, settings, bolt, globe, code,
        users, star, mail, terminal, package, page.
        You can also pass a raw ``<svg ...>`` string.

        Example::

            @admin.page("minecraft", label="Minecraft", icon="server")
            async def mc_page(request):
                players = get_online_players()
                return admin.html.page(
                    title="Minecraft Server",
                    subtitle=f"{players} online",
                    content=\"\"\"
                        <div class="card">
                            <div class="card-body">Server is running</div>
                        </div>
                    \"\"\",
                )
        """
        def decorator(func):
            self._pages[slug] = CustomPage(slug=slug, label=label, icon=icon, handler=func)
            return func
        return decorator

    # ------------------------------------------------------------------
    # HTML helpers (use inside custom page handlers)
    # ------------------------------------------------------------------

    @property
    def html(self) -> "_HtmlHelpers":
        return _HtmlHelpers(self)

    # ------------------------------------------------------------------
    # DB session
    # ------------------------------------------------------------------

    def get_session(self) -> Session:
        return Session(self.engine)

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    @property
    def auth_enabled(self) -> bool:
        return bool(self.username and self.password)


# ─────────────────────────────────────────────────────────────────
# HTML helper DSL  (admin.html.*)
# ─────────────────────────────────────────────────────────────────

class _HtmlHelpers:
    """Convenience builders for common admin UI fragments.

    All methods return plain HTML strings you can compose freely.
    """

    def __init__(self, admin: AdminSite):
        self._admin = admin

    # ── High-level page wrapper ──────────────────────────────────

    def page(
        self,
        *,
        title: str,
        subtitle: str = "",
        content: str = "",
        actions: str = "",
    ) -> str:
        """Full-page content block (title bar + body)."""
        sub = f'<div class="page-sub">{subtitle}</div>' if subtitle else ""
        act = f'<div>{actions}</div>' if actions else ""
        return f"""
<div class="page-header">
  <div>
    <div class="page-title">{title}</div>
    {sub}
  </div>
  {act}
</div>
{content}"""

    # ── Stat cards ───────────────────────────────────────────────

    def stat_card(
        self,
        label: str,
        value: str | int,
        *,
        icon: str = "chart",
        color: str = "#6366f1",
        link: str = "",
    ) -> str:
        svg = _icon_svg(icon, 20)
        link_html = f'<a href="{link}" class="stat-link" style="color:{color};">View →</a>' if link else ""
        return f"""
<div class="card stat-card">
  <div class="stat-icon" style="background:{color}18;color:{color};">{svg}</div>
  <div>
    <div class="stat-lbl">{label}</div>
    <div class="stat-val" style="color:{color};">{value}</div>
    {link_html}
  </div>
</div>"""

    def stats_row(self, *cards: str) -> str:
        """Wrap stat_card() calls in a responsive grid."""
        return f'<div class="stats-grid">{"".join(cards)}</div>'

    # ── Table ────────────────────────────────────────────────────

    def table(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        empty_msg: str = "No data.",
    ) -> str:
        if not rows:
            return f'<div class="empty"><div class="empty-ico">📭</div><h3>{empty_msg}</h3></div>'
        ths = "".join(f"<th>{h}</th>" for h in headers)
        trs = ""
        for row in rows:
            tds = "".join(f"<td>{cell}</td>" for cell in row)
            trs += f"<tr>{tds}</tr>"
        return f"""
<div class="card">
  <div class="table-wrap">
    <table>
      <thead><tr>{ths}</tr></thead>
      <tbody>{trs}</tbody>
    </table>
  </div>
</div>"""

    # ── Alert / info boxes ───────────────────────────────────────

    def alert(self, message: str, *, kind: str = "success") -> str:
        colors = {
            "success": ("#f0fdf4", "#bbf7d0", "#15803d"),
            "error":   ("#fef2f2", "#fecaca", "#b91c1c"),
            "warning": ("#fffbeb", "#fde68a", "#92400e"),
            "info":    ("#eff6ff", "#bfdbfe", "#1e40af"),
        }
        bg, border, text = colors.get(kind, colors["info"])
        return (
            f'<div class="alert" '
            f'style="background:{bg};border:1px solid {border};color:{text};'
            f'padding:12px 16px;border-radius:7px;font-size:13.5px;margin-bottom:16px;">'
            f'{message}</div>'
        )

    # ── Card ─────────────────────────────────────────────────────

    def card(self, content: str, *, padding: bool = True) -> str:
        inner = f'<div class="form-body">{content}</div>' if padding else content
        return f'<div class="card">{inner}</div>'

    # ── Button ───────────────────────────────────────────────────

    def button(
        self,
        label: str,
        *,
        href: str = "#",
        kind: str = "primary",
        icon: str = "",
    ) -> str:
        svg = f'<span>{_icon_svg(icon, 15)}</span>' if icon else ""
        return f'<a href="{href}" class="btn btn-{kind}">{svg}{label}</a>'

    # ── Badge ────────────────────────────────────────────────────

    def badge(self, text: str, *, color: str = "gray") -> str:
        cls = {"green": "badge-green", "red": "badge-red"}.get(color, "badge-gray")
        return f'<span class="badge {cls}">{text}</span>'
