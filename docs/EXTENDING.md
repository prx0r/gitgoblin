# Extending GitGoblin

## New industry, no code

Copy a sector YAML and change:

```yaml
id: robotics
seed_builders: [...]
keywords: [...]
arxiv_queries: [...]
expertise_languages: [c++, python, rust]
primitive_rules:
  robot-task-runtime: [ros, manipulation, planning, control]
```

Then:

```bash
gitgoblin scan robotics --seed examplebuilder
```

## New source

Implement a collector returning `Entity` and `Observation` objects. Example sources worth adding:

- package-registry release/dependency stream;
- Hugging Face model/dataset activity;
- MCP registry;
- patents;
- conference proceedings;
- job/hiring changes;
- company engineering blogs;
- funding/company formation;
- customer-internal GitHub/GitLab/Slack/knowledge sources.

Each source needs explicit documentation for:

- provenance;
- timestamp semantics;
- rate limits;
- licensing/terms;
- independent source-family classification.

## Better graph independence

Current v1 uses company metadata as a simple correlated-cluster penalty. Upgrade path:

1. maintain an actor-to-organization/collaboration graph;
2. compute community labels periodically;
3. use effective independent sample size rather than raw actor count;
4. test whether this improves historical prediction.

## Prior predictive accuracy

Add outcome labels and compute per-builder:

```text
lead_time
precision@k
hit_rate
sector_specific_hit_rate
calibration_error
```

This should become a major `BuilderScore` input only after enough historical labels exist.

## Architecture extraction

The current deterministic extractor is intentionally conservative. A future repository analyzer can:

- fetch README/docs/tree/package manifests;
- inspect tests/benchmarks;
- map modules/dependencies;
- summarize only evidenced behavior with an LLM;
- emit a structured `PrimitiveReport` with source-line/repo-path references.

The LLM should never be allowed to infer that a benchmark passed merely because a benchmark file exists.

## MCP

A future MCP server should wrap stable API operations rather than become a second implementation. Candidate tools:

```text
frontier_search
watch_builder
watch_repo
explain_signal
architecture_report
opportunity_search
sector_digest
```
