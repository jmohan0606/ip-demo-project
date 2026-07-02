from app.config.manifest import project_manifest
from app.config.settings import get_settings
from app.config.validation import ConfigValidator
from app.services.adapter_status_service import AdapterStatusService
from app.services.runtime_status_service import RuntimeStatusService

def main() -> None:
    assert ConfigValidator(get_settings()).validate().valid is True
    manifest=project_manifest(); assert manifest['application']=='iPerform Insights & Coaching'; assert manifest['schema_prefix']=='phx_dm_'
    adapter_status=AdapterStatusService().model_adapter_status(); assert adapter_status['active_adapter'] in {'MockModelAdapter','OpenAIModelAdapter'}
    runtime=RuntimeStatusService().get_health_report(); assert runtime.graph_name=='iperform_insights_coaching_demo'
    print('Part 11.0.3 validation passed.'); print(f"Adapter: {adapter_status['active_adapter']}"); print(f'Runtime status: {runtime.overall_status}')
if __name__ == '__main__': main()
