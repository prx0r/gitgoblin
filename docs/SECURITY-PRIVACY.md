# Security, privacy and source-policy notes

GitGoblin is designed for technical ecosystem intelligence from lawfully/publicly accessible sources. It should not be used to build spam lists or bypass source access controls.

## GitHub

- Use the documented API.
- Honor primary and secondary rate limits.
- Do not attempt to defeat the 2026 restrictions on arbitrary repository stargazer/watcher enumeration.
- Do not sell/export personal contact data or use the API for spam.
- Treat public-event API latency as a source-quality property rather than pretending the feed is immediate.

## Secrets

Store `GITHUB_TOKEN`, `OPENALEX_API_KEY` and optional model credentials in environment variables or a secrets manager. `.env` is ignored by git.

## Source data

Raw public facts can still have upstream terms and data licenses. Store source family, source URL and artifact hash on every derived observation. When redistributing ecosyste.ms-derived datasets, review its CC BY-SA 4.0 requirements.

## Repository code reuse

GitGoblin's license classifier is a safety gate, not legal advice. Permissive licenses can still require notices. Copyleft licenses can trigger obligations when code is incorporated/distributed. Unknown/no-license repositories should be treated as non-reusable source code until permission/license is established.

## Abuse controls for a hosted product

Before multi-tenant deployment add:

- authenticated API keys;
- per-tenant quotas;
- audit log;
- abuse monitoring;
- source-specific crawl budgets;
- deletion/correction workflow for derived identity mappings;
- clear acceptable-use terms.
