from app.config.settings import get_settings
from app.config.validation import ConfigValidator

def test_config_validator_runs():
    result = ConfigValidator(get_settings()).validate()
    assert result.valid is True
    assert isinstance(result.warnings, list)
