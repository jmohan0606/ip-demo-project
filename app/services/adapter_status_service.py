from app.ai.adapters.adapter_factory import ModelAdapterFactory
from app.config.settings import get_settings
from app.models.enums import AdapterProvider
from app.shared.exceptions import ConfigurationError
class AdapterStatusService:
    def model_adapter_status(self) -> dict:
        s=get_settings(); adapter=ModelAdapterFactory.create(AdapterProvider.OPENAI); name=adapter.__class__.__name__
        return {'selected_provider':AdapterProvider.OPENAI,'active_adapter':name,'openai_configured':bool(s.openai_api_key),'smart_sdk_available':False,'fallback_active':name=='MockModelAdapter'}
    def validate_openai_ready(self) -> None:
        if not get_settings().openai_api_key: raise ConfigurationError('OPENAI_API_KEY is required for OpenAI model execution.')
