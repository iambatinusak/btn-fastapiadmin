# fastapiadmin — Kullanım Kılavuzu

## İçindekiler

1. [Kurulum](#1-kurulum)
2. [Temel Kullanım](#2-temel-kullanım)
3. [AdminSite Seçenekleri](#3-adminsite-seçenekleri)
4. [ModelAdmin ile Özelleştirme](#4-modeladmin-ile-özelleştirme)
5. [Custom Sayfalar](#5-custom-sayfalar)
6. [HTML Yardımcıları (admin.html.*)](#6-html-yardımcıları-adminhtml)
7. [Gerçek Dünya Örnekleri](#7-gerçek-dünya-örnekleri)
8. [Kimlik Doğrulama](#8-kimlik-doğrulama)

---

## 1. Kurulum

```bash
pip install fastapiadmin
```

Bağımlılıklar otomatik kurulur:
`fastapi`, `sqlalchemy`, `jinja2`, `python-multipart`, `itsdangerous`

---

## 2. Temel Kullanım

```python
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase
from fastapiadmin import AdminSite, ModelAdmin

# --- Database ---
engine = create_engine("sqlite:///./app.db")

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id     = Column(Integer, primary_key=True)
    name   = Column(String(100))
    email  = Column(String(200))
    active = Column(Boolean, default=True)

Base.metadata.create_all(engine)

# --- App ---
app = FastAPI()

# --- Admin ---
admin = AdminSite(
    app=app,
    engine=engine,
    title="Benim Admin Panelim",
    username="admin",
    password="gizli123",
)

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display  = ["id", "name", "email", "active"]
    search_fields = ["name", "email"]
```

`uvicorn main:app --reload` ile çalıştır, ardından **http://localhost:8000/admin** adresine git.

---

## 3. AdminSite Seçenekleri

```python
admin = AdminSite(
    app=app,                              # FastAPI uygulaması (zorunlu)
    engine=engine,                        # SQLAlchemy Engine (zorunlu)
    title="My App",                       # Sidebar başlığı
    prefix="/admin",                      # URL prefix (varsayılan: /admin)
    username="admin",                     # Giriş kullanıcı adı (None = auth yok)
    password="secret",                    # Giriş şifresi
    brand_color="#6366f1",               # Accent rengi (herhangi bir hex)
    secret_key="cok-gizli-uretim-key",   # Cookie imzalama anahtarı
)
```

> ⚠️ Üretimde `secret_key` için güçlü rastgele bir değer kullan:
> ```python
> import secrets
> secret_key = secrets.token_hex(32)
> ```

---

## 4. ModelAdmin ile Özelleştirme

```python
@admin.register(Product)
class ProductAdmin(ModelAdmin):
    # Listede gösterilecek kolonlar
    list_display = ["id", "name", "price", "stock", "is_available"]

    # Arama kutusunun aradığı kolonlar
    search_fields = ["name", "description"]

    # Create/Edit formundan gizlenecek alanlar
    exclude = ["internal_code", "created_by_system"]

    # Görüntülenebilir ama düzenlenemeyen alanlar
    readonly_fields = ["created_at", "updated_at"]

    # Sayfa başına satır sayısı
    per_page = 25

    # Sidebar'da görünecek isim
    verbose_name_plural = "Ürünler"
```

### Desteklenen Kolon Tipleri

| SQLAlchemy Tipi | HTML Input |
|----------------|------------|
| `String`, `VARCHAR` | `<input type="text">` |
| `Text`, `UnicodeText` | `<textarea>` |
| `Integer`, `BigInteger` | `<input type="number">` |
| `Float`, `Numeric` | `<input type="number" step="any">` |
| `Boolean` | `<input type="checkbox">` |
| `DateTime` | `<input type="datetime-local">` |
| `Date` | `<input type="date">` |
| `Enum` | `<select>` |
| `JSON` | `<textarea>` |

### `__str__` Ekle (isteğe bağlı)

Delete ekranında model adının güzel görünmesi için:

```python
class User(Base):
    ...
    def __str__(self):
        return f"{self.name} <{self.email}>"
```

---

## 5. Custom Sayfalar

Admin paneline tamamen özel sekmeler ekleyebilirsin. Sadece bir fonksiyon yaz, geri kalan her şey otomatik:

```python
@admin.page("minecraft", label="Minecraft Server", icon="server")
async def minecraft_page(request):
    players = get_online_players()   # kendi kodun
    return admin.html.page(
        title="Minecraft Server",
        subtitle="SurvivalCraft — play.example.com:25565",
        content=admin.html.stats_row(
            admin.html.stat_card("Oyuncular", f"{players}/20", icon="users", color="#22c55e"),
            admin.html.stat_card("TPS", "19.8", icon="bolt", color="#f59e0b"),
        ),
    )
```

### `@admin.page()` Parametreleri

| Parametre | Açıklama |
|-----------|----------|
| `slug` | URL parçası → `/admin/pages/<slug>` |
| `label` | Sidebar'da görünecek isim |
| `icon` | İkon adı veya `<svg ...>` string |

### Kullanılabilir İkon İsimleri

`server`, `chart`, `settings`, `bolt`, `globe`, `code`,
`users`, `star`, `mail`, `terminal`, `package`, `page`

Özel SVG de gönderebilirsin:
```python
@admin.page("custom", label="Özel", icon='<svg viewBox="0 0 24 24">...</svg>')
```

### Handler Dönüş Tipleri

Fonksiyonun ya bir **HTML string** ya da **FastAPI Response** döndürmeli:

```python
# 1) String döndür → otomatik admin layout içine sarılır
@admin.page("status", label="Status")
async def status_page(request):
    return "<h1>Sistem çalışıyor</h1>"

# 2) Response döndür → tam kontrol
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

@admin.page("api-status", label="API Status")
async def api_status(request):
    return JSONResponse({"status": "ok", "uptime": 9999})

# 3) Redirect
@admin.page("goto-docs", label="Docs →")
async def goto_docs(request):
    return RedirectResponse("https://fastapi.tiangolo.com")
```

### Request ile Veri Okuma

```python
@admin.page("dashboard", label="Dashboard")
async def dashboard(request):
    # URL parametresi: /admin/pages/dashboard?period=7d
    period = request.query_params.get("period", "30d")

    # Cookie / session erişimi
    token = request.cookies.get("my_token")

    return admin.html.page(title="Dashboard", ...)
```

### POST İşlemleri (Form Gönderimi)

Custom sayfalarda POST işlemi yapmak için ayrı bir FastAPI route yaz:

```python
from fastapi import Request
from fastapi.responses import RedirectResponse

# Admin'deki custom sayfa (GET)
@admin.page("websender", label="WebSender", icon="terminal")
async def websender_page(request):
    return admin.html.page(
        title="WebSender",
        content="""
        <form method="post" action="/mc/send">
            <div class="form-group">
                <input class="form-control" name="cmd" placeholder="/say Hello!"/>
            </div>
            <button class="btn btn-primary" type="submit">Gönder</button>
        </form>
        """,
    )

# Ayrı FastAPI route (POST)
@app.post("/mc/send")
async def mc_send(request: Request):
    form = await request.form()
    cmd = form.get("cmd", "")
    execute_mc_command(cmd)   # kendi fonksiyonun
    return RedirectResponse(f"{admin.prefix}/pages/websender", status_code=303)
```

---

## 6. HTML Yardımcıları (admin.html.*)

Custom sayfa fonksiyonlarında admin layout'una uyumlu HTML üretmek için:

### `admin.html.page()`

```python
return admin.html.page(
    title="Sayfa Başlığı",
    subtitle="Alt başlık",                      # isteğe bağlı
    actions=admin.html.button("Yeni", href="/new", icon="bolt"),  # isteğe bağlı
    content="<p>Buraya içerik</p>",
)
```

### `admin.html.stat_card()`

```python
admin.html.stat_card(
    "Toplam Kullanıcı",   # etiket
    "1,284",              # değer (int veya str)
    icon="users",         # ikon
    color="#6366f1",      # hex renk
    link="/admin/user",   # isteğe bağlı link
)
```

### `admin.html.stats_row()`

```python
admin.html.stats_row(
    admin.html.stat_card("A", 10, color="#6366f1"),
    admin.html.stat_card("B", 20, color="#22c55e"),
    admin.html.stat_card("C", 30, color="#f59e0b"),
)
```

### `admin.html.table()`

```python
admin.html.table(
    headers=["Ad", "E-posta", "Durum"],
    rows=[
        ["Alice", "alice@example.com", admin.html.badge("Aktif", color="green")],
        ["Bob",   "bob@example.com",   admin.html.badge("Pasif", color="red")],
    ],
    empty_msg="Kayıt bulunamadı.",
)
```

### `admin.html.alert()`

```python
admin.html.alert("Kayıt başarıyla güncellendi!", kind="success")
admin.html.alert("Bağlantı hatası.", kind="error")
admin.html.alert("Bu alan yakında kaldırılacak.", kind="warning")
admin.html.alert("Daha fazla bilgi için belgeye bak.", kind="info")
```

### `admin.html.card()`

```python
admin.html.card("<p>Kart içeriği</p>", padding=True)
```

### `admin.html.button()`

```python
admin.html.button("Yeni Ekle", href="/admin/user/new", kind="primary", icon="bolt")
admin.html.button("İptal",     href="/admin/user",     kind="secondary")
admin.html.button("Sil",       href="/admin/user/1/delete", kind="danger")
```

### `admin.html.badge()`

```python
admin.html.badge("Online",  color="green")
admin.html.badge("Offline", color="red")
admin.html.badge("Bekliyor", color="gray")
```

---

## 7. Gerçek Dünya Örnekleri

### Minecraft Sunucu Paneli

```python
import subprocess

def mc_rcon(cmd: str) -> str:
    """mcrcon ile sunucuya komut gönder."""
    result = subprocess.run(
        ["mcrcon", "-H", "localhost", "-P", "25575", "-p", "rcon_pass", cmd],
        capture_output=True, text=True
    )
    return result.stdout.strip()

@admin.page("minecraft", label="Minecraft", icon="server")
async def minecraft_page(request):
    players = mc_rcon("list")
    return admin.html.page(
        title="Minecraft Server",
        actions=admin.html.button("Restart", href="/mc/restart", kind="danger", icon="bolt"),
        content=admin.html.card(f"<pre>{players}</pre>"),
    )
```

### Discord Bot Durumu

```python
import httpx

@admin.page("discord", label="Discord Bot", icon="bolt")
async def discord_page(request):
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:8080/bot/status")
        data = r.json()

    return admin.html.page(
        title="Discord Bot",
        content=admin.html.stats_row(
            admin.html.stat_card("Sunucular", data["guilds"], icon="users", color="#5865F2"),
            admin.html.stat_card("Ping", f"{data['ping']}ms", icon="bolt", color="#22c55e"),
        ),
    )
```

### Uygulama Logu Görüntüleme

```python
@admin.page("logs", label="Uygulama Logları", icon="terminal")
async def logs_page(request):
    lines = open("app.log").readlines()[-50:]  # son 50 satır
    log_html = "".join(f"<div>{line}</div>" for line in lines)

    return admin.html.page(
        title="Uygulama Logları",
        content=admin.html.card(
            f'<pre style="font-size:12px;color:#94a3b8;background:#0f172a;'
            f'padding:16px;border-radius:8px;overflow-x:auto;">{log_html}</pre>',
            padding=False,
        ),
    )
```

### Sayfa İçinde Jinja2 Şablonu

Kendi `.html` dosyalarını da kullanabilirsin:

```python
from jinja2 import Environment, FileSystemLoader

_env = Environment(loader=FileSystemLoader("templates/"))

@admin.page("report", label="Rapor", icon="chart")
async def report_page(request):
    data = get_report_data()
    html = _env.get_template("report.html").render(data=data, request=request)
    return html
```

---

## 8. Kimlik Doğrulama

### Auth Kapalı (Geliştirme Ortamı)

```python
admin = AdminSite(app=app, engine=engine)   # username/password yok
```

### Auth Açık (Üretim)

```python
import os

admin = AdminSite(
    app=app,
    engine=engine,
    username=os.environ["ADMIN_USER"],
    password=os.environ["ADMIN_PASS"],
    secret_key=os.environ["ADMIN_SECRET"],
)
```

### Mevcut FastAPI Auth ile Entegrasyon

Kendi middleware'ini kullanmak istiyorsan, custom sayfanda `request` objesine eklenen bilgilere erişebilirsin:

```python
@admin.page("secure", label="Güvenli Sayfa")
async def secure_page(request):
    # request.state, request.headers, request.cookies — hepsi mevcut
    user = request.state.user   # kendi auth middleware'inden gelen
    return admin.html.page(title=f"Merhaba {user.name}")
```
