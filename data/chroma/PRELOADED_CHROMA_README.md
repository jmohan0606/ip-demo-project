# Preloaded Chroma Directory

This folder is included so the package ships with a physical Chroma location.

The local application can rebuild real Chroma collections by running:

```bash
uv run python scripts/preload_demo_databases.py
```

In environments where `chromadb` is installed, the script will create persistent Chroma collections here. The manifest and lightweight JSON index are included for immediate validation and fallback.
