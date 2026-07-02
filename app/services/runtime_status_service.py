from __future__ import annotations
from app.config.constants import GRAPH_NAME, SCHEMA_PREFIX
from app.config.settings import get_settings
from app.feature_store.sqlite_manager import SQLiteManager
from app.graph.tigergraph.mcp_client import TigerGraphMcpClient
from app.graph.tigergraph.rest_client import TigerGraphRestClient
from app.models.enums import RuntimeComponentStatus
from app.models.runtime import ComponentHealth, RuntimeHealthReport

class RuntimeStatusService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _sqlite_health(self) -> ComponentHealth:
        try:
            SQLiteManager().initialize_foundation_tables()
            return ComponentHealth(component_name="SQLite Feature Store", status=RuntimeComponentStatus.HEALTHY, configured=True, detail=self.settings.sqlite_db_path)
        except Exception as exc:
            return ComponentHealth(component_name="SQLite Feature Store", status=RuntimeComponentStatus.ERROR, configured=True, detail=str(exc))

    def _chroma_health(self) -> ComponentHealth:
        if not self.settings.enable_chroma:
            return ComponentHealth(component_name="Chroma Knowledge Store", status=RuntimeComponentStatus.UNCONFIGURED, configured=False, detail="ENABLE_CHROMA=false")
        try:
            self.settings.ensure_local_directories()
            return ComponentHealth(component_name="Chroma Knowledge Store", status=RuntimeComponentStatus.HEALTHY, configured=True, detail=self.settings.chroma_path)
        except Exception as exc:
            return ComponentHealth(component_name="Chroma Knowledge Store", status=RuntimeComponentStatus.ERROR, configured=True, detail=str(exc))

    def _openai_health(self) -> ComponentHealth:
        if self.settings.openai_api_key and self.settings.enable_openai:
            return ComponentHealth(component_name="OpenAI Adapter", status=RuntimeComponentStatus.HEALTHY, configured=True, detail=f"model={self.settings.openai_model}")
        return ComponentHealth(component_name="OpenAI Adapter", status=RuntimeComponentStatus.UNCONFIGURED, configured=False, detail="OPENAI_API_KEY not configured; MockModelAdapter fallback will be used.")

    def _mcp_health(self) -> ComponentHealth:
        client = TigerGraphMcpClient()
        if client.is_configured() and self.settings.enable_tigergraph_mcp:
            return ComponentHealth(component_name="TigerGraph MCP", status=RuntimeComponentStatus.HEALTHY, configured=True, detail=self.settings.tigergraph_mcp_url)
        return ComponentHealth(component_name="TigerGraph MCP", status=RuntimeComponentStatus.UNCONFIGURED, configured=False, detail="TIGERGRAPH_MCP_URL not configured.")

    def _rest_health(self) -> ComponentHealth:
        client = TigerGraphRestClient()
        if client.is_configured() and self.settings.enable_tigergraph_rest_fallback:
            return ComponentHealth(component_name="TigerGraph REST Fallback", status=RuntimeComponentStatus.HEALTHY, configured=True, detail=self.settings.tigergraph_host)
        return ComponentHealth(component_name="TigerGraph REST Fallback", status=RuntimeComponentStatus.UNCONFIGURED, configured=False, detail="TIGERGRAPH_HOST not configured.")

    def get_health_report(self) -> RuntimeHealthReport:
        components = [self._sqlite_health(), self._chroma_health(), self._openai_health(), self._mcp_health(), self._rest_health()]
        if any(c.status == RuntimeComponentStatus.ERROR for c in components):
            overall = RuntimeComponentStatus.ERROR
        elif any(c.status == RuntimeComponentStatus.UNCONFIGURED for c in components):
            overall = RuntimeComponentStatus.DEGRADED
        else:
            overall = RuntimeComponentStatus.HEALTHY
        return RuntimeHealthReport(
            application=self.settings.app_name,
            version=self.settings.app_version,
            environment=self.settings.app_env,
            graph_name=GRAPH_NAME,
            schema_prefix=SCHEMA_PREFIX,
            overall_status=overall,
            components=components,
        )
