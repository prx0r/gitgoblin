# Architecture

## Design goal

GitGoblin should scale from one person's frontier watchlist to an industry intelligence product without replacing its core. The stable boundary is a normalized, append-only observation envelope. Sources and downstream products are plugins around that boundary.

## Layers

### 1. Sensors

Implemented sensors:

- GitHub REST: builder profile, following snapshot, user-star timeline, public events, owned repos.
- OpenAlex: scholarly works/authorship/citation-count snapshot.
- arXiv: newest matching preprints.
- ecosyste.ms: repository metadata cross-check.
- Hacker News official API: current technical discourse.
- RSS/Atom: arbitrary technical blogs or sector feeds.

Future sensors can include package-registry dependency changes, hiring/job posts, patents, conference proceedings, company engineering blogs, Hugging Face, MCP registry, funding/company events, vulnerability feeds, or customer-specific internal sources.

### 2. Observation plane

`Observation` is the immutable evidence atom. It separates:

- `occurred_at`: when the underlying event happened;
- `observed_at`: when GitGoblin retrieved it;
- `quality.temporal_precision`: event vs snapshot;
- source provenance and payload hash.

Observations are idempotently inserted into SQLite. Duplicate event IDs do not create duplicate evidence.

### 3. Entity graph

Entity records are mutable projections over immutable observations. They contain current repository/user/paper metadata needed for scoring. Replacing an entity projection never erases historical observations.

### 4. Expertise model

`ExpertiseScorer` estimates technical signal quality from demonstrated behavior. The current v1 combines:

- reputation (capped),
- technical activity,
- originality,
- average original-repository traction,
- sector language fit,
- account experience,
- small configured-seed prior.

Popularity is intentionally only 15% of the score.

Future versions should add contribution-depth, code-review quality, dependency adoption, publication record, prior early-hit calibration and sector-specific proof signals.

### 5. Attention/convergence model

For each target, technical alpha combines:

- builder score,
- action commitment weight,
- recency half-life,
- temporal precision,
- target novelty/saturation,
- recent momentum,
- independence by actor cluster,
- independent source-family breadth.

A star is weaker than a fork; a fork is weaker than a PR/dependency/authoring action. Scores saturate to prevent spammy volume from dominating.

### 6. Primitive extractor

The deterministic v1 maps target metadata, topics, descriptions, paper summaries and tags onto configurable architectural primitives. Sector YAML can extend/override the taxonomy.

The optional LLM analyzer is enrichment only. It must be shown repository/paper context and may propose architecture hypotheses, but it cannot set the core score or create evidence.

### 7. Opportunity engine

For each frontier signal, GitGoblin produces 1–3 opportunity hypotheses scored across technical alpha, signal confidence, novelty, momentum, monetization prior, proofability, source breadth and reuse safety.

Decisions align with VentureLab semantics: `BUILD`, `RESEARCH`, `WATCH`, `REJECT`.

### 8. Product/API plane

FastAPI exposes stable read/write operations and a tiny dashboard. The same data can be used by a paid web product, alerts, a CLI, an MCP server, or VentureLab.

### 9. VentureLab boundary

`gitgoblin.integrations.cuntgoblin` converts frontier signals into VentureLab `MarketObservation` records and opportunities into its `Opportunity` object. GitGoblin does not import VentureLab code and therefore remains separately deployable/versionable.

## Storage evolution

MVP: SQLite WAL.

Recommended progression by measured need:

- PostgreSQL: multi-user transactional product/API.
- ClickHouse: billions of event-time records / historical replay / fast aggregations.
- Object store: raw event archives and evidence artifacts.
- Graph DB only if graph traversal becomes the dominant workload; do not introduce one solely because the domain is graph-shaped.

The IDs and observation contracts are storage-neutral so migrations do not change public API semantics.

## Bounded graph expansion

Never recursively crawl everyone followed by everyone. A live scan expands only a small configurable number of one-hop relationships per seed. Future expansion should be budgeted by expected information gain:

```text
next_person_value ≈ builder_prior × novelty_of_neighborhood × source_gap × expected_signal_gain / API_cost
```

This keeps the system under API limits and focuses collection on useful edges.

## Versioning

Before changing formulas in production:

- add `scoring_method_version` to persisted signals;
- replay a historical window;
- compare precision/lead time against prior release;
- retain old signals rather than mutating history.

The v0.1 implementation is intentionally compact but keeps these boundaries available.
