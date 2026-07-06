from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="iPerform Insights & Coaching", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_version: str = Field(default="11.0.1", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Structured logging / CloudWatch-ready sink (see app/shared/logging.py docstring) ---
    # log_sink selects WHERE structured JSON logs go, so switching for ECS/Fargate is a
    # config change, not a code change:
    #   file       → RotatingFileHandler to logs/app.log (local default)
    #   stdout     → structured JSON to stdout (Fargate ships stdout straight to CloudWatch)
    #   cloudwatch → watchtower CloudWatchLogHandler (falls back to stdout if unavailable)
    log_sink: str = Field(default="file", alias="LOG_SINK")  # file | stdout | cloudwatch
    log_json: bool = Field(default=True, alias="LOG_JSON")  # JSON when true; human console when false
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    log_file_name: str = Field(default="app.log", alias="LOG_FILE_NAME")
    log_rotate_max_bytes: int = Field(default=10_485_760, alias="LOG_ROTATE_MAX_BYTES")  # 10 MB
    log_rotate_backup_count: int = Field(default=5, alias="LOG_ROTATE_BACKUP_COUNT")
    # CloudWatch (log_sink=cloudwatch) — used only by the watchtower handler.
    log_cloudwatch_group: str = Field(default="/iperform/insights-coaching", alias="LOG_CLOUDWATCH_GROUP")
    log_cloudwatch_stream: str | None = Field(default=None, alias="LOG_CLOUDWATCH_STREAM")
    aws_region: str | None = Field(default=None, alias="AWS_REGION")
    # Register the deliberate-error diagnostics route (/_diagnostics/*). Kept out of prod.
    enable_diagnostics_routes: bool = Field(default=True, alias="ENABLE_DIAGNOSTICS_ROUTES")

    # Adapter selection (Section 2 of the rebuild brief)
    graph_client_mode: str = Field(default="mock", alias="GRAPH_CLIENT_MODE")  # mock | local_real | real
    llm_client_mode: str = Field(default="mock", alias="LLM_CLIENT_MODE")  # mock | claude | real
    embedding_client_mode: str = Field(default="local", alias="EMBEDDING_CLIENT_MODE")  # local | azure
    local_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="LOCAL_EMBEDDING_MODEL"
    )

    # Section 11.1: real model tier (ModelClient) + graph-entity vector storage (VectorClient).
    # Defaults keep the verified deterministic scorers/vectors as the working path; `real`/
    # `tigergraph` are opt-in and always fall back to deterministic when no artifact/engine.
    model_client_mode: str = Field(default="deterministic", alias="MODEL_CLIENT_MODE")  # deterministic | real
    vector_client_mode: str = Field(default="local", alias="VECTOR_CLIENT_MODE")  # local | tigergraph
    ml_artifacts_dir: str = Field(default="models/artifacts", alias="ML_ARTIFACTS_DIR")
    ml_time_box_minutes: int = Field(default=10, alias="ML_TIME_BOX_MINUTES")
    # Section 11.3: apply the outcome-driven-learning affinity as a bounded ±10% confidence
    # modifier on recommendations (evidence is always attached regardless). Priority ranking
    # stays owned by the bandit weight alone.
    fl_affinity_in_confidence: bool = Field(default=True, alias="FL_AFFINITY_IN_CONFIDENCE")

    # Section 11.6: context ranking (rerank) + scope-aware assembly.
    rerank_client_mode: str = Field(default="local", alias="RERANK_CLIENT_MODE")  # local | cohere
    cohere_api_key: str | None = Field(default=None, alias="COHERE_API_KEY")
    cohere_rerank_model: str = Field(default="rerank-english-v3.0", alias="COHERE_RERANK_MODEL")
    context_rerank_top_k: int = Field(default=8, alias="CONTEXT_RERANK_TOP_K")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="gpt-4o-mini", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-3-small", alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    )
    azure_openai_api_version: str = Field(default="2024-06-01", alias="AZURE_OPENAI_API_VERSION")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL")

    tigergraph_host: str | None = Field(default=None, alias="TIGERGRAPH_HOST")
    tigergraph_username: str | None = Field(default=None, alias="TIGERGRAPH_USERNAME")
    tigergraph_password: str | None = Field(default=None, alias="TIGERGRAPH_PASSWORD")
    tigergraph_secret: str | None = Field(default=None, alias="TIGERGRAPH_SECRET")
    tigergraph_token: str | None = Field(default=None, alias="TIGERGRAPH_TOKEN")
    tigergraph_graph: str = Field(default="iperform_insights_coaching_demo", alias="TIGERGRAPH_GRAPH")
    tigergraph_schema_prefix: str = Field(default="phx_dm_", alias="TIGERGRAPH_SCHEMA_PREFIX")
    tigergraph_restpp_url: str = Field(default="http://localhost:14240/restpp", alias="TIGERGRAPH_RESTPP_URL")
    tigergraph_verify_ssl: bool = Field(default=True, alias="TIGERGRAPH_VERIFY_SSL")
    tigergraph_timeout_seconds: int = Field(default=120, alias="TIGERGRAPH_TIMEOUT_SECONDS")
    graph_load_batch_size: int = Field(default=500, alias="GRAPH_LOAD_BATCH_SIZE")

    # TigerGraph Foundation package (Section 3 — source of truth for schema/data/queries)
    foundation_dir: str = Field(default="docs/tigergraph_foundation", alias="FOUNDATION_DIR")

    # --- Section 9.4: 4-tier GraphClient adapter (MCP → pyTigerGraph → RESTPP → mock) ---
    # TG_* vars use the official tigergraph-mcp naming so the same env drives both the
    # MCP server subprocess (Tier 1) and the direct pyTigerGraph connection (Tier 2).
    # Defaults are mock-friendly: with no live TigerGraph the chain falls to Tier 4.
    tg_host: str = Field(default="http://127.0.0.1", alias="TG_HOST")
    tg_graphname: str | None = Field(default=None, alias="TG_GRAPHNAME")  # None → TIGERGRAPH_GRAPH
    tg_username: str = Field(default="tigergraph", alias="TG_USERNAME")
    tg_password: str = Field(default="tigergraph", alias="TG_PASSWORD")
    tg_api_token: str | None = Field(default=None, alias="TG_API_TOKEN")
    tg_restpp_port: int = Field(default=9000, alias="TG_RESTPP_PORT")
    tg_gs_port: int = Field(default=14240, alias="TG_GS_PORT")
    # Tier-1 MCP server subprocess (stdio); see TIGERGRAPH_MCP_COMMAND/ARGS in
    # tigergraph_mcp_stdio_client.py (read via os.getenv for subprocess spawning).
    graph_tier_cooldown_seconds: int = Field(default=60, alias="GRAPH_TIER_COOLDOWN_SECONDS")
    graph_tier_probe_timeout_seconds: int = Field(default=10, alias="GRAPH_TIER_PROBE_TIMEOUT_SECONDS")

    # TigerGraph MCP-first graph access
    graph_access_strategy: str = "mcp_rest_mock"
    tigergraph_mcp_url: str = ""
    tigergraph_mcp_transport: str = "http"
    tigergraph_mcp_api_key: str = ""
    tigergraph_mcp_auth_header: str = "Authorization"
    tigergraph_mcp_auth_scheme: str = "Bearer"
    tigergraph_mcp_timeout_seconds: int = 30
    tigergraph_mcp_tool_health_check: str = "health_check"
    tigergraph_mcp_tool_query_graph: str = "query_graph"
    tigergraph_mcp_tool_run_installed_query: str = "run_installed_query"
    tigergraph_mcp_tool_upsert_vertex: str = "upsert_vertex"
    tigergraph_mcp_tool_upsert_edge: str = "upsert_edge"
    tigergraph_mcp_tool_run_gsql: str = "run_gsql"
    tigergraph_mcp_tool_get_schema: str = "get_schema"

    # TigerGraph MCP library-based integration
    tigergraph_mcp_client_mode: str = "streamable_http"
    tigergraph_mcp_stdio_command: str = "python"
    tigergraph_mcp_stdio_args: str = "-m,tigergraph_mcp"
    tigergraph_mcp_use_library_client: bool = True
    tigergraph_mcp_list_tools_on_health: bool = True


    tigergraph_mcp_url: str | None = Field(default=None, alias="TIGERGRAPH_MCP_URL")
    tigergraph_mcp_token: str | None = Field(default=None, alias="TIGERGRAPH_MCP_TOKEN")
    tigergraph_rest_timeout_seconds: int = Field(default=30, alias="TIGERGRAPH_REST_TIMEOUT_SECONDS")

    sqlite_db_path: str = Field(default="./data/feature_store/iperform_features.db", alias="SQLITE_DB_PATH")
    chroma_path: str = Field(default="./data/chroma", alias="CHROMA_PATH")
    uploads_path: str = Field(default="./data/uploads", alias="UPLOADS_PATH")
    checkpoints_path: str = Field(default="./data/checkpoints", alias="CHECKPOINTS_PATH")
    exports_path: str = Field(default="./data/exports", alias="EXPORTS_PATH")
    documents_path: str = Field(default="./data/documents", alias="DOCUMENTS_PATH")

    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_base_url: str = Field(default="http://127.0.0.1:8000", alias="API_BASE_URL")
    streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")

    enable_openai: bool = Field(default=True, alias="ENABLE_OPENAI")
    enable_chroma: bool = Field(default=True, alias="ENABLE_CHROMA")
    enable_tigergraph_mcp: bool = Field(default=True, alias="ENABLE_TIGERGRAPH_MCP")
    enable_tigergraph_rest_fallback: bool = Field(default=True, alias="ENABLE_TIGERGRAPH_REST_FALLBACK")
    enable_local_mock_fallback: bool = Field(default=True, alias="ENABLE_LOCAL_MOCK_FALLBACK")

    def ensure_local_directories(self) -> None:
        for path in [
            self.sqlite_db_path,
            self.chroma_path,
            self.uploads_path,
            self.checkpoints_path,
            self.exports_path,
            self.documents_path,
        ]:
            candidate = Path(path)
            if candidate.suffix:
                candidate.parent.mkdir(parents=True, exist_ok=True)
            else:
                candidate.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_local_directories()
    return settings
