# Frontier / prior-art research (2026-08-18)

This document records the design research used for the first GitGoblin build. It is not a claim that upstream projects endorse GitGoblin.

## Closest systems and what to reuse

| System | Useful primitive | License / access implication | GitGoblin decision |
|---|---|---|---|
| OSSInsight | 10B+ GitHub-event analytics, developer/repo analytics, collections, public API | Public analytics/API; inspect current repo license before code reuse | Treat as complementary analytics/source, not the product architecture |
| GH Archive | Public GitHub event archive and BigQuery workflow | MIT code/docs; dataset may include third-party rights | Safe architectural reference; useful historical-event source |
| ecosyste.ms repos/timeline/packages | Repository/package/dependency/timeline APIs; many small composable services | Server code AGPL-3.0; API data commonly CC BY-SA 4.0 | Consume APIs and respect data attribution/share-alike; do not vendor server code into proprietary core |
| Libraries.io | OSS discovery + package manager ecosystem indexing | AGPL-3.0 | Learn from discovery model; prefer ecosyste.ms APIs rather than copying server |
| Star History | Repository star time-series visualization/API | MIT | Reusable visualization patterns, but direct stargazer enumeration is less dependable after GitHub's 2026 restrictions |
| Most Influential GitHub Repo Stars | Ranks influential stargazers/forkers; SQLite cache, bounded concurrency, rate-limit handling | MIT | Closest small prior art to expert-weighted attention; its repo-centric stargazer direction is now constrained by GitHub's June 2026 access change, so GitGoblin reverses the graph: start from selected builders and observe their public actions |
| CHAOSS GrimoireLab | Multi-source software-development analytics platform | GPL-3.0 | Reference for adapter separation and normalized software-event analytics; do not vendor into proprietary core |
| Aveloxis (successor direction from Augur) | High-throughput OSS metrics collection, staged JSONB ingest, gap-fill verification, scheduler/monitoring | MIT (per repository README) | Strong reference for future high-scale collector architecture: stage raw envelopes, process deterministically, verify collection completeness, separate collection from analysis |
| Google deps.dev | Package/project/dependency/security graph via HTTP/gRPC | API definitions/examples Apache-2.0; generated data CC BY 4.0 | Future dependency-adoption sensor |
| OpenAlex | Huge scholarly graph of works/authors/institutions/citations | Open data; API now freemium/usage-priced | Primary research/person/paper graph sensor |

## Key current constraints

### GitHub access

GitHub announced in June 2026 that repository stargazer-list and watcher-list endpoints/UI views would be restricted to repository admins/collaborators. GitGoblin therefore must not depend on enumerating every stargazer of arbitrary repositories.

Still-useful public routes include current-user/repository metadata, a user's public events, people a public user follows, and repositories a public user has starred (subject to current API terms and permissions). Public Events API data is explicitly not a true real-time feed and can lag.

GitHub's REST API has primary and secondary rate limits; authenticated personal access typically raises the core limit compared with unauthenticated traffic. Collectors must obey reset/Retry-After signals rather than brute-force retries.

Sources:
- https://github.blog/changelog/2026-06-30-upcoming-access-restrictions-to-public-api-endpoints-and-ui-views/
- https://docs.github.com/en/rest/activity/starring
- https://docs.github.com/en/rest/users/followers?apiVersion=2026-03-10
- https://docs.github.com/en/rest/activity/events
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

### Why raw stars are a bad target metric

Research and current OSS tooling show that public promotion can strongly shift star trajectories, and research has identified suspected fake-star activity at scale. GitGoblin therefore treats stars as one weak action and tries to detect expert attention *before* mass promotion.

Research:
- https://arxiv.org/abs/2412.13459
- https://arxiv.org/abs/2511.04453
- https://arxiv.org/abs/2502.00058

### OpenAlex

OpenAlex is a heterogeneous scholarly graph with works/authors/institutions/topics/citations and provides API/snapshot access. In 2026 its API moved to usage-based pricing with a free daily allowance. This makes it appropriate as a sensor but collection must be budget-aware.

Sources:
- https://developers.openalex.org/
- https://developers.openalex.org/api-reference/authentication
- https://arxiv.org/abs/2205.01833

### ecosyste.ms

The project explicitly uses many small independent API services that can be combined into larger pipelines. This strongly validates GitGoblin's sensor architecture. Its server code is AGPL-3.0 and API data is generally CC BY-SA 4.0, so the commercial-safe approach is API consumption plus license-compliant attribution/data handling.

Sources:
- https://github.com/ecosyste-ms/roadmap
- https://github.com/ecosyste-ms/timeline
- https://github.com/ecosyste-ms/repos
- https://github.com/ecosyste-ms/packages

## What appears still missing

Existing products mostly answer one of:

- what is popular/trending;
- what is a repo's historical growth;
- what dependencies exist;
- what startups/people exist;
- what papers/authors cite each other.

GitGoblin's intended differentiation is the pipeline:

```text
historically high-signal people
→ weighted public technical actions
→ temporal/independence-aware convergence
→ architectural primitive extraction
→ downstream product hypotheses
→ measured VentureLab outcomes
→ calibrate which people/signals were actually predictive
```

The final feedback loop—measuring whether early signals later became technically/commercially important—is the long-run moat, not the raw GitHub ingest.
