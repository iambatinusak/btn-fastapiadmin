"""
fastapiadmin — örnek uygulama
Çalıştırmak için:
    pip install fastapi uvicorn sqlalchemy python-multipart itsdangerous jinja2
    uvicorn example.main:app --reload
Ardından http://localhost:8000/admin adresine gidin.
"""
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from fastapiadmin import AdminSite, ModelAdmin

# ── Database ──────────────────────────────────────────────────────────────────

engine = create_engine("sqlite:///./demo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    stock = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)

    def __str__(self):
        return self.name


class BlogPost(Base):
    __tablename__ = "blog_posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    slug = Column(String(300), nullable=False)
    content = Column(Text, nullable=True)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __str__(self):
        return self.title


Base.metadata.create_all(bind=engine)

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="fastapiadmin Demo")

# ── Admin panel ───────────────────────────────────────────────────────────────

admin = AdminSite(
    app=app,
    engine=engine,
    title="My App",
    prefix="/admin",
    username="admin",
    password="admin123",
    brand_color="#6366f1",       # indigo — istediğiniz hex rengi yazabilirsiniz
    secret_key="super-secret-key-change-in-production",
)


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ["id", "name", "email", "is_active", "created_at"]
    search_fields = ["name", "email"]
    readonly_fields = ["created_at"]
    per_page = 15


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ["id", "name", "price", "stock", "is_available"]
    search_fields = ["name"]
    per_page = 20


@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin):
    list_display = ["id", "title", "slug", "published", "created_at"]
    search_fields = ["title", "slug"]
    readonly_fields = ["created_at"]


# ── Seed data (first run only) ────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([
                User(name="Alice Johnson", email="alice@example.com", bio="Backend engineer.", is_active=True),
                User(name="Bob Smith", email="bob@example.com", bio="Frontend dev.", is_active=True),
                User(name="Carol White", email="carol@example.com", is_active=False),
            ])
        if db.query(Product).count() == 0:
            db.add_all([
                Product(name="Wireless Keyboard", price=79.99, stock=42, is_available=True),
                Product(name="USB-C Hub", price=49.99, stock=18, is_available=True),
                Product(name="Webcam HD", price=129.00, stock=0, is_available=False),
            ])
        if db.query(BlogPost).count() == 0:
            db.add_all([
                BlogPost(title="Getting Started", slug="getting-started",
                         content="Welcome to the blog!", published=True),
                BlogPost(title="Draft Post", slug="draft-post",
                         content="Work in progress...", published=False),
            ])
        db.commit()
    finally:
        db.close()


seed()


# ── Custom pages ──────────────────────────────────────────────────────────────

@admin.page("minecraft", label="Minecraft Server", icon="server")
async def minecraft_page(request):
    """Demo: Minecraft sunucu yönetim paneli."""
    import random
    players = random.randint(0, 20)
    tps = round(random.uniform(18.5, 20.0), 1)
    uptime = "3d 14h 22m"

    return admin.html.page(
        title="Minecraft Server",
        subtitle="SurvivalCraft — play.example.com:25565",
        actions=admin.html.button("Restart Server", href="#", kind="danger", icon="bolt"),
        content=admin.html.stats_row(
            admin.html.stat_card("Players Online", f"{players}/20", icon="users", color="#22c55e"),
            admin.html.stat_card("TPS", tps, icon="bolt", color="#f59e0b"),
            admin.html.stat_card("Uptime", uptime, icon="server", color="#6366f1"),
            admin.html.stat_card("RAM Usage", "1.8 GB", icon="chart", color="#0ea5e9"),
        ) + admin.html.table(
            headers=["Player", "Status", "Joined", "Playtime"],
            rows=[
                ["Notch", admin.html.badge("Online", color="green"), "2024-01-15", "1,203h"],
                ["jeb_", admin.html.badge("Online", color="green"), "2024-02-03", "874h"],
                ["Herobrine", admin.html.badge("Offline", color="red"), "2023-11-20", "42h"],
            ],
        ),
    )


@admin.page("websender", label="WebSender", icon="terminal")
async def websender_page(request):
    """Demo: Sunucuya komut gönderme arayüzü."""
    return admin.html.page(
        title="WebSender",
        subtitle="Minecraft sunucusuna komut gönder",
        content=admin.html.alert(
            "⚡ WebSender aktif — komutlar anında işlenir.",
            kind="info",
        ) + admin.html.card("""
            <div class="form-group">
                <label class="form-label">Komut</label>
                <div style="display:flex;gap:8px;">
                    <input class="form-control" type="text" placeholder="/say Merhaba dünya!"
                           id="cmd-input" style="font-family:monospace;"/>
                    <button class="btn btn-primary" onclick="sendCmd()">Gönder</button>
                </div>
                <div class="form-hint">Örnek: /give @a diamond 64 &nbsp;|&nbsp; /time set day &nbsp;|&nbsp; /weather clear</div>
            </div>
            <div class="form-group" style="margin-top:16px;">
                <label class="form-label">Konsol Çıktısı</label>
                <div id="console-out" style="background:#0f172a;color:#94a3b8;padding:14px 16px;
                     border-radius:8px;font-family:monospace;font-size:12.5px;min-height:160px;
                     max-height:320px;overflow-y:auto;line-height:1.8;">
                    <span style="color:#22c55e;">[INFO]</span> Server started on port 25565<br>
                    <span style="color:#22c55e;">[INFO]</span> Notch joined the game<br>
                    <span style="color:#f59e0b;">[WARN]</span> Can't keep up! Did the system time change?<br>
                </div>
            </div>
            <script>
            function sendCmd() {
                const cmd = document.getElementById('cmd-input').value.trim();
                if (!cmd) return;
                const out = document.getElementById('console-out');
                out.innerHTML += '<span style="color:#6366f1;">[CMD]</span> ' + cmd + '<br>';
                out.scrollTop = out.scrollHeight;
                document.getElementById('cmd-input').value = '';
            }
            document.getElementById('cmd-input')?.addEventListener('keydown', e => {
                if (e.key === 'Enter') sendCmd();
            });
            </script>
        """),
    )


@admin.page("analytics", label="Analytics", icon="chart")
async def analytics_page(request):
    """Demo: Basit istatistik sayfası."""
    return admin.html.page(
        title="Analytics",
        subtitle="Son 30 günün özeti",
        content=admin.html.stats_row(
            admin.html.stat_card("Toplam Kullanıcı", "1,284", icon="users", color="#6366f1"),
            admin.html.stat_card("Aktif Oturum", "47", icon="bolt", color="#22c55e"),
            admin.html.stat_card("Hata Oranı", "0.3%", icon="chart", color="#ef4444"),
            admin.html.stat_card("Ort. Yanıt", "142ms", icon="globe", color="#0ea5e9"),
        ) + admin.html.alert(
            "Bu sayfa bir demo. Gerçek veriyi buraya bağlayabilirsiniz.",
            kind="warning",
        ),
    )


@app.get("/")
def root():
    return {"message": "API running. Visit /admin for the admin panel."}
