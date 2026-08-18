from gitgoblin.pipeline.opportunities import OpportunityEngine
from gitgoblin.pipeline.signals import SignalEngine


def test_frontier_signal_detects_independent_high_commitment_attention(populated_store, settings, profile):
    signals = SignalEngine(populated_store, settings, profile).detect(include_test=True)
    assert signals
    signal = signals[0]
    assert signal.target_id == "github:repo:newco/frontier"
    assert signal.expert_count == 3
    assert signal.independent_cluster_count == 3
    assert signal.technical_alpha > 0.6
    assert any("higher-commitment" in reason for reason in signal.reasons)


def test_opportunity_is_derived_from_evidenced_signal(populated_store, settings, profile):
    signal = SignalEngine(populated_store, settings, profile).detect(include_test=True)[0]
    opps = OpportunityEngine(populated_store, settings, profile).derive(signal)
    assert opps
    assert opps[0].primitive in {"durable-agent-state", "agent-orchestration"}
    assert opps[0].decision in {"BUILD", "RESEARCH", "WATCH"}
    assert opps[0].evidence_ids == signal.evidence_ids
