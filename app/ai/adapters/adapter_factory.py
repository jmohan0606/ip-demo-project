from __future__ import annotations
from app.ai.adapters.model_adapter import ModelAdapter
from app.ai.adapters.mock_adapter import MockModelAdapter
from app.ai.adapters.openai_adapter import OpenAIModelAdapter
from app.ai.adapters.smartsdk_adapter import SmartSdkModelAdapter
from app.config.settings import get_settings
from app.models.enums import AdapterProvider

class ModelAdapterFactory:
    @staticmethod
    def create(provider: AdapterProvider | str | None = None) -> ModelAdapter:
        settings = get_settings()
        selected = AdapterProvider(provider or AdapterProvider.OPENAI)
        if selected == AdapterProvider.OPENAI:
            if settings.openai_api_key and settings.enable_openai:
                return OpenAIModelAdapter()
            return MockModelAdapter()
        if selected == AdapterProvider.SMARTSDK:
            return SmartSdkModelAdapter()
        if selected == AdapterProvider.MOCK:
            return MockModelAdapter()
        raise ValueError(f"Unsupported model adapter provider: {selected}")
