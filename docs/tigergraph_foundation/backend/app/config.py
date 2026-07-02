from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "iPerform TigerGraph Foundation"
    app_env: str = "local"
    graph_name: str = "iperform_insights_coaching_demo"
    tigergraph_restpp_url: str = "http://localhost:14240/restpp"
    tigergraph_token: str = ""
    tigergraph_verify_ssl: bool = True
    tigergraph_timeout_seconds: int = 120
    sample_data_dir: str = str(BASE_DIR / "data" / "sample")
    manifest_path: str = str(BASE_DIR / "data" / "manifest.json")
    schema_catalog_path: str = str(BASE_DIR / "tigergraph" / "schema" / "schema_catalog.json")
    query_catalog_path: str = str(BASE_DIR / "tigergraph" / "queries" / "query_catalog.json")
    query_cases_path: str = str(BASE_DIR / "tests" / "query_cases.json")
    tracker_db_path: str = str(BASE_DIR / "runtime" / "ingestion_tracker.db")
    load_batch_size: int = 500
    mock_tigergraph: bool = False
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def restpp_url(self) -> str:
        value = self.tigergraph_restpp_url.rstrip("/")
        return value if value.endswith("/restpp") else value + "/restpp"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
