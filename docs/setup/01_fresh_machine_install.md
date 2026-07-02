# Fresh Machine Installation

## 1. Unzip Package

```bash
unzip Part12_2_Installation_Operations_Guide_Package.zip
cd iperform-insights-coaching
```

## 2. Create Environment File

```bash
cp .env.example .env
```

Windows:

```powershell
copy .env.example .env
```

## 3. Install Dependencies

```bash
uv sync
```

## 4. Run Final Smoke Test

```bash
uv run python scripts/final_smoke_test.py
```

## 5. Run Graph Access Validation

```bash
uv run python scripts/validate_graph_access.py
```

## 6. Run Full Demo

```bash
uv run python scripts/run_full_demo.py
```

## 7. Start API

```bash
uv run python run_local_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 8. Start Streamlit

Open a second terminal:

```bash
uv run streamlit run app/ui/app_enterprise.py
```
