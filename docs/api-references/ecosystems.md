# ecosyste.ms API Reference

## Base URL
`https://repos.ecosyste.ms/api/v1`

## Authentication
May require API key for some endpoints.

## Rate Limits
- No public documentation
- Returns 402 on unauthenticated access to some endpoints
- Be conservative — 1 req/5s recommended

## Key Endpoints Used

### Repository Metadata
```
GET /hosts/GitHub/repositories/{owner}/{name}
```
- Returns: repo metadata including stars, forks, issues, license, language, topics, last_synced_at
- Cache TTL: 3600s (1 hour)

## Response Structure
```json
{
  "html_url": "https://github.com/owner/name",
  "stargazers_count": 1234,
  "forks_count": 56,
  "open_issues_count": 7,
  "created_at": "2020-01-01T00:00:00Z",
  "pushed_at": "2026-08-18T00:00:00Z",
  "license": "MIT",
  "language": "Python",
  "topics": ["ai", "agent"],
  "last_synced_at": "2026-08-18T00:00:00Z"
}
```

## Best Practices
1. Cache aggressively — repo metadata changes slowly
2. May need API key for production use
3. Use CC-BY-SA-4.0 licensed data
