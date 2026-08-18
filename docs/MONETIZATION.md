# Monetization

GitGoblin should monetize **decision advantage**, not raw public records.

## Product ladder

### Free public surface

Use this for distribution:

- weekly public frontier digest;
- limited watchlists;
- delayed signals;
- public repository pages;
- SDK/OpenAPI/MCP client;
- examples and a small set of transparent scores.

Do not expose the complete seed graph, historical calibration data, exact high-value scoring weights or full opportunity graph by default.

### Individual Pro

Target: technical founders, senior engineers, researchers, indie investors.

Possible package:

- real-time-ish watchlists;
- custom sectors/keywords;
- signal explanations;
- architecture/primitives reports;
- saved builders/repos;
- email/webhook/API alerts;
- historical comparison.

Suggested initial validation price: **$19–49/month**, then raise based on retention and demonstrated lead-time value.

### Team / R&D

Target: venture studios, technical strategy teams, developer-relations teams, corporate R&D.

- shared sector graphs;
- custom expert seeds;
- organization collaboration maps;
- API/webhooks;
- private annotations;
- exports;
- higher collection budgets;
- custom source adapters.

Suggested validation range: **$199–999/month** depending on seats/data intensity.

### Enterprise / data/API

Target: funds, strategy firms, platforms, research organizations.

- bulk/historical data products;
- custom scoring/replay;
- warehouse delivery;
- SLAs;
- private/internal-source fusion;
- sector-specific models;
- dedicated support.

Price by data volume/value rather than seats alone. Comparable intelligence vendors commonly make API/bulk data an enterprise sales motion rather than publishing low fixed prices.

## API pricing

A strong unit is not "per GitHub row." Sell the derived operation:

- frontier signal lookup,
- watchlist monitoring,
- architecture report,
- opportunity derivation,
- historical replay.

For agents, usage pricing can be simple credits:

```text
repo/person lookup        cheap
frontier search           medium
architecture deep-dive    higher
sector replay/backtest    batch/enterprise
```

## Moat

Keep these private by default:

- curated seed graph;
- historical interaction/event archive where legally permitted;
- prior-hit calibration per builder;
- identity resolution corrections;
- independence clusters;
- false-positive/true-positive labels;
- downstream VentureLab outcome data;
- calibrated scoring weights;
- customer-specific source integrations.

The more important feedback loop is:

```text
signal detected at t0
→ opportunity proposed
→ prototype/research outcome
→ later ecosystem adoption at t+n
→ credit/blame original signals/builders
→ update predictive priors
```

Over time GitGoblin learns *who is early and right about what*, which is substantially harder to clone than source code.

## Public/private repository strategy

Develop the core privately. Publish only components that create distribution:

- client SDKs,
- schemas,
- MCP facade,
- examples,
- maybe generic collectors that are not a moat.

Do not publish the current full production scoring/data pipeline simply to prove the product exists. A public API and reproducible benchmark can prove utility without publishing the proprietary graph and weights.
