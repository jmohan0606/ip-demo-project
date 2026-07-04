from __future__ import annotations

from app.models.ingestion import IngestionEntityConfig


# NOTE: csv_file_name resolves under IngestionService.sample_data_dir, which points
# at the verified TigerGraph Foundation vertex CSVs (docs/tigergraph_foundation/
# data/sample/vertices — the same 60-advisor dataset the graph store loads).
# required_columns are verified subsets of each CSV's actual header, so every
# entity's ingestion run passes header validation against the real data.
ENTITY_CONFIGS: dict[str, IngestionEntityConfig] = {
    "advisor": IngestionEntityConfig(
        entity_name="advisor",
        csv_file_name="phx_dm_advisor.csv",
        primary_key="advisor_id",
        tigergraph_vertex="phx_dm_advisor",
        required_columns=["advisor_id", "advisor_name", "status"],
        edge_files=["edges_phx_dm_advisor_in_market.csv", "edges_phx_dm_advisor_serves_household.csv"],
    ),
    "household": IngestionEntityConfig(
        entity_name="household",
        csv_file_name="phx_dm_household.csv",
        primary_key="household_id",
        tigergraph_vertex="phx_dm_household",
        required_columns=["household_id", "household_name", "segment", "total_aum"],
        edge_files=["edges_phx_dm_household_has_account.csv"],
    ),
    "account": IngestionEntityConfig(
        entity_name="account",
        csv_file_name="phx_dm_account.csv",
        primary_key="account_id",
        tigergraph_vertex="phx_dm_account",
        required_columns=["account_id", "account_name", "account_type", "status"],
    ),
    "transaction": IngestionEntityConfig(
        entity_name="transaction",
        csv_file_name="phx_dm_revenue_transaction.csv",
        primary_key="transaction_id",
        tigergraph_vertex="phx_dm_revenue_transaction",
        required_columns=["transaction_id", "transaction_date", "transaction_type", "revenue_amount"],
        batch_size=1000,
    ),
    "crm_activity": IngestionEntityConfig(
        entity_name="crm_activity",
        csv_file_name="phx_dm_crm_activity.csv",
        primary_key="activity_id",
        tigergraph_vertex="phx_dm_crm_activity",
        required_columns=["activity_id", "activity_type", "activity_date", "status"],
    ),
    "agp_goal": IngestionEntityConfig(
        entity_name="agp_goal",
        csv_file_name="phx_dm_goal.csv",
        primary_key="goal_id",
        tigergraph_vertex="phx_dm_goal",
        required_columns=["goal_id", "goal_name", "goal_type", "target_value", "status"],
    ),
    "kpi": IngestionEntityConfig(
        entity_name="kpi",
        csv_file_name="phx_dm_kpi.csv",
        primary_key="kpi_id",
        tigergraph_vertex="phx_dm_kpi",
        required_columns=["kpi_id", "kpi_name", "kpi_code", "status"],
    ),
    "prediction": IngestionEntityConfig(
        entity_name="prediction",
        csv_file_name="phx_dm_prediction_result.csv",
        primary_key="prediction_id",
        tigergraph_vertex="phx_dm_prediction_result",
        required_columns=["prediction_id", "prediction_type", "score", "confidence", "status"],
    ),
    "opportunity": IngestionEntityConfig(
        entity_name="opportunity",
        csv_file_name="phx_dm_opportunity.csv",
        primary_key="opportunity_id",
        tigergraph_vertex="phx_dm_opportunity",
        required_columns=["opportunity_id", "opportunity_type", "score", "severity", "status"],
    ),
    "recommendation": IngestionEntityConfig(
        entity_name="recommendation",
        csv_file_name="phx_dm_recommendation.csv",
        primary_key="recommendation_id",
        tigergraph_vertex="phx_dm_recommendation",
        required_columns=["recommendation_id", "recommendation_type", "title", "severity", "status"],
    ),
    "feedback": IngestionEntityConfig(
        entity_name="feedback",
        csv_file_name="phx_dm_feedback_event.csv",
        primary_key="feedback_id",
        tigergraph_vertex="phx_dm_feedback_event",
        required_columns=["feedback_id", "action", "reason_code"],
    ),
    "memory": IngestionEntityConfig(
        entity_name="memory",
        csv_file_name="phx_dm_context_memory.csv",
        primary_key="memory_id",
        tigergraph_vertex="phx_dm_context_memory",
        required_columns=["memory_id", "memory_type", "subject_type", "subject_id"],
    ),
    "document": IngestionEntityConfig(
        entity_name="document",
        csv_file_name="phx_dm_document.csv",
        primary_key="document_id",
        tigergraph_vertex="phx_dm_document",
        required_columns=["document_id", "title", "document_type", "status"],
    ),
    "feature_snapshot": IngestionEntityConfig(
        entity_name="feature_snapshot",
        csv_file_name="phx_dm_feature_snapshot.csv",
        primary_key="feature_snapshot_id",
        tigergraph_vertex="phx_dm_feature_snapshot",
        required_columns=["feature_snapshot_id", "entity_type", "entity_id", "feature_group"],
    ),
    "embedding": IngestionEntityConfig(
        entity_name="embedding",
        csv_file_name="phx_dm_embedding.csv",
        primary_key="embedding_id",
        tigergraph_vertex="phx_dm_embedding",
        required_columns=["embedding_id", "entity_type", "entity_id", "model_name"],
    ),
}


def get_entity_config(entity_name: str) -> IngestionEntityConfig:
    try:
        return ENTITY_CONFIGS[entity_name]
    except KeyError as exc:
        raise ValueError(f"Unknown ingestion entity: {entity_name}") from exc


def list_entity_configs() -> list[IngestionEntityConfig]:
    return list(ENTITY_CONFIGS.values())
