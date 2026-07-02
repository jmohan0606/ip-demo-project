from __future__ import annotations
from app.config.settings import get_settings


class ChromaClientFactory:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create_client(self):
        import chromadb
        return chromadb.PersistentClient(path=self.settings.chroma_path)

    def get_or_create_collection(self, collection_name: str):
        return self.create_client().get_or_create_collection(name=collection_name)
