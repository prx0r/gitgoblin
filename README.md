# GitGoblin

**Technical alpha before virality.** GitGoblin watches high-signal builders, repositories, papers, dependencies and technical discourse; converts their activity into evidence-backed observations; detects independent expert convergence; extracts the underlying technical primitive; and emits downstream product opportunities.

GitGoblin is designed as both:

1. a standalone frontier-intelligence product; and
2. a specialized oracle for VentureLab/venture-lab.

## What is implemented

- GitHub public-profile, following, starred-repository, public-event and repository collectors.
- OpenAlex recent-work collector.
- arXiv Atom collector.
- ecosyste.ms repository-metadata collector.
- Hacker News official API collector.
- Generic RSS/Atom technical-publication collector.
- SQLite WAL store with idempotent append-only observation ingestion.
- Evidence hashes and source URLs on every observation.
- Builder expertise scoring that caps raw popularity influence.
- Time-decayed weighted attention, momentum, novelty and independence scoring.
- Frontier convergence signals ("technical alpha").
- Rule-based architectural primitive extraction with sector overrides.
- Product-opportunity derivation and build/research/watch/reject decisions.
- License classifier to prevent accidental source-code incorporation.
- FastAPI service, CLI, dashboard, Docker image and scheduler.
- VentureLab-compatible `MarketObservation` and `Opportunity` export.
- Deterministic tests and a certificate generator that records actual pytest output.

The core decision path does **not** require an LLM. An optional OpenAI-compatible analyzer can enrich architecture analysis, but it cannot manufacture evidence or override deterministic scoring.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env

# Add a seed builder to an industry profile
gitgoblin seed databases carlsverre

# Live scan: GitHub + arXiv + OpenAlex + HN
gitgoblin scan databases --seed carlsverre --expand 2

# Inspect signals
gitgoblin rank --sector databases

# Export to VentureLab/venture-lab
gitgoblin export --sector databases --out build/venture-lab-export.json

# Dashboard + API
gitgoblin serve --host 0.0.0.0 --port 8787
```

For GitHub automation, set `GITHUB_TOKEN`; unauthenticated requests have much lower limits. OpenAlex now uses API keys for scaled API access, so set `OPENALEX_API_KEY` for production use.

## API

- `GET /health`
- `POST /v1/seeds`
- `GET /v1/seeds/{sector}`
- `POST /v1/scans`
- `GET /v1/signals`
- `GET /v1/opportunities`
- `GET /v1/entities/{entity_id}`
- `GET /v1/export/venture-lab`
- `GET /` — compact dashboard

Interactive OpenAPI docs are provided automatically by FastAPI at `/docs`.

## Why it is not just GitHub Trending

GitGoblin's unit of signal is not `star_count`. It weights:

- **who** acted (demonstrated technical depth),
- **what** action they took (star < fork < PR/dependency/authoring),
- **when** they acted (early + recent > post-viral),
- **independence** (five unrelated experts > five coworkers),
- **novelty/saturation** of the target,
- **momentum** in recent high-quality interactions,
- **source breadth** across code/research/discourse.

This is deliberately designed to surface small projects with strong expert convergence before broad popularity.

## Architecture

```text
GitHub ─┐
GHArchive/ecosyste.ms ─┤
OpenAlex/arXiv ─────────┤
HN/RSS ─────────────────┤
future sensors ─────────┘
          │
          ▼
  normalized observations
  + evidence + timestamps
          │
          ▼
   entity/identity graph
          │
          ▼
    builder expertise
          │
          ▼
 weighted attention graph
          │
          ▼
 convergence + novelty + momentum
          │
          ▼
      FrontierSignal
          │
          ▼
 architectural primitive extraction
          │
          ▼
 opportunity derivation
      │             │
      ▼             ▼
 GitGoblin API   VentureLab oracle
```

See `docs/ARCHITECTURE.md` for contracts and extension points.

## Industry profiles

Profiles live in `configs/sectors/*.yaml`. Included:

- `ai`
- `databases`
- `devtools`

A profile selects seed builders, research queries, keywords, expertise languages and primitive rules. Adding robotics, biotech, security, climate-tech, crypto-infrastructure, etc. is configuration plus optional new source adapters—not a fork of the core engine.

## Evidence doctrine

Production observations must have:

- source identity,
- source family,
- occurred/observed timestamps,
- artifact SHA-256,
- source URL where available,
- quality metadata when temporal precision is weaker than an event timestamp.

Current GitHub following relationships are recorded as **snapshots**, never falsely timestamped as historical follow events.

Test fixtures are explicitly flagged `is_test_fixture=true` and are excluded from normal production queries/exports.

## Testing

```bash
pytest -q
python -m gitgoblin.certify --output build/CERTIFICATE.json
```

The certificate records the actual pytest return code/output and a content digest of the codebase. See `docs/TESTING.md`.

## Privacy / use boundaries

GitGoblin is intended for aggregate technical-intelligence analysis, not spam, stalking, or sale of personal contact data. Do not defeat upstream access restrictions. Respect source/API terms, rate limits, and data licenses. GitHub's 2026 changes restricting repository stargazer lists are one reason the architecture uses redundant event sources rather than scraping restricted UI/API surfaces.

## Commercial model

The open surface can be SDK/schema/dashboard samples; the valuable private core is the historical attention graph, calibrated builder scores, sector-specific seed graph, convergence model, primitive/opportunity models and accumulated outcome feedback. See `docs/MONETIZATION.md`.
