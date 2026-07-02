from app.ai.adapters.adapter_factory import ModelAdapterFactory
from app.ai.adapters.mock_adapter import MockModelAdapter
from app.models.enums import AdapterProvider

def test_mock_adapter_factory():
    adapter = ModelAdapterFactory.create(AdapterProvider.MOCK)
    assert isinstance(adapter, MockModelAdapter)
    assert adapter.generate_json("test")["source"] == "mock_adapter"
    assert len(adapter.embed_text("hello")) == 64
