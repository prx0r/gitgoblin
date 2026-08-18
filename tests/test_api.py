from fastapi.testclient import TestClient

from gitgoblin.api import create_app
from gitgoblin.pipeline.opportunities import OpportunityEngine
from gitgoblin.pipeline.signals import SignalEngine


def test_api_health_and_exports(tmp_path, populated_store, settings, profile):
    # Seed a real signal/opportunity into the same temporary DB used by the API.
    signal = SignalEngine(populated_store, settings, profile).detect(include_test=True)[0]
    populated_store.add_signal(signal)
    populated_store.add_opportunity(OpportunityEngine(populated_store, settings, profile).derive(signal)[0])

    app = create_app(db_path=str(populated_store.path), config_root="configs")
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/v1/signals").json()[0]["signal_id"] == signal.signal_id
    exported = client.get("/v1/export/cuntgoblin").json()
    assert exported["market_observations"]
    assert exported["opportunities"]
    assert "GitGoblin" in client.get("/").text
