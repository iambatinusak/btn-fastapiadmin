# fastapiadmin

A beautiful, minimal admin panel for **FastAPI** + **SQLAlchemy**.

## Install

```bash
pip install fastapiadmin
```

## Quick Start

```python
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase
from fastapiadmin import AdminSite, ModelAdmin

engine = create_engine("sqlite:///./app.db")

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id      = Column(Integer, primary_key=True)
    name    = Column(String(100))
    email   = Column(String(200))
    active  = Column(Boolean, default=True)

Base.metadata.create_all(engine)

app = FastAPI()

admin = AdminSite(
    app=app,
    engine=engine,
    title="My Admin",
    username="admin",
    password="secret",
)

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display  = ["id", "name", "email", "active"]
    search_fields = ["name", "email"]
```

Visit **http://localhost:8000/admin** — done.

## AdminSite options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `app` | — | FastAPI instance |
| `engine` | — | SQLAlchemy `Engine` |
| `title` | `"Admin"` | Sidebar/page title |
| `prefix` | `"/admin"` | URL prefix |
| `username` | `None` | Login username (no auth if omitted) |
| `password` | `None` | Login password |
| `brand_color` | `"#6366f1"` | Accent color (any hex) |
| `secret_key` | `"change-me-in-production"` | Signs session cookies |

## ModelAdmin options

| Attribute | Default | Description |
|-----------|---------|-------------|
| `list_display` | all columns | Columns shown in list view |
| `search_fields` | `[]` | Columns searched by the search bar |
| `exclude` | `[]` | Fields hidden from create/edit form |
| `readonly_fields` | `[]` | Fields shown but not editable |
| `per_page` | `20` | Rows per page |
| `verbose_name_plural` | model name + "s" | Label in the sidebar |

## Run the demo

```bash
git clone https://github.com/fastapiadmin/fastapiadmin
cd fastapiadmin
pip install -e ".[dev]"
uvicorn example.main:app --reload
```

Open http://localhost:8000/admin — login: **admin / admin123**

## License

MIT
