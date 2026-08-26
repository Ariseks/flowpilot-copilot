import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    data_file = tmp_path / "state.json"
    settings = Settings(llm_api_key="", data_file=str(data_file))
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def rate_limited_client(tmp_path):
    data_file = tmp_path / "state.json"
    settings = Settings(
        llm_api_key="",
        data_file=str(data_file),
        rate_limit=1,
        rate_window_seconds=60,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def persisted_state(tmp_path):
    data_file = tmp_path / "state.json"
    settings = Settings(llm_api_key="", data_file=str(data_file))
    with TestClient(create_app(settings)) as test_client:
        test_client.post(
            "/api/feedback",
            json={"message": "测试持久化", "rating": 5, "category": "测试"},
        )
    return json.loads(data_file.read_text(encoding="utf-8"))
