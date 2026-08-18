# VentureLab / cuntgoblin integration

GitGoblin should be registered as a specialized frontier-intelligence oracle rather than embedded directly into VentureLab.

## Contract

Oracle ID:

```text
gitgoblin.frontier_graph.v1
```

GitGoblin exports each `FrontierSignal` as several VentureLab-compatible market observations:

- `technical_alpha`
- `novelty`
- `momentum`
- `expert_count`
- `independent_cluster_count`

It also exports GitGoblin opportunities in the VentureLab `Opportunity` shape with decision values:

- `BUILD`
- `RESEARCH`
- `WATCH`
- `REJECT`

## Pull integration

```bash
gitgoblin export --sector ai --out build/gitgoblin-ai.json
```

VentureLab can ingest the resulting file as one oracle batch.

## API integration

```text
GET /v1/export/cuntgoblin?sector=ai
```

For production, cuntgoblin should store the received artifact hash and ingestion timestamp, not merely copy current scores into markdown.

## Feedback integration

The next important integration is the reverse direction. VentureLab should publish outcome records back to GitGoblin:

```text
opportunity_id
prototype_result
real_usage
revenue_or_adoption
false_positive_reason
observed_at
```

GitGoblin can then calibrate seed-builder and signal-quality priors using actual downstream outcomes. This is intentionally left as a future schema because the current VentureLab outcome contract should remain authoritative.
