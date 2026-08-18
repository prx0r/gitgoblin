import json
import pytest

try:
    from mcp.server.fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False


@pytest.fixture
def mcp_server(tmp_path):
    if not HAS_FASTMCP:
        pytest.skip("mcp.server.fastmcp not available (need mcp[cli] or mcp<2)")
    from gitgoblin.mcp_server import build_server
    server = build_server(db_path=str(tmp_path / "test.db"), config_root="configs")
    return server


def test_list_sectors_tool(mcp_server):
    result = mcp_server._tool_manager._tools["list_sectors"]()
    data = json.loads(result)
    assert len(data) >= 3
    ids = [s["id"] for s in data]
    assert "ai" in ids


def test_get_signals_empty(mcp_server):
    result = mcp_server._tool_manager._tools["get_signals"]()
    data = json.loads(result)
    assert data == []


def test_get_opportunities_empty(mcp_server):
    result = mcp_server._tool_manager._tools["get_opportunities"]()
    data = json.loads(result)
    assert data == []


def test_add_and_list_seeds(mcp_server):
    result = mcp_server._tool_manager._tools["add_seed"](sector="ai", username="testdev")
    data = json.loads(result)
    assert "testdev" in data["seeds"]
    result2 = mcp_server._tool_manager._tools["list_seeds"](sector="ai")
    data2 = json.loads(result2)
    assert "testdev" in data2["persisted"]


def test_get_entity_not_found(mcp_server):
    result = mcp_server._tool_manager._tools["get_entity"](entity_id="nonexistent")
    data = json.loads(result)
    assert "error" in data


def test_get_sector_stats(mcp_server):
    result = mcp_server._tool_manager._tools["get_sector_stats"](sector="ai")
    data = json.loads(result)
    assert data["sector"] == "ai"
    assert data["signal_count"] == 0


def test_export_cuntgoblin_empty(mcp_server):
    result = mcp_server._tool_manager._tools["export_cuntgoblin"]()
    data = json.loads(result)
    assert "market_observations" in data
    assert "opportunities" in data
    assert len(data["market_observations"]) == 0


def test_search_entities_empty(mcp_server):
    result = mcp_server._tool_manager._tools["search_entities"](query="test")
    data = json.loads(result)
    assert data == []
