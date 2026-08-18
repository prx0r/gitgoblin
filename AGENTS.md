# AGENTS.md — GitGoblin

Read this before changing the repository.

## Mission

GitGoblin converts public technical activity into **evidence-backed frontier signals**, then into falsifiable product hypotheses. It is not a content scraper and not a startup-idea text generator.

## Non-negotiable invariants

1. **No evidence, no signal.** Every production observation carries a source reference and SHA-256 evidence hash.
2. **Never invent timestamps.** Snapshot relationships (for example current GitHub follows) are labeled `snapshot_only`; event timestamps are used only when an upstream source supplies them.
3. **Test fixtures never become market evidence.** Fixtures use `is_test_fixture=true`; default DB queries and VentureLab exports exclude them.
4. **No hidden network fallback.** A failed collector raises or records an explicit source failure; it must not silently substitute fabricated data.
5. **No popularity-only ranking.** Raw stars/followers are capped components, not the target metric.
6. **Independence matters.** Multiple correlated actors must not be counted as independent confirmations.
7. **Respect upstream access controls.** Do not scrape around GitHub/API restrictions or use the product for spam/contact harvesting.
8. **License before reuse.** Study any public architecture, but do not incorporate code until its license is known and compatible.
9. **Cuntgoblin compatibility is a contract.** Changes to export objects require tests against the checked-in compatibility schemas.
10. **A markdown claim is not a test result.** Run the commands and retain the log/certificate.

## Work order

For any material change:

```text
READ contracts/config
→ define behavior and failure mode
→ write/adjust test
→ implement
→ run targeted test
→ run full pytest
→ run certificate
→ inspect build/CERTIFICATE.json and build/test.log
```

## Commands

```bash
# full deterministic suite
pytest -q

# verbose failed test
pytest -q -x -vv

# real certification; invokes pytest unless --skip-pytest
python -m gitgoblin.certify --output build/CERTIFICATE.json

# initialize and run locally
gitgoblin init
gitgoblin seed databases carlsverre
gitgoblin scan databases --seed carlsverre --expand 2
gitgoblin serve --port 8787
```

## Source adapter contract

A source adapter returns:

```python
(list[Entity], list[Observation])
```

Rules:

- normalize IDs with a namespace (`github:user:`, `github:repo:`, `openalex:work:`, etc.);
- preserve original source URL/record ID in `Evidence`;
- hash the exact normalized source payload used for the observation;
- distinguish `occurred_at` from collection `observed_at`;
- raise on malformed/forbidden upstream responses unless the caller intentionally treats that source as optional;
- do not let source-specific fields leak into cross-source scoring except through `value`, `tags` or entity attrs.

## Adding an industry

Prefer `configs/sectors/<sector>.yaml` first. Add code only when the industry requires a genuinely new source type or primitive extractor.

A sector file contains:

- seed builders,
- keywords,
- research queries,
- expertise languages,
- primitive rules.

Do not duplicate the engine per sector.

## Adding a source

1. Implement a collector under `gitgoblin/sources/`.
2. Add a parser test using a recorded/controlled payload.
3. Document source terms, rate limits and temporal semantics.
4. Wire it into `Scout` only if it is generally useful; otherwise compose it in a sector-specific runner later.
5. Add its source family to evidence-breadth reasoning only when genuinely independent.

## Scoring changes

Scoring code must remain deterministic and versionable. A new metric needs:

- motivation,
- explicit formula,
- bounded range,
- regression test,
- replay/calibration plan.

Never let an LLM directly set `technical_alpha` or `decision`.

## Repository reuse workflow

When GitGoblin flags a promising repository:

```text
license → architecture → benchmarks/tests → dependency graph → primitive → clean product hypothesis
```

For permissive code, reuse still requires notices/attribution and compliance with the exact license. For copyleft/unknown repositories, default to API consumption, interoperability, or independent reimplementation until reviewed.

## Operational discipline

- Secrets only through environment variables/secrets manager.
- Keep `data/`, HTTP caches and run artifacts out of git.
- SQLite WAL is suitable for a single-node MVP. Move to Postgres/ClickHouse/graph storage only when measured volume requires it.
- Back up the append-only observations before migrations.
- Use bounded expansion; never recursively crawl the whole social graph by default.
- Honor `Retry-After`/rate-limit reset headers and stop on persistent throttling.

## Definition of done

A change is done only when:

- code path is implemented,
- tests exercise its success and relevant failure semantics,
- full suite passes,
- certification is regenerated,
- docs/config/schema are updated if contracts changed.
