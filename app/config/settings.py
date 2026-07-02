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

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")

    tigergraph_host: str | None = Field(default=None, alias="TIGERGRAPH_HOST")
    tigergraph_username: str | None = Field(default=None, alias="TIGERGRAPH_USERNAME")
    tigergraph_password: str | None = Field(default=None, alias="TIGERGRAPH_PASSWORD")
    tigergraph_secret: str | None = Field(default=None, alias="TIGERGRAPH_SECRET")
    tigergraph_token: str | None = Field(default=None, alias="TIGERGRAPH_TOKEN")
    tigergraph_graph: str = Field(default="iperform_insights_coaching_demo", alias="TIGERGRAPH_GRAPH")
    tigergraph_schema_prefix: str = Field(default="phx_dm_", alias="TIGERGRAPH_SCHEMA_PREFIX")

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
