# Quick Start

## 1. Unzip

```bash
unzip Part11_16_Final_Consolidated_Delivery_Package.zip
cd iperform-insights-coaching
```

## 2. Install dependencies

```bash
uv sync
```

## 3. Validate the package

```bash
uv run python scripts/final_smoke_test.py
```

## 4. Run full demo pipeline

```bash
uv run python scripts/run_full_demo.py
```

## 5. Run FastAPI

```bash
uv run python run_local_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 6. Run Streamlit UI

```bash
uv run streamlit run app/ui/app_enterprise.py
```

## Recommended Demo Flow

1. End-to-End Demo Run
2. Executive Dashboard
3. Advisor 360
4. AGP Goals & Coaching
5. Recommendations
6. Feedback Learning
7. AI Assistant Chat
8. Context Memory
9. Knowledge Management
10. Data Ingestion & Sync
