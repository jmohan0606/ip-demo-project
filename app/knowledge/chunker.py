from __future__ import annotations

from app.knowledge.models import DocumentChunk


class DocumentChunker:
    def __init__(self, chunk_size: int = 900, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document_id: str, document_name: str, content: str, metadata: dict | None = None) -> list[DocumentChunk]:
        clean = " ".join((content or "").split())
        if not clean:
            clean = "No content supplied. Demo placeholder content for knowledge ingestion."

        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        while start < len(clean):
            end = min(len(clean), start + self.chunk_size)
            text = clean[start:end]
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{document_id}-CHUNK-{index:04d}",
                    document_id=document_id,
                    document_name=document_name,
                    chunk_index=index,
                    text=text,
                    metadata=metadata or {},
                )
            )
            index += 1
            if end == len(clean):
                break
            start = max(0, end - self.overlap)
        return chunks
