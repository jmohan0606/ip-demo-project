from __future__ import annotations
from app.api.routers.llm_activation import router as llm_activation_router
from app.api.routers.tigergraph_activation import router as tigergraph_activation_router
from app.api.routers.memory_runtime import router as memory_runtime_router
from app.api.routers.recommendation_runtime import router as recommendation_runtime_router
from app.api.routers.feature_runtime import router as feature_runtime_router
from app.api.routers.knowledge_runtime import router as knowledge_runtime_router
from app.api.routers.graph_runtime import router as graph_runtime_router
from app.api.routers.orchestration import router as orchestration_router
from app.api.routers.ui_integrated_expanded import router as ui_integrated_expanded_router
from app.api.routers.ui_integrated import router as ui_integrated_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.middleware.error_handlers import register_exception_handlers
from app.api.routers.adapters import router as adapters_router
from app.api.routers.config import router as config_router
from app.api.routers.health import router as health_router
from app.api.routers.manifest import router as manifest_router
from app.config.constants import GRAPH_NAME, SCHEMA_PREFIX
from app.config.settings import get_settings
from app.models.common import HealthResponse
from app.shared.logging import configure_logging
from app.api.routers.config_status import router as config_status_router
from app.api.routers.agentic_ai import router as agentic_ai_router
from app.api.routers.graph_access import router as graph_access_router
from app.api.routers.ai_chat import router as ai_chat_router
from app.api.routers.insights_coaching import router as insights_coaching_router
from app.api.routers.feedback_learning import router as feedback_learning_router
from app.api.routers.recommendations import router as recommendations_router
from app.api.routers.opportunities import router as opportunities_router
from app.api.routers.predictions import router as predictions_router
from app.api.routers.embeddings import router as embeddings_router
from app.api.routers.features import router as features_router
from app.api.routers.memory import router as memory_router
from app.api.routers.knowledge import router as knowledge_router
from app.api.routers.ingestion import router as ingestion_router
from app.api.routers.tigergraph_foundation import router as tigergraph_foundation_router
configure_logging(); settings=get_settings()
app=FastAPI(title=settings.app_name, version=settings.app_version, description='Local enterprise demo API for iPerform Insights & Coaching')
register_exception_handlers(app)
@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok', app_name=settings.app_name, app_version=settings.app_version, environment=settings.app_env, graph_name=GRAPH_NAME, schema_prefix=SCHEMA_PREFIX)
app.include_router(health_router)
app.include_router(config_router)
app.include_router(adapters_router)
app.include_router(manifest_router)

app.include_router(tigergraph_foundation_router)


app.include_router(ingestion_router)

app.include_router(knowledge_router)

app.include_router(memory_router)

app.include_router(features_router)

app.include_router(embeddings_router)

app.include_router(predictions_router)

app.include_router(opportunities_router)

app.include_router(recommendations_router)

app.include_router(feedback_learning_router)

app.include_router(insights_coaching_router)

app.include_router(ai_chat_router)


app.include_router(graph_access_router)

app.include_router(agentic_ai_router)



app.include_router(config_status_router)
app.include_router(ui_integrated_router)
app.include_router(ui_integrated_expanded_router)
app.include_router(orchestration_router)
app.include_router(graph_runtime_router)
app.include_router(knowledge_runtime_router)
app.include_router(feature_runtime_router)
app.include_router(recommendation_runtime_router)
app.include_router(memory_runtime_router)
app.include_router(tigergraph_activation_router)
app.include_router(llm_activation_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://127.0.0.1:3000","http://localhost:3001","http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
