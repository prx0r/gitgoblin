import pytest
from gitgoblin.api import create_app


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient
    app = create_app(db_path=str(tmp_path / "test.db"), config_root="configs")
    return TestClient(app)


def test_list_sectors(client):
    r = client.get("/v1/sectors")
    assert r.status_code == 200
    sectors = r.json()
    assert len(sectors) >= 3
    ids = [s["id"] for s in sectors]
    assert "ai" in ids
    assert "databases" in ids
    assert "devtools" in ids


def test_stats_empty(client):
    r = client.get("/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["signal_count"] == 0
    assert data["opportunity_count"] == 0
    assert data["sector"] == "all"


def test_stats_sector_filter(client):
    r = client.get("/v1/stats?sector=ai")
    assert r.status_code == 200
    data = r.json()
    assert data["sector"] == "ai"


def test_search_empty(client):
    r = client.get("/v1/search?q=nonexistent")
    assert r.status_code == 200
    assert r.json() == []


def test_seeds_persist(client):
    client.post("/v1/seeds", json={"sector": "ai", "username": "testuser"})
    r = client.get("/v1/seeds/ai")
    assert r.status_code == 200
    data = r.json()
    assert "testuser" in data["persisted"]
