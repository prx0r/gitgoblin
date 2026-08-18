import json
from pathlib import Path

import jsonschema

from gitgoblin.integrations.cuntgoblin import opportunity_to_cuntgoblin, signal_to_market_observations
from gitgoblin.pipeline.opportunities import OpportunityEngine
from gitgoblin.pipeline.signals import SignalEngine


def test_cuntgoblin_export_contract(populated_store, settings, profile):
    signal = SignalEngine(populated_store, settings, profile).detect(include_test=True)[0]
    obs = signal_to_market_observations(signal)
    assert {"observation_id", "oracle_id", "entity_id", "metric", "observed_at", "source_family", "evidence"} <= set(obs[0])
    assert obs[0]["evidence"]["artifact_sha256"]

    opp = OpportunityEngine(populated_store, settings, profile).derive(signal)[0]
    exported = opportunity_to_cuntgoblin(opp)
    assert {"opportunity_id", "market_topic_ids", "problem", "miner", "evidence", "scorecard", "decision"} <= set(exported)
    assert exported["decision"] in {"BUILD", "RESEARCH", "WATCH", "REJECT"}


def test_exports_validate_against_checked_contract_schemas(populated_store, settings, profile):
    from gitgoblin.pipeline.signals import SignalEngine
    from gitgoblin.pipeline.opportunities import OpportunityEngine

    signal = SignalEngine(populated_store, settings, profile).detect(include_test=True)[0]
    opportunity = OpportunityEngine(populated_store, settings, profile).derive(signal)[0]
    root = Path(__file__).resolve().parents[1]
    market_schema = json.loads((root / "schemas/cuntgoblin_market_observation.schema.json").read_text())
    opp_schema = json.loads((root / "schemas/cuntgoblin_opportunity.schema.json").read_text())
    for record in signal_to_market_observations(signal):
        jsonschema.validate(record, market_schema)
    jsonschema.validate(opportunity_to_cuntgoblin(opportunity), opp_schema)
