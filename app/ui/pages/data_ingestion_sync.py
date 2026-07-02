from __future__ import annotations

import streamlit as st

from app.ingestion.ingestion_service import IngestionService
from app.models.ingestion import IngestionRunRequest


def render_data_ingestion_sync_page() -> None:
    st.title("Data Ingestion & Sync")
    st.caption("Upload, validate, delta-detect, checkpoint, resume, and upsert into TigerGraph.")

    service = IngestionService()
    entities = service.list_entities()
    entity_names = [e["entity_name"] for e in entities]

    selected = st.selectbox("Entity", entity_names)
    dry_run = st.checkbox("Dry Run", value=True)
    resume = st.checkbox("Resume failed/incomplete batch", value=True)
    batch_size = st.number_input("Batch size", min_value=10, max_value=5000, value=500, step=100)

    if st.button("Run Next Batch"):
        with st.status("Running ingestion batch...", expanded=True) as status:
            result = service.run_entity_ingestion(
                IngestionRunRequest(
                    entity_name=selected,
                    dry_run=dry_run,
                    resume=resume,
                    batch_size=int(batch_size),
                )
            )
            batch = result.batch_status
            st.write(f"Status: {batch.status}")
            st.write(f"Processed: {batch.processed_records} / {batch.total_records}")
            st.progress(min(100, int(batch.progress_percent)))
            st.write(
                {
                    "created": batch.created_records,
                    "updated": batch.updated_records,
                    "skipped": batch.skipped_records,
                    "failed": batch.failed_records,
                    "last_processed_row": batch.last_processed_row,
                    "message": batch.message,
                }
            )
            if str(batch.status) == "completed":
                status.update(label="Ingestion completed", state="complete")
            elif str(batch.status) == "failed":
                status.update(label="Ingestion failed", state="error")
            else:
                status.update(label="Batch completed", state="complete")

    st.subheader("Upload / Sync History")
    st.dataframe(service.list_batches(), use_container_width=True)
