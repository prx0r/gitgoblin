# Operations

## Single-node MVP

Use SQLite WAL on persistent disk and run the API separately from the scheduler.

```bash
# terminal/service 1
gitgoblin serve --host 0.0.0.0 --port 8787

# terminal/service 2: one cycle
python -m gitgoblin.scheduler --sector ai --sector databases --once
```

For repeated scheduling, use systemd/cron/or an external durable scheduler rather than relying on a sleeping shell process.

## Collection budgets

Start with:

- 1–5 carefully chosen seeds per sector;
- 1–2 pages per GitHub endpoint;
- one-hop expansion of 0–3 people per seed;
- 1–3 research queries;
- 6-hour or daily cadence.

Measure API cost and signal yield before increasing breadth.

## Backups

Back up:

- `data/gitgoblin.db`
- `data/artifacts/runs/`
- production config/seeds

HTTP cache can be regenerated.

## Migration trigger

Move from SQLite when one of these is measured:

- concurrent writers routinely block;
- observation volume makes queries materially slow after indexes/tuning;
- multi-tenant isolation/HA becomes required;
- historical replay requires analytical scans over hundreds of millions/billions of rows.

At that point, prefer PostgreSQL for the operational projection and ClickHouse/object storage for event history.
