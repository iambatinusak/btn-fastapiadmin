# PyPI'ye Yükleme Rehberi

Bu belge `fastapiadmin` paketini PyPI'ye yüklemek için gereken adımları açıklar.

---

## Ön Hazırlık

### 1. Araçları Kur

```bash
pip install build twine
```

- **build** → `pyproject.toml`'dan paket oluşturur
- **twine** → PyPI'ye yükler

### 2. PyPI Hesabı Aç

→ https://pypi.org/account/register/

Test için (ücretiz, güvenli):
→ https://test.pypi.org/account/register/

### 3. API Token Oluştur

PyPI'de **Account Settings → API Tokens → Add API Token** yolunu izle.

Token'ı `~/.pypirc` dosyasına kaydet:

```ini
[pypi]
  username = __token__
  password = pypi-AgEIcHlwaS5vcmcA...   ← token buraya

[testpypi]
  username = __token__
  password = pypi-AgENdGVzdC5weXBpLm9...
```

---

## Yükleme Adımları

### Adım 1 — Versiyon Numarasını Güncelle

`pyproject.toml` içinde:
```toml
[project]
version = "0.2.0"   # her sürümde artır
```

`fastapiadmin/__init__.py` içinde:
```python
__version__ = "0.2.0"
```

### Adım 2 — Paketin Temizlenmesi

```bash
# Eski build çıktılarını sil
rm -rf dist/ build/ *.egg-info
```

Windows PowerShell:
```powershell
Remove-Item -Recurse -Force dist, build, fastapiadmin.egg-info -ErrorAction SilentlyContinue
```

### Adım 3 — Paketi Derle

```bash
python -m build
```

Bu komut `dist/` klasörüne iki dosya oluşturur:
```
dist/
  fastapiadmin-0.2.0-py3-none-any.whl   ← wheel (tercih edilen)
  fastapiadmin-0.2.0.tar.gz             ← source archive
```

### Adım 4 — Önce Test PyPI'ye Yükle (tavsiye edilir)

```bash
twine upload --repository testpypi dist/*
```

Test et:
```bash
pip install --index-url https://test.pypi.org/simple/ fastapiadmin
```

### Adım 5 — Gerçek PyPI'ye Yükle

```bash
twine upload dist/*
```

Artık herkes şununla kurabilir:
```bash
pip install fastapiadmin
```

---

## Versiyon Stratejisi

[Semantic Versioning](https://semver.org/) önerilir: `MAJOR.MINOR.PATCH`

| Değişiklik | Örnek | Versiyon Artışı |
|------------|-------|-----------------|
| Bug fix | Login hatası düzeltme | `0.1.0` → `0.1.1` |
| Yeni özellik | Custom sayfa desteği | `0.1.1` → `0.2.0` |
| Breaking change | API kırılması | `0.2.0` → `1.0.0` |

---

## `pyproject.toml` Kontrol Listesi

PyPI'ye yüklemeden önce şunları doldur:

```toml
[project]
name = "fastapiadmin"           # pip'te görünecek isim (benzersiz olmalı!)
version = "0.1.0"
description = "A beautiful, minimal admin panel for FastAPI + SQLAlchemy"
readme = "README.md"            # PyPI sayfasında gösterilir
license = { text = "MIT" }
authors = [
    { name = "Adın", email = "email@ornek.com" }
]
keywords = ["fastapi", "admin", "sqlalchemy", "panel", "crud"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: FastAPI",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "License :: OSI Approved :: MIT License",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
]
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0",
    "sqlalchemy>=2.0.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.6",
    "itsdangerous>=2.1.0",
]

[project.urls]
Homepage = "https://github.com/kullanici_adi/fastapiadmin"
Repository = "https://github.com/kullanici_adi/fastapiadmin"
Documentation = "https://github.com/kullanici_adi/fastapiadmin/blob/main/USAGE.md"
"Bug Tracker" = "https://github.com/kullanici_adi/fastapiadmin/issues"
```

---

## GitHub Actions ile Otomatik Yayın (isteğe bağlı)

`.github/workflows/publish.yml` dosyası oluştur:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"          # v0.2.0 gibi bir tag push'layınca tetiklenir

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build
        run: |
          pip install build
          python -m build

      - name: Publish
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

**GitHub repo'da Secrets ekle:**
`Settings → Secrets → Actions → New secret`
- İsim: `PYPI_API_TOKEN`
- Değer: PyPI'den aldığın token

**Release nasıl yapılır:**
```bash
git tag v0.2.0
git push origin v0.2.0
```

GitHub Actions otomatik olarak paketi PyPI'ye yükler.

---

## Paket İsmi Çakışması

`fastapiadmin` ismi zaten alınmışsa alternatifler:
```
fastapi-admin-panel
fastapi-minimal-admin
myadmin-fastapi
fastadmin-ui
```

Kontrol et: https://pypi.org/search/?q=fastapiadmin

---

## Tam Yükleme Özeti

```bash
# 1. Versiyon artır (pyproject.toml + __init__.py)

# 2. Temizle
rm -rf dist/ build/ *.egg-info

# 3. Derle
python -m build

# 4. Test PyPI (isteğe bağlı)
twine upload --repository testpypi dist/*

# 5. Yayınla
twine upload dist/*
```

---

## Sorun Giderme

**`HTTPError: 400 File already exists`**
→ Aynı versiyon zaten yüklenmiş. Versiyon numarasını artır.

**`Invalid distribution file`**
→ `dist/` klasörünü temizle ve `python -m build` ile yeniden derle.

**`twine: command not found`**
→ `pip install twine` komutunu çalıştır.

**`403 Forbidden`**
→ `~/.pypirc` içindeki token'ı kontrol et. Token `__token__` prefix ile başlamalı.
