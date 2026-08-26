import asyncio

from app.config import Settings
from app.services.llm import LLMClient


def test_llm_client_skips_network_without_api_key():
    client = LLMClient(Settings(llm_api_key=""))
    result = asyncio.run(client.complete("system", "user", []))
    assert client.mode == "demo"
    assert result.content is None
    assert result.provider_used == "demo"
    assert result.fallback_used is True


def test_llm_client_falls_back_when_cloud_is_unreachable():
    client = LLMClient(
        Settings(llm_api_key="test-key", llm_base_url="http://127.0.0.1:1")
    )
    result = asyncio.run(client.complete("system", "user", []))
    assert client.mode == "cloud"
    assert result.content is None
    assert result.provider_used == "cloud"
    assert result.fallback_used is True
    assert result.error_type
